"""
Upload Validator - Pre-Upload Validation for YouTube
Prevents upload failures by validating all assets and metadata
"""

import os
import json
import logging
from datetime import datetime


def validate_upload_ready(video_path, thumbnail_path, seo_metadata):
    """
    Comprehensive pre-upload validation.
    
    Validates:
    - Video file exists and is valid
    - Thumbnail exists and is valid format
    - SEO metadata within YouTube limits
    
    Args:
        video_path: Path to video file
        thumbnail_path: Path to thumbnail image
        seo_metadata: Dict with title, description, tags
    
    Returns:
        dict: {"valid": bool, "issues": [], "warnings": []}
    
    Raises:
        Exception: If critical validation fails
    """
    
    issues = []
    warnings = []
    
    # 1. VIDEO VALIDATION
    if not video_path or not os.path.exists(video_path):
        issues.append(f"Video not found: {video_path}")
    else:
        # Check file size (YouTube limit: 256GB, but practical ~2GB for reliability)
        file_size = os.path.getsize(video_path)
        if file_size > 2 * 1024 * 1024 * 1024:  # 2GB
            warnings.append(f"Video large: {file_size/(1024*1024*1024):.1f}GB (slow upload)")
        if file_size < 1024:  # < 1KB
            issues.append(f"Video too small: {file_size} bytes (likely corrupted)")
    
    # 2. THUMBNAIL VALIDATION
    if not thumbnail_path:
        warnings.append("No thumbnail provided - YouTube will auto-generate (low CTR)")
    elif not os.path.exists(thumbnail_path):
        issues.append(f"Thumbnail not found: {thumbnail_path}")
    else:
        # Check format
        valid_formats = ['.png', '.jpg', '.jpeg']
        ext = os.path.splitext(thumbnail_path)[1].lower()
        if ext not in valid_formats:
            issues.append(f"Invalid thumbnail format: {ext} (use PNG/JPG)")
        
        # Check size (YouTube requirements: 2MB max, min 640x360)
        thumb_size = os.path.getsize(thumbnail_path)
        if thumb_size > 2 * 1024 * 1024:  # 2MB
            issues.append(f"Thumbnail too large: {thumb_size/(1024*1024):.1f}MB (max 2MB)")
    
    # 3. SEO METADATA VALIDATION
    metadata_issues = validate_youtube_metadata(seo_metadata)
    issues.extend(metadata_issues.get('errors', []))
    warnings.extend(metadata_issues.get('warnings', []))
    
    # Result
    result = {
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings
    }
    
    if not result['valid']:
        logging.error(f"Upload validation failed: {issues}")
        raise Exception(f"Upload validation failed: {', '.join(issues)}")
    
    if warnings:
        logging.warning(f"Upload warnings: {warnings}")
    
    return result


def validate_youtube_metadata(seo_metadata, auto_fix=True):
    """
    Validate SEO metadata against YouTube limits.
    
    YouTube Limits:
    - Title: 100 characters max
    - Description: 5,000 characters max
    - Tags: 500 characters total
    - Hashtags in description: 60 characters recommended
    
    Args:
        seo_metadata: Dict with title, description, tags
        auto_fix: If True, automatically truncate to limits
    
    Returns:
        dict: {"errors": [], "warnings": [], "fixed_metadata": {}}
    """
    
    errors = []
    warnings = []
    
    title = seo_metadata.get('title', '')
    description = seo_metadata.get('description', '')
    tags = seo_metadata.get('tags', [])
    
    fixed_metadata = seo_metadata.copy()
    
    # TITLE VALIDATION
    if not title:
        errors.append("Title is empty")
    elif len(title) > 100:
        if auto_fix:
            fixed_metadata['title'] = title[:97] + "..."
            warnings.append(f"Title truncated: {len(title)} → 100 chars")
        else:
            errors.append(f"Title too long: {len(title)}/100 chars")
    elif len(title) < 10:
        warnings.append(f"Title short: {len(title)} chars (recommend 60-70)")
    
    # DESCRIPTION VALIDATION
    if len(description) > 5000:
        if auto_fix:
            fixed_metadata['description'] = description[:4997] + "..."
            warnings.append(f"Description truncated: {len(description)} → 5000 chars")
        else:
            errors.append(f"Description too long: {len(description)}/5000 chars")
    elif len(description) < 100:
        warnings.append("Description short (recommend 200+ chars for SEO)")
    
    # TAGS VALIDATION
    tags_str = " ".join(tags)
    if len(tags_str) > 500:
        if auto_fix:
            # Trim tags to fit 500 char limit
            trimmed_tags = []
            current_len = 0
            for tag in tags:
                if current_len + len(tag) + 1 <= 500:
                    trimmed_tags.append(tag)
                    current_len += len(tag) + 1
                else:
                    break
            fixed_metadata['tags'] = trimmed_tags
            warnings.append(f"Tags trimmed: {len(tags)} → {len(trimmed_tags)} tags")
        else:
            errors.append(f"Tags too long: {len(tags_str)}/500 chars")
    elif len(tags) < 3:
        warnings.append("Few tags (recommend 5-10 relevant tags)")
    
    return {
        "errors": errors,
        "warnings": warnings,
        "fixed_metadata": fixed_metadata
    }


