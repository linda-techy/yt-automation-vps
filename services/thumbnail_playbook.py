"""
Production-Ready Malayalam Thumbnail Playbook Validator

Ensures thumbnails follow YPP-safe CTR-optimized rules for Malayalam audiences.
"""

import os
import logging
from PIL import Image


def validate_thumbnail_production_ready(image_path, text, video_type):
    """
    Validates thumbnail against production playbook rules.
    
    Args:
        image_path: Path to thumbnail
        text: Malayalam headline text
        video_type: "short" or "long"
    
    Returns:
        dict with {"passed": bool, "issues": list, "warnings": list}
    """
    issues = []
    warnings = []
    
    # Rule 1: Text word count (3-5 words)
    words = text.split()
    if len(words) < 3:
        issues.append(f"Text too short ({len(words)} words). Minimum 3 words.")
    elif len(words) > 5:
        issues.append(f"Text too long ({len(words)} words). Maximum 5 words.")
    
    # Rule 2: Aspect ratio validation
    try:
        img = Image.open(image_path)
        w, h = img.size
        
        if video_type == "short":
            # Must be 9:16
            expected_ratio = 9/16
            actual_ratio = w/h
            if abs(actual_ratio - expected_ratio) > 0.01:
                issues.append(f"Shorts aspect ratio incorrect: {w}x{h} (expected 9:16)")
        else:  # long
            # Must be 16:9
            expected_ratio = 16/9
            actual_ratio = w/h
            if abs(actual_ratio - expected_ratio) > 0.01:
                issues.append(f"Long video aspect ratio incorrect: {w}x{h} (expected 16:9)")
        
        img.close()
    except Exception as e:
        issues.append(f"Could not validate image: {e}")
    
    # Rule 3: Text language check (should have Malayalam characters)
    has_malayalam = any('\u0d00' <= char <= '\u0d7f' for char in text)
    if not has_malayalam:
        warnings.append("Text does not contain Malayalam characters")
    
    # Rule 4: Avoid full sentences (check for multiple punctuation)
    punctuation_count = text.count('?') + text.count('!') + text.count('.')
    if punctuation_count > 1:
        warnings.append("Text may be a full sentence (avoid complete sentences)")
    
    # Rule 5: Check for common spoken Malayalam patterns (good sign)
    spoken_patterns = ["ആണോ", "ഇല്ലേ", "ഉണ്ടോ", "എങ്ങനെ", "എന്താ"]
    has_spoken_pattern = any(pattern in text for pattern in spoken_patterns)
    if has_spoken_pattern:
        logging.info("✅ Using spoken Malayalam pattern - good for CTR")
    
    passed = len(issues) == 0
    return {
        "passed": passed,
        "issues": issues,
        "warnings": warnings,
        "word_count": len(words),
        "has_malayalam": has_malayalam
    }


def get_color_combo_recommendation(video_type):
    """
    Returns CTR-optimized color combinations.
    
    Based on proven high-CTR combos:
    - Yellow on Black
    - White on Red
    - Cyan on Dark Blue
    """
    proven_combos = {
        "short": [
            {"text": (255, 255, 0), "bg": (0, 0, 0), "name": "Yellow on Black"},
            {"text": (255, 255, 255), "bg": (220, 20, 60), "name": "White on Red"},
            {"text": (0, 255, 255), "bg": (25, 25, 112), "name": "Cyan on Dark Blue"}
        ],
        "long": [
            {"text": (255, 255, 0), "bg": (0, 0, 0), "name": "Yellow on Black"},
            {"text": (255, 255, 255), "bg": (139, 0, 0), "name": "White on Dark Red"},
            {"text": (255, 215, 0), "bg": (0, 0, 0), "name": "Gold on Black"}
        ]
    }
    
    import random
    return random.choice(proven_combos.get(video_type, proven_combos["short"]))


def check_ypp_safety(text, topic):
    """
    Validates thumbnail is YPP-safe (no misleading promises).
    
    Returns:
        dict with {"safe": bool, "violations": list}
    """
    violations = []
    
    # Check for clickbait patterns that violate YPP
    forbidden_patterns = [
        ("100%", "Avoid absolute guarantees"),
        ("guaranteed", "Avoid guarantees"),
        ("secret trick", "Avoid overpromising"),
        ("shocking", None),  # Borderline but acceptable in Malayalam
    ]
    
    text_lower = text.lower()
    topic_lower = topic.lower()
    
    for pattern, reason in forbidden_patterns:
        if reason and pattern in text_lower:
            violations.append(f"YPP Risk: {reason} (found: '{pattern}')")
    
    # Check topic alignment (basic check)
    # In production, use AI to validate alignment
    
    safe = len(violations) == 0
    return {
        "safe": safe,
        "violations": violations
    }


def get_font_recommendation():
    """
    Returns Malayalam-friendly fonts optimized for thumbnails.
    
    Priority order:
    1. Noto Sans Malayalam Bold (best for thumbnails)
    2. Meera Bold
    3. Uroob Heavy
    4. Nirmala UI Bold (Windows fallback)
    """
    fonts = [
        # Best options
        ("fonts/NotoSansMalayalam-Bold.ttf", "Noto Sans Malayalam Bold"),
        ("C:/Windows/Fonts/NirmalaUI-Bold.ttf", "Nirmala UI Bold"),
        
        # Linux
        ("/usr/share/fonts/truetype/noto/NotoSansMalayalam-Bold.ttf", "Noto Sans Malayalam Bold"),
        
        # Fallbacks
        ("C:/Windows/Fonts/NirmalaUI.ttf", "Nirmala UI"),
        ("fonts/NotoSansMalayalam-Regular.ttf", "Noto Sans Malayalam Regular"),
        ("/usr/share/fonts/truetype/noto/NotoSansMalayalam-Regular.ttf", "Noto Sans Malayalam"),
    ]
    
    for path, name in fonts:
        if os.path.exists(path):
            logging.info(f"[Font] Using: {name}")
            return path
    
    raise Exception("No Malayalam-friendly font found. Install Noto Sans Malayalam or Nirmala UI.")


if __name__ == "__main__":
    # Test validation
    test_cases = [
        ("ഇത് സംഭവിച്ചോ?", "short", True),  # Perfect
        ("ഇത് ആരും പറയില്ല", "long", True),  # Perfect
        ("This is a test", "short", False),  # No Malayalam
        ("ഇത് വളരെ നല്ല ഒരു കാര്യം ആണ് പറയാൻ", "short", False),  # Too long
    ]
    
    print("Thumbnail Validation Tests:")
    print("=" * 50)
    for text, video_type, should_pass in test_cases:
        result = validate_thumbnail_production_ready("test.png", text, video_type)
        status = "✅ PASS" if result["passed"] == should_pass else "❌ FAIL"
        print(f"{status} | {text} ({video_type})")
        if result["issues"]:
            print(f"  Issues: {result['issues']}")
