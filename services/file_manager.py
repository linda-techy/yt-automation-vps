"""
File Management Utility for YouTube Automation

Handles:
- Unique file naming (prevents collisions)
- Auto-cleanup after successful upload
- Disk space management
"""

import os
import shutil
import hashlib
import datetime
import re
import logging


def generate_unique_filename(topic, format_type="long", extension=".mp4"):
    """
    Generate unique filename based on topic, timestamp, and format.
    
    Args:
        topic: Video topic string
        format_type: 'long' or 'short'
        extension: File extension (default .mp4)
    
    Returns:
        Unique filename like: long_ai_tech_2025-12-21_143022_a1b2c.mp4
    """
    # Clean topic for filename (remove special chars, limit length)
    clean_topic = re.sub(r'[^a-zA-Z0-9\s]', '', topic)
    clean_topic = "_".join(clean_topic.split()[:3]).lower()  # First 3 words
    clean_topic = clean_topic[:30] if len(clean_topic) > 30 else clean_topic
    
    # Timestamp
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    
    # Short hash for uniqueness
    hash_input = f"{topic}{timestamp}{os.getpid()}"
    short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:5]
    
    filename = f"{format_type}_{clean_topic}_{timestamp}_{short_hash}{extension}"
    return filename


def get_output_path(topic, format_type="long", extension=".mp4"):
    """
    Get full output path for video file with unique naming.
    
    Args:
        topic: Video topic
        format_type: 'long' or 'short_0', 'short_1', etc.
        extension: File extension
    
    Returns:
        Full path like: videos/output/long_ai_tech_2025-12-21_143022_a1b2c.mp4
    """
    filename = generate_unique_filename(topic, format_type, extension)
    output_dir = "videos/output"
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, filename)


def cleanup_after_upload(file_paths, delete_output=True):
    """
    Clean up video files after successful YouTube upload.
    
    Args:
        file_paths: List of file paths to delete
        delete_output: If True, delete output files. If False, only temp files.
    """
    deleted = 0
    failed = 0
    
    for path in file_paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
                logging.info(f"[Cleanup] Deleted: {os.path.basename(path)}")
                deleted += 1
            except Exception as e:
                logging.warning(f"[Cleanup] Failed to delete {path}: {e}")
                failed += 1
    
    logging.info(f"[Cleanup] Deleted {deleted} files, {failed} failed")
    return deleted, failed


def cleanup_temp_folder():
    """
    Clean up entire temp folder.
    """
    temp_dir = "videos/temp"
    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            os.makedirs(temp_dir, exist_ok=True)
            logging.info("[Cleanup] Temp folder cleared")
            return True
        except Exception as e:
            logging.warning(f"[Cleanup] Temp folder cleanup failed: {e}")
            return False
    return True


def cleanup_old_output_files(max_age_hours=24):
    """
    Clean up old output files to save disk space.
    Useful for VPS with limited storage.
    
    Args:
        max_age_hours: Delete files older than this many hours
    """
    output_dir = "videos/output"
    if not os.path.exists(output_dir):
        return 0
    
    cutoff_time = datetime.datetime.now() - datetime.timedelta(hours=max_age_hours)
    deleted = 0
    
    for filename in os.listdir(output_dir):
        filepath = os.path.join(output_dir, filename)
        if os.path.isfile(filepath):
            file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
            if file_mtime < cutoff_time:
                try:
                    os.remove(filepath)
                    logging.info(f"[Cleanup] Deleted old file: {filename}")
                    deleted += 1
                except Exception as e:
                    logging.warning(f"[Cleanup] Failed to delete old file {filename}: {e}")
    
    if deleted > 0:
        logging.info(f"[Cleanup] Deleted {deleted} old output files (>{max_age_hours}h old)")
    return deleted


def get_disk_usage():
    """
    Get disk usage statistics for videos folder.
    
    Returns:
        Dict with total, used, free space in GB
    """
    try:
        import shutil
        total, used, free = shutil.disk_usage("videos")
        return {
            "total_gb": round(total / (1024**3), 2),
            "used_gb": round(used / (1024**3), 2),
            "free_gb": round(free / (1024**3), 2),
            "usage_percent": round((used / total) * 100, 1)
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    # Test
    print("File Management Utility Test")
    print("=" * 40)
    
    topic = "AI Technology Breakthrough 2025"
    
    print(f"Long video path: {get_output_path(topic, 'long')}")
    print(f"Short 0 path: {get_output_path(topic, 'short_0')}")
    print(f"Short 1 path: {get_output_path(topic, 'short_1')}")
    
    print(f"\nDisk usage: {get_disk_usage()}")
