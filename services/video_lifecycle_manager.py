"""
Video Lifecycle Manager - Production Grade Storage Management

Handles complete video lifecycle from creation to safe deletion:
1. Track video creation and upload status
2. Preserve videos until successful upload confirmation
3. Smart cleanup that respects scheduled uploads
4. Retry failed uploads on next run
5. Prevent storage bloat while ensuring YPP compliance

CRITICAL: Videos are NEVER deleted before upload confirmation.
"""

import os
import json
import logging
import datetime
from typing import Dict, List, Optional

VIDEO_LIFECYCLE_DB = "channel/video_lifecycle.json"

def load_lifecycle_db():
    """Load video lifecycle database"""
    if not os.path.exists(VIDEO_LIFECYCLE_DB):
        return {
            "videos": [],
            "last_cleanup": None
        }
    
    try:
        with open(VIDEO_LIFECYCLE_DB, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"[Lifecycle] Failed to load DB: {e}")
        return {"videos": [], "last_cleanup": None}

def save_lifecycle_db(db):
    """Save video lifecycle database"""
    os.makedirs(os.path.dirname(VIDEO_LIFECYCLE_DB), exist_ok=True)
    try:
        with open(VIDEO_LIFECYCLE_DB, 'w', encoding='utf-8') as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"[Lifecycle] Failed to save DB: {e}")

def register_video(video_path: str, video_type: str, topic: str, 
                  scheduled_time: str, metadata: Dict = None) -> str:
    """
    Register a newly created video in the lifecycle system.
    
    Args:
        video_path: Absolute path to video file
        video_type: "long" or "short_0", "short_1", etc.
        topic: Video topic
        scheduled_time: ISO format scheduled upload time
        metadata: Additional metadata (title, etc.)
    
    Returns:
        Video ID (internal tracking ID)
    """
    db = load_lifecycle_db()
    
    video_id = f"{video_type}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    video_entry = {
        "id": video_id,
        "file_path": os.path.abspath(video_path),
        "video_type": video_type,
        "topic": topic,
        "scheduled_time": scheduled_time,
        "created_at": datetime.datetime.now().isoformat(),
        "status": "created",  # created -> uploading -> uploaded -> deleted
        "youtube_video_id": None,
        "upload_attempts": 0,
        "last_attempt": None,
        "thumbnail_path": metadata.get("thumbnail_path") if metadata else None,  # For cleanup
        "metadata": metadata or {}
    }
    
    db["videos"].append(video_entry)
    save_lifecycle_db(db)
    
    logging.info(f"[Lifecycle] ✅ Registered: {os.path.basename(video_path)} ({video_id})")
    return video_id

def mark_upload_started(video_id: str):
    """Mark that upload attempt has started"""
    db = load_lifecycle_db()
    
    for video in db["videos"]:
        if video["id"] == video_id:
            video["status"] = "uploading"
            video["upload_attempts"] = video.get("upload_attempts", 0) + 1
            video["last_attempt"] = datetime.datetime.now().isoformat()
            save_lifecycle_db(db)
            logging.info(f"[Lifecycle] Upload started: {video_id}")
            return
    
    logging.warning(f"[Lifecycle] Video not found: {video_id}")

def mark_upload_success(file_path: str, youtube_video_id: str):
    """
    Mark video as successfully uploaded to YouTube.
    
    Args:
        file_path: Path to the video file
        youtube_video_id: YouTube's video ID (from API response)
    """
    db = load_lifecycle_db()
    
    for video in db["videos"]:
        if video["file_path"] == os.path.abspath(file_path):
            video["status"] = "uploaded"
            video["youtube_video_id"] = youtube_video_id
            video["uploaded_at"] = datetime.datetime.now().isoformat()
            save_lifecycle_db(db)
            logging.info(f"[Lifecycle] ✅ Upload confirmed: {os.path.basename(file_path)} → {youtube_video_id}")
            return
    
    logging.warning(f"[Lifecycle] Video not tracked: {file_path}")

def mark_upload_failed(video_id: str, error_msg: str):
    """Mark upload as failed (will retry later)"""
    db = load_lifecycle_db()
    
    for video in db["videos"]:
        if video["id"] == video_id:
            video["status"] = "upload_failed"
            video["last_error"] = error_msg
            save_lifecycle_db(db)
            logging.warning(f"[Lifecycle] Upload failed: {video_id} - {error_msg}")
            return

def get_videos_pending_upload() -> List[Dict]:
    """Get videos that need to be uploaded (created or failed)"""
    db = load_lifecycle_db()
    return [v for v in db["videos"] if v["status"] in ["created", "upload_failed"]]

def get_videos_safe_to_delete() -> List[Dict]:
    """
    Get videos that are safe to delete.
    
    Safe deletion criteria:
    - Status is "uploaded" (confirmed on YouTube)
    - YouTube video ID exists
    - File still exists on disk
    """
    db = load_lifecycle_db()
    safe_videos = []
    
    for video in db["videos"]:
        if (video["status"] == "uploaded" and 
            video.get("youtube_video_id") and
            os.path.exists(video["file_path"])):
            safe_videos.append(video)
    
    return safe_videos

