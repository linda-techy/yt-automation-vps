"""
Retention Optimizer - YPP Compliance & Viewer Engagement

This module validates and optimizes videos for:
- First 3-second hook effectiveness
- Pacing and scene variety
- Content uniqueness (avoiding "reused content" flags)
- Retention-optimized structure
"""

import logging
from moviepy.editor import VideoFileClip
import json


def validate_first_3_seconds(video_path):
    """
    Validates the first 3 seconds have a strong hook.
    
    Returns:
        dict with {"passed": bool, "issues": list}
    """
    issues = []
    
    try:
        clip = VideoFileClip(video_path)
        
        # Check video has at least 3 seconds
        if clip.duration < 3:
            issues.append("Video too short (< 3 seconds)")
            return {"passed": False, "issues": issues}
        
        # For now, just validate duration exists
        # In future: analyze first frame for visual interest, check audio levels
        logging.info(f"✅ First 3 seconds: {clip.duration:.1f}s total duration")
        
        clip.close()
        
    except Exception as e:
        issues.append(f"Failed to analyze video: {e}")
        return {"passed": False, "issues": issues}
    
    return {"passed": True, "issues": []}


def validate_scene_variety(scene_durations, transformation_log=None):
    """
    Validates pacing and visual variety.
    
    Args:
        scene_durations: List of scene durations in seconds
        transformation_log: Optional list of transformation profiles used
    
    Returns:
        dict with {"passed": bool, "issues": list, "recommendations": list}
    """
    issues = []
    recommendations = []
    
    # Check scene pacing
    if not scene_durations:
        issues.append("No scene data available")
        return {"passed": False, "issues": issues, "recommendations": []}
    
    # Ensure scenes are 3-8 seconds (optimal retention)
    long_scenes = [i for i, dur in enumerate(scene_durations) if dur > 8]
    short_scenes = [i for i, dur in enumerate(scene_durations) if dur < 2]
    
    if long_scenes:
        issues.append(f"{len(long_scenes)} scenes exceed 8 seconds (scenes: {long_scenes[:5]})")
    
    if short_scenes:
        recommendations.append(f"{len(short_scenes)} scenes under 2 seconds may feel rushed")
    
    # Check for variety in transformations
    if transformation_log:
        unique_profiles = len(set(transformation_log))
        if unique_profiles < 2:
            issues.append("Low visual variety - only single transformation profile used")
        elif unique_profiles >= 3:
            logging.info(f"✅ Good visual variety: {unique_profiles} different profiles")
    
    passed = len(issues) == 0
    return {
        "passed": passed,
        "issues": issues,
        "recommendations": recommendations
    }


def validate_content_uniqueness(script_data, visual_assets):
    """
    Validates content adds unique value (YPP requirement).
    
    Checks:
    - Script is not just narrating stock footage
    - Visual transformations are applied
    - Custom commentary/analysis present
    
    Returns:
        dict with {"passed": bool, "issues": list}
    """
    issues = []
    
    # Check script has unique commentary
    script_text = ""
    if isinstance(script_data, dict):
        sections = script_data.get('sections', [])
        script_text = " ".join([s.get('content', '') for s in sections])
    elif isinstance(script_data, str):
        script_text = script_data
    
    if len(script_text) < 100:
        issues.append("Script too short - may lack unique value")
    
    # Check visual assets
    if not visual_assets or len(visual_assets) < 5:
        issues.append("Too few visual assets - video may feel repetitive")
    
    # In a full implementation, we'd also check:
    # - Audio has clear commentary (not just music)
    # - Graphics overlays are present
    # - Content structure follows narrative arc
    
    passed = len(issues) == 0
    return {"passed": passed, "issues": issues}


def validate_retention_structure(video_path, script_data, scene_durations=None):
    """
    Main validation function - checks all retention criteria.
    
    Args:
        video_path: Path to final video
        script_data: Script dict or string
        scene_durations: Optional list of scene durations
    
    Returns:
        dict with validation results
    """
    results = {
        "passed": True,
        "checks": {},
        "all_issues": [],
        "recommendations": []
    }
    
    # 1. First 3-second hook
    hook_result = validate_first_3_seconds(video_path)
    results["checks"]["hook"] = hook_result
    if not hook_result["passed"]:
        results["passed"] = False
        results["all_issues"].extend(hook_result["issues"])
    
    # 2. Scene variety (if data available)
    if scene_durations:
        variety_result = validate_scene_variety(scene_durations)
        results["checks"]["variety"] = variety_result
        if not variety_result["passed"]:
            results["passed"] = False
            results["all_issues"].extend(variety_result["issues"])
        results["recommendations"].extend(variety_result.get("recommendations", []))
    
    # 3. Content uniqueness
    uniqueness_result = validate_content_uniqueness(script_data, [])
    results["checks"]["uniqueness"] = uniqueness_result
    if not uniqueness_result["passed"]:
        results["passed"] = False
        results["all_issues"].extend(uniqueness_result["issues"])
    
    # Summary
    if results["passed"]:
        logging.info("✅ Retention validation PASSED - Video is YPP-compliant")
    else:
        logging.warning(f"⚠️ Retention issues found: {results['all_issues']}")
    
    return results


def optimize_hook_placement(script_sections):
    """
    Reorders script sections to ensure strongest hook is first.
    
    Args:
        script_sections: List of script section dicts
    
    Returns:
        Reordered list with best hook first
    """
    # Hook indicators (questions, shocking statements, bold claims)
    hook_keywords = [
        "?", "shocking", "revealed", "secret", "never", "don't know",
        "ഞെട്ടിക്കുന്ന", "രഹസ്യം", "അറിയാതെ"  # Malayalam hook words
    ]
    
    # Score each section for hook potential
    scored_sections = []
    for i, section in enumerate(script_sections):
        content = section.get('content', '').lower()
        title = section.get('title', '').lower()
        score = 0
        
        # Check for hook keywords
        for keyword in hook_keywords:
            if keyword in content or keyword in title:
                score += 1
        
        # First section bonus (usually designed as hook)
        if i == 0:
            score += 2
        
        scored_sections.append((score, section))
    
    # Sort by score (descending)
    scored_sections.sort(key=lambda x: x[0], reverse=True)
    
    # Return reordered (but in practice, we usually keep original order if hook is already first)
    return [s[1] for s in scored_sections]


if __name__ == "__main__":
    # Test validation
    test_video = "videos/output/test.mp4"
    test_script = {
        "sections": [
            {"title": "Hook", "content": "ഇത് നിങ്ങൾക്കറിയാമോ? This shocking secret will change everything!"},
            {"title": "Body", "content": "Let me explain the full context behind this revelation..."}
        ]
    }
    
    result = validate_retention_structure(test_video, test_script, [3.5, 4.2, 3.8])
    print(json.dumps(result, indent=2))
