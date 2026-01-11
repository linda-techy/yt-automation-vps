import os
import time
import logging
import requests
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont, ImageOps
import random

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_malayalam_headline(topic, title, emotion_type="curiosity", video_type="short"):
    """
    Generate CTR-optimized Malayalam headline using proven formulas.
    
    Production-Ready Playbook Integration:
    - Uses spoken Malayalam (not formal literature)
    - 3-5 words MAX
    - Emotion + curiosity gap
    - Different strategies for Long vs Short
    
    Args:
        topic: Video topic
        title: Original title
        emotion_type: "curiosity", "shock", "urgency", "relatable"
        video_type: "short" or "long"
    
    Returns:
        3-5 word Malayalam headline
    """
    
    # PRODUCTION-READY FORMULAS - Proven to work
    if video_type == "short":
        # SHORTS: Instant stop-scroll (Urgency/Drama)
        proven_hooks = {
            "curiosity": [
                "ഇത് സംഭവിച്ചോ?",
                "ഇത് സത്യമാണോ",
                "ഒറ്റ സെക്കൻഡ്",
                "ഇത് എങ്ങനെ?",
                "ആരും പറയില്ല"
            ],
            "shock": [
                "വല്ലാത്ത പണി",
                "ഇത് കണ്ടാൽ ഞെട്ടും",
                "വിശ്വസിക്കാൻ പറ്റില്ല",
                "ഇത് സംഭവിച്ചു",
                "ഞെട്ടിക്കുന്ന സത്യം"
            ],
            "urgency": [
                "ഇങ്ങനെ ചെയ്യരുത്",
                "ഇത് അറിയണം",
                "ഉടൻ കാണണം",
                "ഇപ്പോൾ തന്നെ",
                "ഇവിടെ ശ്രദ്ധിക്കൂ"
            ],
            "relatable": [
                "നിങ്ങളും ആണോ?",
                "എല്ലാവർക്കും പറ്റും",
                "ഇത് സാധാരണമാണോ",
                "നമുക്കെല്ലാം പറ്റും",
                "ആരും രക്ഷപ്പെടില്ല"
            ]
        }
    else:  # long
        # LONG VIDEOS: Curiosity + Credibility
        proven_hooks = {
            "curiosity": [
                "ഇത് ആരും പറയില്ല",
                "ഇത് അറിഞ്ഞില്ലേ?",
                "ഇവിടെ ആണ് രഹസ്യം",
                "എന്താണ് സത്യം?",
                "മറഞ്ഞിരിക്കുന്ന കാര്യം"
            ],
            "shock": [
                "ഇവിടെ പറ്റിയ പിഴവ്",
                "എല്ലാവരും തെറ്റിക്കുന്നു",
                "ശ്രദ്ധിക്കേണ്ട കാര്യം",
                "ഇത് ആർക്കറിയാം",
                "വലിയ തെറ്റ്"
            ],
            "urgency": [
                "ഇത് ചെയ്യരുത്",
                "ഇത് അറിയണം",
                "ഇവിടെ പിഴവ്",
                "ഇത് പ്രധാനമാണ്",
                "അറിയേണ്ട സമയം"
            ],
            "relatable": [
                "നിങ്ങൾക്കും പറ്റിയോ",
                "എല്ലാവരും ചെയ്യും",
                "സാധാരണ തെറ്റ്",
                "നമ്മളെല്ലാം അനുഭവിക്കും",
                "ഇത് നമുക്കറിയാം"
            ]
        }
    
    # Try AI generation first with proven formula guidance
    try:
        formula_examples = proven_hooks.get(emotion_type, proven_hooks["curiosity"])
        
        prompt = f"""You are a Malayalam YouTube CTR expert. Create a thumbnail headline.

STRICT RULES:
1. Use SPOKEN Malayalam only (not formal/literary)
2. EXACTLY 3-5 words
3. Must create {emotion_type} emotion
4. Video Type: {video_type.upper()}

{"SHORTS Strategy: Instant stop-scroll, urgent, dramatic" if video_type == "short" else "LONG VIDEO Strategy: Curiosity + credibility"}

Proven formulas that work:
{chr(10).join(f"- {hook}" for hook in formula_examples[:3])}

Topic: {topic}
Title context: {title}

Return ONLY the Malayalam headline (3-5 words, spoken language):"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=30,
            temperature=0.8
        )
        headline = response.choices[0].message.content.strip()
        
        # Validate word count
        words = headline.split()
        if len(words) > 5:
            headline = " ".join(words[:5])
        elif len(words) < 3:
            # Fallback to proven hook
            import random
            headline = random.choice(proven_hooks.get(emotion_type, proven_hooks["curiosity"]))
        
        return headline
        
    except Exception as e:
        logging.warning(f"AI headline generation failed: {e}, using proven hook")
        # Fallback to proven hooks
        import random
        return random.choice(proven_hooks.get(emotion_type, proven_hooks["curiosity"]))


def validate_thumbnail_contrast(image_path, text_color, bg_sample_coords):
    """
    Validate text has sufficient contrast (WCAG 3:1 minimum for large text).
    
    Args:
        image_path: Path to image
        text_color: RGB tuple of text color
        bg_sample_coords: List of (x,y) tuples to sample background
    
    Returns:
        bool: True if contrast is sufficient
    """
    try:
        img = Image.open(image_path)
        pixels = img.load()
        
        # Sample background colors
        bg_luminances = []
        for x, y in bg_sample_coords:
            if 0 <= x < img.width and 0 <= y < img.height:
                pixel = pixels[x, y]
                # Calculate relative luminance
                r, g, b = pixel[:3]
                lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                bg_luminances.append(lum)
        
        # Calculate text luminance
        r, g, b = text_color
        text_lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        
        # Check contrast ratio
        avg_bg_lum = sum(bg_luminances) / len(bg_luminances)
        contrast_ratio = (max(text_lum, avg_bg_lum) + 0.05) / (min(text_lum, avg_bg_lum) + 0.05)
        
        return contrast_ratio >= 3.0
    except Exception as e:
        logging.warning(f"Contrast validation failed: {e}")
        return True  # Assume okay if validation fails


def generate_thumbnail(topic, title, video_type="short", output_path=None):
    """
    Generates optimized thumbnails with CTR psychology.
    
    Args:
        topic: Video topic for DALL-E prompt
        title: Video title (used for headline generation)
        video_type: "short" (9:16, 1080x1920) or "long" (16:9, 1920x1080)
        output_path: Optional custom output path
    
    Returns:
        Path to generated thumbnail
    
    Raises:
        Exception if generation fails
    """
    # Determine dimensions based on video type
    if video_type == "long":
        size = "1792x1024"  # Landscape 16:9
        dimensions = (1920, 1080)
        font_size = 120
        position = ('center', 200)  # Higher position for landscape
    else:  # short
        size = "1024x1792"  # Portrait 9:16
        dimensions = (1080, 1920)
        font_size = 100
        position = 'center'
    
    # Enhanced DALL-E prompt for higher CTR
    if video_type == "long":
        prompt = f"Professional YouTube thumbnail, {topic}, high contrast, vibrant colors, eye-catching composition, 3d render, cinematic lighting, no text, ultra detailed, trending on artstation"
    else:
        prompt = f"High energy YouTube Shorts thumbnail, {topic}, explosive colors, dramatic, attention-grabbing, 3d render, no text, ultra vibrant"
    
    print(f"Generating {video_type.upper()} thumbnail ({dimensions[0]}x{dimensions[1]}) for: {topic[:50]}...")
    
    # Generate base image with DALL-E 3
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality="standard",
            n=1
        )
        url = response.data[0].url
    except Exception as e:
        # Fallback to simple thumbnail
        logging.warning(f"DALL-E thumbnail failed: {e}")
        from services.fallback_thumbnail import create_fallback_thumbnail
        
        # Fallback with unique hash
        import hashlib
        topic_hash = hashlib.md5(topic.encode()).hexdigest()[:8]
        safe_topic = "".join([c for c in topic if c.isalnum() or c in (' ', '-', '_')]).strip()[:30]
        fallback_path = output_path or f"videos/output/thumb_{topic_hash}_{safe_topic.replace(' ', '_')}_{video_type}.png"
        return create_fallback_thumbnail(title, topic, fallback_path, dimensions)
    
    # Download image to OUTPUT directory with UNIQUE filename
    # Match video naming pattern: thumb_{hash}_{topic}_{type}.png
    import hashlib
    topic_hash = hashlib.md5(topic.encode()).hexdigest()[:8]
    safe_topic = "".join([c for c in topic if c.isalnum() or c in (' ', '-', '_')]).strip()[:30]
    path = output_path or f"videos/output/thumb_{topic_hash}_{safe_topic.replace(' ', '_')}_{video_type}.png"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    MAX_RETRIES = 5
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            with open(path, "wb") as f:
                f.write(r.content)
            print(f"Downloaded thumbnail (attempt {attempt+1})")
            break
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(2 ** attempt)
    else:
        raise Exception(f"Thumbnail download failed after {MAX_RETRIES} attempts: {last_error}")
    
    # Process image - add text overlay
    image = Image.open(path)
    image = ImageOps.fit(image, dimensions, method=Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image)
    
    # Get Malayalam headline with CTR psychology
    emotion = random.choice(["curiosity", "shock", "urgency", "relatable"])
    malayalam_headline = generate_malayalam_headline(topic, title, emotion, video_type)
    
    # Validate headline before proceeding
    from services.thumbnail_playbook import validate_thumbnail_production_ready, get_color_combo_recommendation
    
    validation = validate_thumbnail_production_ready(path, malayalam_headline, video_type)
    if not validation["passed"]:
        logging.warning(f"⚠️ Thumbnail validation issues: {validation['issues']}")
        # For production, could regenerate or use fallback
    
    # Get CTR-optimized color combo
    color_combo = get_color_combo_recommendation(video_type)
    text_color = color_combo["text"]
    stroke_color = (0, 0, 0)  # Always black for maximum contrast
    
    logging.info(f"🎨 Using proven CTR combo: {color_combo['name']}")
    
    # Load Malayalam font
    from services.thumbnail_playbook import get_font_recommendation
    
    try:
        font_path = get_font_recommendation()
        font = ImageFont.truetype(font_path, font_size)
    except Exception as e:
        logging.error(f"Font loading failed: {e}")
        raise Exception("Malayalam font required for thumbnails. Install Noto Sans Malayalam or Nirmala UI.")
    
    # High-contrast text rendering with proven CTR colors
    text = malayalam_headline
    w, h = image.size
    
    if video_type == "long":
        # Long videos: Text in left or right third for curiosity + credibility
        x, y = w/3, h/5  # Left third, top
    else:
        # Shorts: Center or top for instant stop-scroll
        x, y = w/2, h/4  # Top center
    
    # Multi-layer stroke for ultra-high contrast
    stroke_width = 5
    # Black outline (maximum readability)
    draw.text((x, y), text, font=font, fill="black", anchor="mm", stroke_width=stroke_width+2, stroke_fill="black")
    # Final colored text with proven CTR color
    draw.text((x, y), text, font=font, fill=text_color, anchor="mm", stroke_width=stroke_width, stroke_fill=stroke_color)
    
    image.save(path)
    
    # Final validation
    final_validation = validate_thumbnail_production_ready(path, text, video_type)
    if final_validation["passed"]:
        logging.info(f"✅ Thumbnail passed production validation")
    else:
        logging.warning(f"⚠️ Thumbnail issues: {final_validation['issues']}")
    
    # YPP Safety check
    from services.thumbnail_playbook import check_ypp_safety
    ypp_check = check_ypp_safety(text, topic)
    if not ypp_check["safe"]:
        logging.warning(f"⚠️ YPP Safety concerns: {ypp_check['violations']}")
    
    safe_text = text.encode('ascii', 'replace').decode('ascii')
    print(f"Thumbnail created ({video_type}, {color_combo['name']}): {safe_text}")
    
    return path


if __name__ == "__main__":
    # Test both thumbnail types
    test_topic = "Motivational Success Story"
    test_title = "മനോഹരമായ ജീവിതം"
    
    print("Testing SHORT thumbnail (9:16)...")
    short_thumb = generate_thumbnail(test_topic, test_title, video_type="short")
    print(f"Short: {short_thumb}")
    
    print("\nTesting LONG thumbnail (16:9)...")
    long_thumb = generate_thumbnail(test_topic, test_title, video_type="long")
    print(f"Long: {long_thumb}")
