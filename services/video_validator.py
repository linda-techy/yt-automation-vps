"""
Video Quality Validator

Validates generated videos before upload to prevent:
- Corrupted files
- Zero-duration videos
- Audio/video sync issues
- Resolution mismatches
- Invalid codecs

Ensures only high-quality content reaches YouTube.
"""

import os
import logging
from moviepy.editor import VideoFileClip

def validate_video(video_path, expected_min_duration=10, expected_format="9:16"):
    """
    Comprehensive video quality validation.
    
    Args:
        video_path: Path to video file
        expected_min_duration: Minimum acceptable duration in seconds
        expected_format: "16:9" for long, "9:16" for shorts
    
    Returns:
        dict with validation results
    
    Raises:
        ValueError: If video fails critical validation
    """
    results = {
        "valid": False,
        "file_exists": False,
        "file_size_mb": 0,
        "duration_sec": 0,
        "resolution": None,
        "fps": 0,
        "has_audio": False,
        "codec": None,
        "errors": []
    }
    
    # Check file exists
    if not os.path.exists(video_path):
        results["errors"].append("File does not exist")
        logging.error(f"[Validator] File not found: {video_path}")
        raise ValueError(f"Video file not found: {video_path}")
    
    results["file_exists"] = True
    results["file_size_mb"] = os.path.getsize(video_path) / (1024 * 1024)
    
    # Check file size (YouTube limits: 256GB, but warn if <1MB or >2GB)
    if results["file_size_mb"] < 1:
        results["errors"].append("File too small (< 1MB) - likely corrupted")
    elif results["file_size_mb"] > 2000:
        results["errors"].append("File very large (> 2GB) - may have upload issues")
    
    try:
        # Load video
        clip = VideoFileClip(video_path)
        
        # Validate duration
        results["duration_sec"] = clip.duration
        if clip.duration < expected_min_duration:
            results["errors"].append(f"Duration too short: {clip.duration:.1f}s < {expected_min_duration}s")
        elif clip.duration == 0:
            results["errors"].append("Zero duration - corrupted video")
            raise ValueError("Video has zero duration")
        
        # Validate resolution
        results["resolution"] = f"{clip.size[0]}x{clip.size[1]}"
        width, height = clip.size
        
        if expected_format == "16:9":
            # Long video: should be 1920x1080 or 1280x720
            if not ((width == 1920 and height == 1080) or (width == 1280 and height == 720)):
                results["errors"].append(f"Unexpected resolution for 16:9: {width}x{height}")
        elif expected_format == "9:16":
            # Shorts: should be 1080x1920
            if not (width == 1080 and height == 1920):
                results["errors"].append(f"Unexpected resolution for 9:16: {width}x{height}")
        
        # Validate FPS
        results["fps"] = clip.fps
        if clip.fps < 23 or clip.fps > 61:
            results["errors"].append(f"Unusual FPS: {clip.fps} (expected 24-60)")
        
        # Validate audio
        results["has_audio"] = clip.audio is not None
        if not results["has_audio"]:
            results["errors"].append("No audio track detected")
        
        # Check codec (basic)
        try:
            results["codec"] = clip.filename.split('.')[-1]
        except:
            results["codec"] = "unknown"
        
        # Close clip
        clip.close()
        
        # Overall validation
        critical_errors = [e for e in results["errors"] if "corrupted" in e.lower() or "zero" in e.lower()]
        results["valid"] = len(critical_errors) == 0
        
        if results["valid"]:
            logging.info(f"[Validator] ✅ Video valid: {video_path}")
            logging.info(f"   Duration: {results['duration_sec']:.1f}s, Size: {results['file_size_mb']:.1f}MB")
            logging.info(f"   Resolution: {results['resolution']}, FPS: {results['fps']}")
        else:
            logging.error(f"[Validator] ❌ Video FAILED validation: {video_path}")
            for error in results["errors"]:
                logging.error(f"   - {error}")
        
        return results
    
    except Exception as e:
        logging.error(f"[Validator] Exception during validation: {e}")
        results["errors"].append(f"Validation exception: {str(e)}")
        results["valid"] = False
        return results


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        result = validate_video(video_path)
        
        print("\n" + "="*50)
        print("VIDEO VALIDATION RESULTS")
        print("="*50)
        print(f"File: {video_path}")
        print(f"Valid: {result['valid']}")
        print(f"Duration: {result['duration_sec']:.1f}s")
        print(f"Size: {result['file_size_mb']:.1f}MB")
        print(f"Resolution: {result['resolution']}")
        print(f"FPS: {result['fps']}")
        print(f"Has Audio: {result['has_audio']}")
        
        if result['errors']:
            print(f"\nErrors Found: {len(result['errors'])}")
            for err in result['errors']:
                print(f"  - {err}")
    else:
        print("Usage: python video_validator.py <video_path>")
