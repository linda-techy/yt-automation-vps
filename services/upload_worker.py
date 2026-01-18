"""
Upload Worker - Background Service for Scheduled Uploads

Checks pending uploads and uploads them at scheduled IST peak times.
Runs continuously in daemon loop, checking every minute.
"""

import os
import json
import logging
import datetime
import pytz
from typing import List, Dict, Optional

from services.upload_tracker import (
    get_pending_uploads, 
    mark_as_uploaded,
    get_upload_time_from_scheduled
)
from services.youtube_uploader import upload_short
from services.video_lifecycle_manager import mark_upload_success
from services.content_archiver import archive_content


def should_upload_now(scheduled_time_str: str, window_minutes: int = 5) -> bool:
    """
    Check if current time is within upload window of scheduled time.
    
    Args:
        scheduled_time_str: ISO format scheduled publish time (UTC)
        window_minutes: Time window in minutes before scheduled time (default: 5)
    
    Returns:
        bool: True if current time is within upload window
    """
    try:
        # Get upload time (1 hour before scheduled publish)
        upload_time = get_upload_time_from_scheduled(scheduled_time_str, buffer_hours=1)
        
        # Get current time in UTC
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        
        # Check if we're within the upload window
        time_diff = (upload_time - now_utc).total_seconds() / 60  # minutes
        
        # Upload if we're within window_minutes before upload_time, or if upload_time has passed
        if -window_minutes <= time_diff <= window_minutes:
            return True
        
        return False
    except Exception as e:
        logging.error(f"Error checking upload time: {e}")
        return False


def check_and_upload_pending() -> Dict[str, int]:
    """
    Check pending uploads and upload those ready for scheduled time.
    
    Includes:
    - Duplicate check (prevent re-uploads)
    - Quota validation
    - File locking (prevent concurrent uploads)
    - Cross-promotion comment updates
    
    Returns:
        dict: {"uploaded": count, "failed": count, "pending": count}
    """
    from services.upload_validator import is_already_uploaded, check_quota_available
    from services.upload_tracker import load_upload_status, save_upload_status
    
    pending = get_pending_uploads()
    
    if not pending:
        return {"uploaded": 0, "failed": 0, "pending": 0}
    
    results = {
        "uploaded": 0,
        "failed": 0,
        "pending": len(pending)
    }
    
    # Update linked_long_video IDs for shorts (if long video was uploaded)
    _update_linked_videos()
    
    for item in pending[:]:  # Copy list to avoid modification during iteration
        file_path = item.get("file_path")
        scheduled_time = item.get("scheduled_time")
        metadata = item.get("metadata", {})
        attempts = item.get("attempts", 0)
        max_attempts = 3
        
        # Skip if max attempts reached
        if attempts >= max_attempts:
            logging.warning(f"Skipping {os.path.basename(file_path)} - max attempts ({max_attempts}) reached")
            results["failed"] += 1
            continue
        
        # Check if file exists
        if not os.path.exists(file_path):
            logging.warning(f"Pending upload file not found: {file_path}")
            results["failed"] += 1
            continue
        
        # Check if already uploaded (duplicate prevention)
        already_uploaded, existing_id = is_already_uploaded(file_path)
        if already_uploaded:
            logging.info(f"Video already uploaded: {existing_id}, marking as uploaded")
            mark_as_uploaded(file_path, existing_id)
            mark_upload_success(file_path, existing_id)
            results["uploaded"] += 1
            continue
        
        # Check if it's time to upload
        if not should_upload_now(scheduled_time):
            continue  # Not time yet, skip
        
        # Check quota before upload
        try:
            quota_status = check_quota_available(required_units=1600)
            if not quota_status['available']:
                logging.warning(f"Quota exhausted, skipping upload: {quota_status['used']}/{quota_status['limit']}")
                continue  # Try again next minute
        except Exception as e:
            logging.warning(f"Quota check failed: {e}, proceeding anyway")
        
        # Time to upload!
        logging.info(f"⏰ Upload time reached for: {os.path.basename(file_path)}")
        logging.info(f"   Scheduled: {scheduled_time}")
        
        try:
            # Use upload lock to prevent concurrent uploads
            from utils.upload_lock import upload_lock
            
            with upload_lock(file_path, timeout=300):
                # Extract metadata
                seo_metadata = metadata.get("seo_metadata", {})
                thumbnail_path = metadata.get("thumbnail_path")
                video_type = item.get("type", "short")
                
                # Double-check not already uploaded (race condition protection)
                already_uploaded_check, existing_id_check = is_already_uploaded(file_path)
                if already_uploaded_check:
                    logging.info(f"Video already uploaded (double-check): {existing_id_check}, skipping")
                    mark_as_uploaded(file_path, existing_id_check)
                    mark_upload_success(file_path, existing_id_check)
                    results["uploaded"] += 1
                    continue
                
                # Upload to YouTube
                video_id = upload_short(
                    file_path,
                    seo_metadata,
                    publish_at=scheduled_time,
                    thumbnail_path=thumbnail_path
                )
            
            if video_id:
                # Mark as uploaded
                mark_as_uploaded(file_path, video_id)
                mark_upload_success(file_path, video_id)
                
                # Archive content
                try:
                    archive_content(
                        video_type=video_type,
                        topic=item.get("topic", ""),
                        script=metadata.get("script"),
                        seo=seo_metadata,
                        thumbnail_path=thumbnail_path,
                        video_id=video_id
                    )
                except Exception as e:
                    logging.warning(f"Archive failed for {video_id}: {e}")
                
                # Post engagement comment for long videos
                if video_type == "long":
                    try:
                        from services.youtube_uploader import insert_comment
                        comment_q = "What do you think? Share your thoughts! 💭"
                        insert_comment(video_id, comment_q)
                    except Exception as e:
                        logging.warning(f"Comment posting failed: {e}")
                    
                    # Update linked_long_video for related shorts
                    _update_shorts_with_long_id(video_id, item.get("topic"))
                
                # Handle cross-promotion comments for shorts
                if video_type == "short":
                    long_video_id = metadata.get("linked_long_video")
                    if long_video_id and long_video_id != "pending":
                        try:
                            from services.youtube_uploader import insert_comment, pin_comment
                            link_comment = f"📺 Watch the full breakdown: https://youtube.com/watch?v={long_video_id}"
                            comment_id = insert_comment(video_id, link_comment)
                            if comment_id:
                                pin_comment(comment_id)
                                logging.info(f"  ✅ Pinned cross-promotion comment")
                        except Exception as e:
                            logging.warning(f"Cross-promotion comment failed: {e}")
                
                # Validate video_id is unique (collision detection)
                if video_id:
                    # Check if this video_id already exists in uploaded list
                    status_check = load_upload_status()
                    existing_videos = [v for v in status_check.get("uploaded", []) if v.get("video_id") == video_id]
                    if existing_videos:
                        logging.warning(f"[Upload Worker] Video ID collision detected: {video_id}")
                        logging.warning(f"[Upload Worker] Updating existing record instead of creating duplicate")
                        # Update existing record instead of creating duplicate
                        for existing_video in existing_videos:
                            if existing_video.get("file_path") != file_path:
                                existing_video["file_path"] = file_path
                                existing_video["uploaded_at"] = datetime.datetime.now().isoformat()
                                save_upload_status(status_check)
                                break
                
                results["uploaded"] += 1
                logging.info(f"✅ Successfully uploaded: {os.path.basename(file_path)} → {video_id}")
            else:
                raise Exception("Upload returned None video_id")
                
        except TimeoutError as e:
            # Lock timeout - skip this upload, try again next minute
            logging.warning(f"[Upload Worker] Lock timeout for {os.path.basename(file_path)}: {e}")
            results["failed"] += 1
            continue
        except Exception as e:
            # Increment attempts
            item["attempts"] = attempts + 1
            item["last_error"] = str(e)
            item["last_attempt"] = datetime.datetime.now().isoformat()
            
            # Save updated status
            from services.upload_tracker import load_upload_status, save_upload_status
            status = load_upload_status()
            for idx, pending_item in enumerate(status.get("pending_uploads", [])):
                if pending_item.get("file_path") == file_path:
                    status["pending_uploads"][idx] = item
                    break
            save_upload_status(status)
            
            results["failed"] += 1
            logging.error(f"❌ Upload failed for {os.path.basename(file_path)} (attempt {item['attempts']}/{max_attempts}): {e}")
    
    return results


