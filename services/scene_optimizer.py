"""
Scene Duration Optimizer
Ensures images don't stay on screen too long - improves retention
"""

import logging


def optimize_scene_durations(scene_durations, max_image_duration=4.5):
    """
    Split long scenes into shorter segments for better pacing.
    
    Problem: DALL-E images staying 10-15 seconds = boring, low retention
    Solution: Cap each visual at 3-5 seconds max
    
    Args:
        scene_durations: List of scene durations from Whisper
        max_image_duration: Max time for a single visual (default 4.5s)
    
    Returns:
        Optimized scene durations with better pacing
    """
    
    optimized = []
    
    for duration in scene_durations:
        if duration <= max_image_duration:
            # Short enough - keep as is
            optimized.append(duration)
        else:
            # Too long - split into multiple shorter scenes
            num_splits = int(duration / max_image_duration) + 1
            segment_duration = duration / num_splits
            
            for _ in range(num_splits):
                optimized.append(segment_duration)
            
            logging.info(f"Split {duration:.1f}s scene into {num_splits} × {segment_duration:.1f}s segments")
    
    return optimized


def validate_pacing(scene_durations):
    """
    Validate scene pacing for retention optimization.
    
    Returns:
        Dict with pacing analysis
    """
    
    if not scene_durations:
        return {"valid": False, "error": "No scenes"}
    
    avg_duration = sum(scene_durations) / len(scene_durations)
    max_duration = max(scene_durations)
    min_duration = min(scene_durations)
    
    # Retention best practices
    issues = []
    if max_duration > 6.0:
        issues.append(f"Scene too long: {max_duration:.1f}s (max 6s recommended)")
    if avg_duration > 4.5:
        issues.append(f"Average too high: {avg_duration:.1f}s (target 3-4s)")
    if min_duration < 1.5:
        issues.append(f"Scene too short: {min_duration:.1f}s (min 1.5s)")
    
    return {
        "valid": len(issues) == 0,
        "avg_duration": avg_duration,
        "max_duration": max_duration,
        "min_duration": min_duration,
        "total_scenes": len(scene_durations),
        "issues": issues
    }


if __name__ == "__main__":
    # Test
    test_durations = [3.5, 12.0, 2.5, 8.5, 4.0]
    print(f"Original: {test_durations}")
    print(f"Total: {sum(test_durations):.1f}s")
    
    optimized = optimize_scene_durations(test_durations)
    print(f"\nOptimized: {[f'{d:.1f}' for d in optimized]}")
    print(f"Total: {sum(optimized):.1f}s")
    
    analysis = validate_pacing(optimized)
    print(f"\nPacing: {analysis}")
