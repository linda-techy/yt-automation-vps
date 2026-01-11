"""
Content Archiver

Archives scripts, metadata, and thumbnails after successful upload.

Benefits:
- Historical reference of published content
- Can recreate videos if needed
- Performance analytics tracking
- Audit trail for debugging

Structure:
archive/
  2025-12-22/
    long_video/
      script.json
      seo.txt
      thumbnail.png
      metadata.json
    short_1/
      script.json
      ...
"""

import os
import json
import shutil
import logging
from datetime import datetime

ARCHIVE_DIR = "archive"

def archive_content(video_type, topic, script, seo, thumbnail_path=None, video_id=None):
    """
    Archive content data after successful upload.
    
    Args:
        video_type: "long" or "short_{N}"
        topic: Video topic/title
        script: Script dict with content
        seo: SEO metadata string
        thumbnail_path: Path to thumbnail image
        video_id: YouTube video ID
    
    Returns:
        Path to archive directory
    """
    try:
        # Create date-based directory
        date_str = datetime.now().strftime("%Y-%m-%d")
        archive_path = os.path.join(ARCHIVE_DIR, date_str, video_type)
        os.makedirs(archive_path, exist_ok=True)
        
        # Save script
        script_file = os.path.join(archive_path, "script.json")
        with open(script_file, 'w', encoding='utf-8') as f:
            json.dump(script, f, indent=2, ensure_ascii=False)
        
        # Save SEO
        seo_file = os.path.join(archive_path, "seo.txt")
        with open(seo_file, 'w', encoding='utf-8') as f:
            f.write(seo)
        
        # Copy thumbnail if provided
        if thumbnail_path and os.path.exists(thumbnail_path):
            thumb_archive = os.path.join(archive_path, "thumbnail.png")
            shutil.copy2(thumbnail_path, thumb_archive)
        
        # Save metadata
        metadata = {
            "topic": topic,
            "video_id": video_id,
            "video_type": video_type,
            "archived_at": datetime.now().isoformat(),
            "youtube_url": f"https://youtube.com/watch?v={video_id}" if video_id else None
        }
        
        metadata_file = os.path.join(archive_path, "metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logging.info(f"[Archive] ✅ Archived {video_type}: {archive_path}")
        return archive_path
    
    except Exception as e:
        logging.error(f"[Archive] Failed to archive {video_type}: {e}")
        return None


def get_archive_stats():
    """Get statistics about archived content"""
    if not os.path.exists(ARCHIVE_DIR):
        return {"total_days": 0, "total_videos": 0}
    
    days = os.listdir(ARCHIVE_DIR)
    total_videos = 0
    
    for day in days:
        day_path = os.path.join(ARCHIVE_DIR, day)
        if os.path.isdir(day_path):
            total_videos += len([d for d in os.listdir(day_path) if os.path.isdir(os.path.join(day_path, d))])
    
    return {
        "total_days": len(days),
        "total_videos": total_videos,
        "oldest_date": min(days) if days else None,
        "newest_date": max(days) if days else None
    }


if __name__ == "__main__":
    stats = get_archive_stats()
    print("Archive Statistics:")
    print(f"  Total days: {stats['total_days']}")
    print(f"  Total videos: {stats['total_videos']}")
    print(f"  Date range: {stats.get('oldest_date')} to {stats.get('newest_date')}")