def _update_linked_videos():
    """
    Update linked_long_video IDs for shorts after long video uploads.
    This ensures cross-promotion comments have the correct long video ID.
    """
    from services.upload_tracker import load_upload_status, save_upload_status
    
    try:
        status = load_upload_status()
        uploaded = status.get("uploaded", [])
        pending = status.get("pending_uploads", [])
        
        # Find uploaded long videos by topic
        long_video_by_topic = {}
        for uploaded_item in uploaded:
            if uploaded_item.get("type") == "long":
                topic = uploaded_item.get("topic", "")
                video_id = uploaded_item.get("video_id")
                if topic and video_id:
                    long_video_by_topic[topic] = video_id
        
        # Update shorts that reference long videos
        updated = False
        for pending_item in pending:
            if pending_item.get("type") == "short":
                metadata = pending_item.get("metadata", {})
                linked_long = metadata.get("linked_long_video")
                topic = pending_item.get("topic", "")
                
                # If linked_long_video is "pending", try to find the ID by topic
                if linked_long == "pending" and topic in long_video_by_topic:
                    metadata["linked_long_video"] = long_video_by_topic[topic]
                    pending_item["metadata"] = metadata
                    updated = True
        
        if updated:
            save_upload_status(status)
            logging.debug("Updated linked_long_video IDs for shorts")
    except Exception as e:
        logging.warning(f"Failed to update linked videos: {e}")


def _update_shorts_with_long_id(long_video_id: str, topic: str):
    """
    Update shorts metadata with long video ID after long video uploads.
    
    Args:
        long_video_id: YouTube video ID of the uploaded long video
        topic: Topic string to match related shorts
    """
    from services.upload_tracker import load_upload_status, save_upload_status
    
    try:
        status = load_upload_status()
        pending = status.get("pending_uploads", [])
        updated = False
        
        for pending_item in pending:
            if pending_item.get("type") == "short" and pending_item.get("topic") == topic:
                metadata = pending_item.get("metadata", {})
                if metadata.get("linked_long_video") == "pending":
                    metadata["linked_long_video"] = long_video_id
                    pending_item["metadata"] = metadata
                    updated = True
        
        if updated:
            save_upload_status(status)
            logging.info(f"Updated {updated} shorts with long video ID: {long_video_id}")
    except Exception as e:
        logging.warning(f"Failed to update shorts with long ID: {e}")


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    print("Upload Worker Test")
    print("=" * 50)
    results = check_and_upload_pending()
    print(json.dumps(results, indent=2))
