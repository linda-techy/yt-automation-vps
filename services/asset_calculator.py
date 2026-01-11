"""
Asset Calculator - Pre-Calculate Required Visual Assets
Prevents pipeline failures due to insufficient assets
"""

import logging
from services.subtitle_engine import analyze_audio_timing
from services.scene_optimizer import optimize_scene_durations


def calculate_required_assets(audio_path, max_scene_duration=4.5, safety_buffer=1.15):
    """
    Pre-calculate exactly how many visual assets are needed.
    
    This prevents the pipeline from:
    - Generating 32 assets
    - Starting video build
    - Failing at chunk 4 because it needs 40
    
    Args:
        audio_path: Path to audio file
        max_scene_duration: Max duration per scene (scene optimizer setting)
        safety_buffer: Multiply by 1.15 for 15% safety margin
    
    Returns:
        int: Required number of unique assets
    """
    
    try:
        # Step 1: Analyze audio timing
        scene_durations = analyze_audio_timing(audio_path, language="ml")
        
        if not scene_durations:
            logging.warning("Audio analysis returned empty, using default estimate")
            return 40  # Safe default for 5-6 min video
        
        # Step 2: Apply scene optimization (splits long scenes)
        optimized_scenes = optimize_scene_durations(scene_durations, max_image_duration=max_scene_duration)
        
        # Step 3: Calculate with safety buffer
        required = len(optimized_scenes)
        safe_count = int(required * safety_buffer)
        
        logging.info(f"Asset calculation: {len(scene_durations)} original → "
                    f"{required} optimized scenes → {safe_count} assets (15% buffer)")
        
        return safe_count
        
    except Exception as e:
        logging.error(f"Asset calculation failed: {e}, using safe default")
        return 50  # Conservative default


def validate_asset_count(asset_paths, required_count):
    """
    Validate we have enough assets before building video.
    
    Returns:
        dict: {"valid": bool, "have": int, "need": int, "message": str}
    """
    
    have = len(asset_paths)
    
    if have >= required_count:
        return {
            "valid": True,
            "have": have,
            "need": required_count,
            "message": f"✅ Sufficient assets: {have}/{required_count}"
        }
    else:
        return {
            "valid": False,
            "have": have,
            "need": required_count,
            "message": f"❌ Insufficient assets: {have}/{required_count} (short by {required_count - have})"
        }


if __name__ == "__main__":
    # Test with sample audio
    import sys
    
    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
        required = calculate_required_assets(audio_path)
        print(f"Required assets: {required}")
    else:
        print("Usage: python asset_calculator.py <audio_path>")
