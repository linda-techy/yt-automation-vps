"""
Upload Wrapper - Simplified Integration for Pipeline
Bundles all upload validations into single function
"""

import logging
from services.upload_validator import (
    validate_upload_ready, is_already_uploaded,
    check_quota_available, record_quota_usage, validate_youtube_metadata
)
from services.timezone_converter import convert_to_youtube_time
from services.youtube_uploader import upload_short


def upload_video_safe(
    video_path,
    thumbnail_path,
    seo_metadata,
    publish_time,
    video_type="long"
):
    """
    Safe upload with all validations bundled.
    
    Performs:
    1. Duplicate check
    2. Metadata validation (auto-fix)
    3. Asset validation
    4. Quota check
    5. Timezone conversion
    6. Upload
    7. Quota tracking
    
    Args:
        video_path: Path to video file
        thumbnail_path: Path to thumbnail
        seo_metadata: Dict with title, description, tags
        publish_time: Local time string (IST)
        video_type: "long" or "short"
    
    Returns:
        str: YouTube video ID (or existing ID if duplicate)
    
    Raises:
        Exception: If validation fails or quota exhausted
    """
    
    logging.info(f"🔍 Starting safe upload for {video_type} video...")
    
    # 1. Check duplicate
    already_uploaded, existing_id = is_already_uploaded(video_path)
    if already_uploaded:
        logging.info(f"✅ Video already uploaded: {existing_id}")
        return existing_id
    
    # 2. Validate and fix metadata
    metadata_result = validate_youtube_metadata(seo_metadata, auto_fix=True)
    if metadata_result['warnings']:
        logging.warning(f"SEO auto-fixed: {metadata_result['warnings']}")
    seo_validated = metadata_result['fixed_metadata']
    
    # 3. Validate assets exist
    validate_upload_ready(video_path, thumbnail_path, seo_validated)
    logging.info("✅ Asset validation passed")
    
    # 4. Check quota
    quota_status = check_quota_available(required_units=1600)
    if not quota_status['available']:
        raise Exception(
            f"❌ Quota exhausted: {quota_status['used']}/{quota_status['limit']} "
            f"(resets tomorrow)"
        )
    logging.info(f"✅ Quota check: {quota_status['remaining']} units remaining")
    
    # 5. Convert timezone
    youtube_time = convert_to_youtube_time(publish_time)
    logging.info(f"✅ Time converted: {publish_time} (IST) → {youtube_time} (UTC)")
    
    # 6. Upload
    logging.info(f"📤 Uploading {video_type} video to YouTube...")
    video_id = upload_short(
        video_path,
        seo_validated,
        publish_at=youtube_time,
        thumbnail_path=thumbnail_path
    )
    logging.info(f"✅ Upload successful: {video_id}")
    
    # 7. Record quota
    record_quota_usage(units_used=1600)
    
    return video_id


def upload_batch_safe(videos_data, continue_on_error=True):
    """
    Upload multiple videos with per-video error recovery.
    
    Args:
        videos_data: List of dicts with:
            - video_path
            - thumbnail_path
            - seo_metadata
            - publish_time
            - video_type
            - metadata (optional, for logging)
        continue_on_error: If True, continue if one video fails
    
    Returns:
        dict: {"successful": [...], "failed": [...]}
    """
    
    results = {
        "successful": [],
        "failed": []
    }
    
    for i, video_data in enumerate(videos_data):
        try:
            video_id = upload_video_safe(
                video_data['video_path'],
                video_data['thumbnail_path'],
                video_data['seo_metadata'],
                video_data['publish_time'],
                video_data.get('video_type', f'video_{i}')
            )
            
            results["successful"].append({
                "index": i,
                "video_id": video_id,
                "path": video_data['video_path']
            })
            
        except Exception as e:
            logging.error(f"❌ Upload {i} failed: {e}")
            results["failed"].append({
                "index": i,
                "error": str(e),
                "path": video_data['video_path']
            })
            
            if not continue_on_error:
                raise
    
    logging.info(
        f"Upload batch complete: {len(results['successful'])} successful, "
        f"{len(results['failed'])} failed"
    )
    
    return results


if __name__ == "__main__":
    # Test
    print("Upload wrapper loaded successfully")
    print("Use: from services.upload_wrapper import upload_video_safe")
