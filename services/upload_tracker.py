import json
import os
import datetime
import logging

UPLOAD_STATUS_FILE = "channel/upload_status.json"

def load_upload_status():
    """Load upload status from JSON file"""
    if not os.path.exists(UPLOAD_STATUS_FILE):
        return {"pending_uploads": [], "uploaded": []}
    
    try:
        with open(UPLOAD_STATUS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"pending_uploads": [], "uploaded": []}

def save_upload_status(status):
    """Save upload status to JSON file"""
    os.makedirs(os.path.dirname(UPLOAD_STATUS_FILE), exist_ok=True)
    with open(UPLOAD_STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(status, f, indent=2, ensure_ascii=False)

def track_pending_upload(file_path, video_type, topic, scheduled_time, metadata=None):
    """Track a file as pending upload"""
    status = load_upload_status()
    
    pending_item = {
        "file_path": file_path,
        "type": video_type,
        "topic": topic,
        "scheduled_time": scheduled_time,
        "created_at": datetime.datetime.now().isoformat(),
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
        "uploaded_at": datetime.datetime.now().isoformat(),
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
                    item["deleted_at"] = datetime.datetime.now().isoformat()
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
