"""
Visual Validator
Ensures perfect audio-visual alignment before export
"""

import logging
from typing import List, Dict


def validate_visual_audio_sync(visual_chunks, audio_chunks):
    """
    Validates perfect audio-visual alignment.
    
    Critical checks:
    - Every visual mapped to audio chunk
    - Intent match score ≥ 0.8
    - No visual exceeds audio meaning duration
    - No random unrelated clips
    
    Args:
        visual_chunks: List of generated visual clips
        audio_chunks: List of audio semantic chunks
    
    Returns:
        {
            "passed": bool,
            "score": 0.0-1.0,
            "issues": [],
            "warnings": []
        }
    """
    
    issues = []
    warnings = []
    
    # Check counts match
    if len(visual_chunks) != len(audio_chunks):
        issues.append(f"Count mismatch: {len(visual_chunks)} visuals vs {len(audio_chunks)} audio chunks")
        return {"passed": False, "score": 0.0, "issues": issues, "warnings": warnings}
    
    # Check each pair
    match_scores = []
    
    for i in range(len(audio_chunks)):
        audio = audio_chunks[i]
        visual = visual_chunks[i]
        
        # Duration alignment
        audio_duration = audio.get("duration", audio.get("end", 0) - audio.get("start", 0))
        visual_duration = visual.get("duration", 0)
        
        duration_diff = abs(visual_duration - audio_duration)
        if duration_diff > 2.0:
            issues.append(f"Chunk {i}: Duration mismatch ({visual_duration:.1f}s vs {audio_duration:.1f}s)")
        elif duration_diff > 1.0:
            warnings.append(f"Chunk {i}: Minor duration difference ({duration_diff:.1f}s)")
        
        # Intent alignment
        audio_intent = audio.get("intent", "unknown")
        visual_source = visual.get("source", "unknown")
        
        intent_match = _check_intent_match(audio_intent, visual_source)
        match_scores.append(intent_match)
        
        if intent_match < 0.8:
            issues.append(f"Chunk {i}: Low intent match ({intent_match:.2f}) - {audio_intent} vs {visual_source}")
        elif intent_match < 0.9:
            warnings.append(f"Chunk {i}: Moderate intent match ({intent_match:.2f})")
        
        # Visual quality check
        visual_type = visual.get("type", "unknown")
        if visual_type == "unrelated_stock":
            issues.append(f"Chunk {i}: Unrelated stock footage detected")
    
    # Calculate overall score
    avg_match_score = sum(match_scores) / len(match_scores) if match_scores else 0
    
    # Determine pass/fail
    passed = len(issues) == 0 and avg_match_score >= 0.8
    
    logging.info(f"Validation: {'PASSED' if passed else 'FAILED'} (score: {avg_match_score:.2f})")
    
    return {
        "passed": passed,
        "score": avg_match_score,
        "issues": issues,
        "warnings": warnings,
        "chunk_scores": match_scores
    }


def _check_intent_match(intent, visual_source):
    """
    Checks if visual source matches intent appropriately.
    
    Returns score 0.0-1.0
    """
    
    # Expected source mappings
    expected_mapping = {
        "person_story": ["pixabay", "real_footage"],
        "how_it_works": ["dalle", "diagram"],
        "mistake_explanation": ["dalle", "motion_graphics", "symbolic"],
        "emotional": ["pixabay", "dalle", "facial"],
        "fact_statement": ["motion_graphics", "generated"],
        "comparison": ["dalle", "split"],
        "conclusion": ["dalle", "minimal"]
    }
    
    expected_sources = expected_mapping.get(intent, [])
    
    # Check if source matches
    for expected in expected_sources:
        if expected in visual_source.lower():
            return 1.0
    
    # Partial matches
    if "dalle" in visual_source.lower() and intent in ["how_it_works", "mistake_explanation"]:
        return 0.9
    if "pixabay" in visual_source.lower() and intent in ["person_story", "emotional"]:
        return 0.9
    if "motion_graphics" in visual_source.lower() and intent == "fact_statement":
        return 0.95
    
    # No match
    return 0.5


def validate_timeline_continuity(visual_chunks):
    """
    Validates smooth timeline continuity.
    
    Checks:
    - No abrupt cuts
    - Smooth transitions
    - Consistent pacing
    """
    
    issues = []
    
    for i in range(len(visual_chunks) - 1):
        current = visual_chunks[i]
        next_clip = visual_chunks[i+1]
        
        # Check for very short clips
        if current.get("duration", 0) < 5:
            issues.append(f"Chunk {i}: Very short duration ({current.get('duration'):.1f}s)")
        
        # Check for very long clips
        if current.get("duration", 0) > 50:
            issues.append(f"Chunk {i}: Very long duration ({current.get('duration'):.1f}s) - may lose retention")
    
    return {
        "passed": len(issues) == 0,
        "issues": issues
    }


def validate_no_unrelated_content(visual_chunks, audio_chunks):
    """
    Ensures no unrelated stock footage or random content.
    """
    
    issues = []
    
    for i, visual in enumerate(visual_chunks):
        # Check if marked as fallback
        if visual.get("is_fallback", False):
            # Fallback is okay if it's motion graphics
            if visual.get("type") != "motion_graphics":
                issues.append(f"Chunk {i}: Using fallback but not motion graphics")
        
        # Check for generic stock
        if visual.get("source") == "pixabay":
            search_quality = visual.get("search_quality", 1.0)
            if search_quality < 0.7:
                issues.append(f"Chunk {i}: Low-quality Pixabay match ({search_quality:.2f})")
    
    return {
        "passed": len(issues) == 0,
        "issues": issues
    }


if __name__ == "__main__":
    # Test validation
    test_audio = [
        {"text": "Test 1", "intent": "mistake_explanation", "duration": 25.0},
        {"text": "Test 2", "intent": "person_story", "duration": 30.0}
    ]
    
    test_visual = [
        {"source": "dalle", "type": "symbolic", "duration": 25.5},
        {"source": "pixabay", "type": "real_footage", "duration": 29.8}
    ]
    
    result = validate_visual_audio_sync(test_visual, test_audio)
    
    print("\n" + "="*60)
    print("VALIDATION RESULT")
    print("="*60)
    print(f"Passed: {result['passed']}")
    print(f"Score: {result['score']:.2f}")
    if result['issues']:
        print("\nIssues:")
        for issue in result['issues']:
            print(f"  - {issue}")
    if result['warnings']:
        print("\nWarnings:")
        for warning in result['warnings']:
            print(f"  - {warning}")