def is_already_uploaded(video_path, lifecycle_file='channel/video_lifecycle.json'):
    """
    Check if video already uploaded via lifecycle tracking.
    
    Prevents duplicate uploads.
    
    Args:
        video_path: Path to video file
        lifecycle_file: Path to lifecycle JSON
    
    Returns:
        tuple: (already_uploaded: bool, youtube_id: str or None)
    """
    
    if not os.path.exists(lifecycle_file):
        return False, None
    
    try:
        with open(lifecycle_file, 'r', encoding='utf-8') as f:
            lifecycle = json.load(f)
        
        for video in lifecycle.get('videos', []):
            if video.get('path') == video_path:
                youtube_id = video.get('youtube_id')
                if youtube_id:
                    logging.info(f"Video already uploaded: {youtube_id} ({video_path})")
                    return True, youtube_id
        
        return False, None
        
    except Exception as e:
        logging.warning(f"Error checking upload status: {e}")
        return False, None


def check_quota_available(required_units=1600, quota_file='channel/youtube_quota.json'):
    """
    Check if enough YouTube API quota available.
    
    YouTube Limits:
    - 10,000 units/day
    - Upload = 1,600 units
    
    Args:
        required_units: Units needed for operation
        quota_file: Path to quota tracking JSON
    
    Returns:
        dict: {"available": bool, "used": int, "limit": int, "reset_at": str}
    """
    
    DAILY_LIMIT = 10000
    
    # Load or initialize quota data
    if os.path.exists(quota_file):
        with open(quota_file, 'r') as f:
            quota_data = json.load(f)
        
        # Reset if new day
        reset_date = datetime.fromisoformat(quota_data['reset_date']).date()
        if reset_date < datetime.now().date():
            quota_data = {
                "used": 0,
                "reset_date": datetime.now().date().isoformat()
            }
    else:
        quota_data = {
            "used": 0,
            "reset_date": datetime.now().date().isoformat()
        }
    
    # Check availability
    available = (quota_data['used'] + required_units) <= DAILY_LIMIT
    
    return {
        "available": available,
        "used": quota_data['used'],
        "limit": DAILY_LIMIT,
        "remaining": DAILY_LIMIT - quota_data['used'],
        "reset_at": quota_data['reset_date']
    }


def record_quota_usage(units_used=1600, quota_file='channel/youtube_quota.json'):
    """
    Record YouTube API quota usage.
    
    Args:
        units_used: Units consumed (upload=1600, comment=50, etc.)
        quota_file: Path to quota tracking JSON
    """
    
    quota_status = check_quota_available(0)  # Get current status
    
    quota_data = {
        "used": quota_status['used'] + units_used,
        "reset_date": quota_status['reset_at']
    }
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(quota_file), exist_ok=True)
    
    with open(quota_file, 'w') as f:
        json.dump(quota_data, f, indent=2)
    
    logging.info(f"Quota: {quota_data['used']}/10000 used")


if __name__ == "__main__":
    # Test validation
    test_seo = {
        "title": "Test Video Title",
        "description": "Test description",
        "tags": ["test", "video"]
    }
    
    result = validate_youtube_metadata(test_seo)
    print(f"Validation: {result}")
