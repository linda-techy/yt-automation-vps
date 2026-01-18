import json
import os
import datetime
import logging

from utils.file_locking import load_json_safe, save_json_safe

UPLOAD_STATUS_FILE = "channel/upload_status.json"

def load_upload_status():
    """Load upload status from JSON file (thread-safe)"""
    default_status = {"pending_uploads": [], "uploaded": []}
    return load_json_safe(UPLOAD_STATUS_FILE, default=default_status)

def save_upload_status(status):
    """Save upload status to JSON file (thread-safe)"""
    success = save_json_safe(UPLOAD_STATUS_FILE, status)
    if not success:
        logging.error(f"[Upload Tracker] Failed to save upload status: {UPLOAD_STATUS_FILE}")

def track_pending_upload(file_path, video_type, topic, scheduled_time, metadata=None):
    """Track a file as pending upload"""
    status = load_upload_status()
    
    pending_item = {
        "file_path": file_path,
        "type": video_type,
        "topic": topic,
        "scheduled_time": scheduled_time,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "attempts": 0,
        "metadata": metadata or {}
    }
    
    status["pending_uploads"].append(pending_item)
    save_upload_status(status)
    logging.info(f"[Upload Status] Tracked pending: {os.path.basename(file_path)}")

def mark_as_uploaded(file_path, video_id):
    """Mark a file as successfully uploaded"""
    status = load_upload_status()
    
    # Remove from pending
    status["pending_uploads"] = [
        item for item in status["pending_uploads"] 
        if item["file_path"] != file_path
    ]
    
    # Add to uploaded
    uploaded_item = {
        "file_path": file_path,
        "video_id": video_id,
        "uploaded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "safe_to_delete": True
    }
    
    status["uploaded"].append(uploaded_item)
    save_upload_status(status)
    logging.info(f"[Upload Status] Marked uploaded: {os.path.basename(file_path)} → {video_id}")

def cleanup_uploaded_files():
    """Delete only files that have been successfully uploaded"""
    status = load_upload_status()
    deleted_count = 0
    
    for item in status["uploaded"]:
        if item.get("safe_to_delete") and item.get("video_id"):
            file_path = item["file_path"]
            
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    item["deleted_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    item["safe_to_delete"] = False  # Mark as already deleted
                    deleted_count += 1
                    logging.info(f"[Upload Status] ✅ Deleted uploaded: {os.path.basename(file_path)}")
                except Exception as e:
                    logging.warning(f"[Upload Status] Failed to delete {file_path}: {e}")
    
    save_upload_status(status)
    return deleted_count

def get_pending_uploads():
    """Get list of pending uploads from previous runs"""
    status = load_upload_status()
    return status.get("pending_uploads", [])

def get_upload_time_from_scheduled(scheduled_time_str: str, buffer_hours: int = 1) -> datetime.datetime:
    """
    Extract upload time from scheduled publish time.
    
    Upload should happen before scheduled publish time to ensure YouTube 
    processing completes before publication.
    
    Args:
        scheduled_time_str: ISO format scheduled publish time (UTC)
        buffer_hours: Hours before publish time to upload (default: 1 hour)
    
    Returns:
        datetime.datetime: Upload time in UTC
    """
    try:
        # Parse scheduled time (handle both 'Z' and '+00:00' formats)
        scheduled = datetime.datetime.fromisoformat(scheduled_time_str.replace('Z', '+00:00'))
        
        # Calculate upload time (buffer_hours before scheduled time)
        upload_time = scheduled - datetime.timedelta(hours=buffer_hours)
        
        return upload_time
    except Exception as e:
        logging.error(f"Failed to parse scheduled_time: {scheduled_time_str}, error: {e}")
        # Fallback: return current time + 1 hour
        return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)

def retry_pending_uploads(upload_function):
    """Retry uploading pending files from previous runs"""
    pending = get_pending_uploads()
    
    if not pending:
        return []
    
    logging.info(f"[Upload Status] Found {len(pending)} pending uploads from previous run")
    
    retried = []
    for item in pending:
        file_path = item["file_path"]
        
        if not os.path.exists(file_path):
            logging.warning(f"[Upload Status] Pending file not found: {file_path}")
            continue
        
        try:
            logging.info(f"[Upload Status] Retrying upload: {os.path.basename(file_path)}")
            video_id = upload_function(item)
            
            if video_id:
                mark_as_uploaded(file_path, video_id)
                retried.append(item)
        except Exception as e:
            item["attempts"] = item.get("attempts", 0) + 1
            logging.error(f"[Upload Status] Retry failed: {e}")
    
    return retried

if __name__ == "__main__":
    # Test
    print("Upload Status Tracker - Test")
    status = load_upload_status()
    print(json.dumps(status, indent=2))
