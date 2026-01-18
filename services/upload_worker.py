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
    
    Returns:
        dict: {"uploaded": count, "failed": count, "pending": count}
    """
    pending = get_pending_uploads()
    
    if not pending:
        return {"uploaded": 0, "failed": 0, "pending": 0}
    
    results = {
        "uploaded": 0,
        "failed": 0,
        "pending": len(pending)
    }
    
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
        
        # Check if it's time to upload
        if not should_upload_now(scheduled_time):
            continue  # Not time yet, skip
        
        # Time to upload!
        logging.info(f"⏰ Upload time reached for: {os.path.basename(file_path)}")
        logging.info(f"   Scheduled: {scheduled_time}")
        
        try:
            # Extract metadata
            seo_metadata = metadata.get("seo_metadata", {})
            thumbnail_path = metadata.get("thumbnail_path")
            video_type = item.get("type", "short")
            
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
                
                # Handle cross-promotion comments for shorts
                if video_type == "short" and metadata.get("linked_long_video"):
                    try:
                        from services.youtube_uploader import insert_comment, pin_comment
                        long_video_id = metadata.get("linked_long_video")
                        if long_video_id and long_video_id != "pending":
                            link_comment = f"📺 Watch the full breakdown: https://youtube.com/watch?v={long_video_id}"
                            comment_id = insert_comment(video_id, link_comment)
                            if comment_id:
                                pin_comment(comment_id)
                                logging.info(f"  ✅ Pinned cross-promotion comment")
                    except Exception as e:
                        logging.warning(f"Cross-promotion comment failed: {e}")
                
                results["uploaded"] += 1
                logging.info(f"✅ Successfully uploaded: {os.path.basename(file_path)} → {video_id}")
            else:
                raise Exception("Upload returned None video_id")
                
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


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    print("Upload Worker Test")
    print("=" * 50)
    results = check_and_upload_pending()
    print(json.dumps(results, indent=2))