def cleanup_uploaded_videos(max_age_hours: int = 48) -> int:
    """
    Delete videos that have been successfully uploaded and published.
    
    This ensures we keep videos for a safety buffer period even after upload, 
    in case YouTube processing fails or we need to re-upload.
    
    CRITICAL: Deletion is based on scheduled publish time, not upload time.
    Videos scheduled for future publication are NEVER deleted.
    
    Args:
        max_age_hours: Only delete videos published more than this many hours ago
    
    Returns:
        Number of files deleted
    """
    db = load_lifecycle_db()
    deleted_count = 0
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    
    for video in get_videos_safe_to_delete():
        # NEW: Check scheduled publish time first
        scheduled_time_str = video.get("scheduled_time")
        if scheduled_time_str:
            try:
                scheduled_time = datetime.datetime.fromisoformat(scheduled_time_str.replace('Z', '+00:00'))
                
                # Don't delete if scheduled for future publication
                if scheduled_time > now_utc:
                    logging.debug(f"[Lifecycle] Keeping future-scheduled video: {os.path.basename(video['file_path'])} (publishes {scheduled_time})")
                    continue  # Keep future-scheduled videos
                
                # Calculate age from publish time, not upload time
                age_hours = (now_utc - scheduled_time).total_seconds() / 3600
                if age_hours < max_age_hours:
                    logging.debug(f"[Lifecycle] Keeping recent video: {os.path.basename(video['file_path'])} (published {age_hours:.1f}h ago)")
                    continue  # Too recent, keep it
            except Exception as e:
                logging.warning(f"[Lifecycle] Failed to parse scheduled_time: {e}, falling back to upload time")
                # Fallback to upload time check
                uploaded_at_str = video.get("uploaded_at")
                if uploaded_at_str:
                    try:
                        uploaded_at = datetime.datetime.fromisoformat(uploaded_at_str)
                        cutoff_time = now_utc - datetime.timedelta(hours=max_age_hours)
                        if uploaded_at > cutoff_time:
                            continue
                    except:
                        continue
        else:
            # No scheduled time, use upload time as fallback
            uploaded_at_str = video.get("uploaded_at")
            if not uploaded_at_str:
                continue
            
            try:
                uploaded_at = datetime.datetime.fromisoformat(uploaded_at_str)
                cutoff_time = now_utc - datetime.timedelta(hours=max_age_hours)
                if uploaded_at > cutoff_time:
                    continue
            except:
                continue
        
        # Safe to delete
        file_path = video["file_path"]
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                video["status"] = "deleted"
                video["deleted_at"] = datetime.datetime.now().isoformat()
                deleted_count += 1
                logging.info(f"[Lifecycle] 🗑️ Deleted video: {os.path.basename(file_path)}")
                
                # Also delete associated thumbnail (same lifecycle)
                thumbnail_path = video.get("thumbnail_path")
                if thumbnail_path and os.path.exists(thumbnail_path):
                    try:
                        os.remove(thumbnail_path)
                        logging.info(f"[Lifecycle] 🗑️ Deleted thumbnail: {os.path.basename(thumbnail_path)}")
                    except Exception as e:
                        logging.warning(f"[Lifecycle] Failed to delete thumbnail {thumbnail_path}: {e}")
                        
            except Exception as e:
                logging.error(f"[Lifecycle] Failed to delete {file_path}: {e}")
    
    save_lifecycle_db(db)
    db["last_cleanup"] = datetime.datetime.now().isoformat()
    save_lifecycle_db(db)
    
    return deleted_count

def cleanup_temp_files():
    """
    Clean up temporary files (audio, intermediate clips, etc.)
    This is safe to do after the pipeline completes.
    """
    import shutil
    temp_dir = "videos/temp"
    
    if not os.path.exists(temp_dir):
        return
    
    try:
        shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)
        logging.info("[Lifecycle] 🧹 Temp files cleaned")
        return True
    except Exception as e:
        logging.warning(f"[Lifecycle] Temp cleanup failed: {e}")
        return False

def get_storage_stats() -> Dict:
    """Get storage statistics for monitoring"""
    db = load_lifecycle_db()
    
    total_videos = len(db["videos"])
    by_status = {}
    total_size_mb = 0
    
    for video in db["videos"]:
        status = video["status"]
        by_status[status] = by_status.get(status, 0) + 1
        
        if os.path.exists(video["file_path"]):
            total_size_mb += os.path.getsize(video["file_path"]) / (1024 * 1024)
    
    return {
        "total_videos": total_videos,
        "by_status": by_status,
        "total_size_mb": round(total_size_mb, 2),
        "pending_upload": by_status.get("created", 0) + by_status.get("upload_failed", 0),
        "last_cleanup": db.get("last_cleanup")
    }

if __name__ == "__main__":
    # Test
    print("Video Lifecycle Manager Test")
    print("=" * 50)
    stats = get_storage_stats()
    print(json.dumps(stats, indent=2))
