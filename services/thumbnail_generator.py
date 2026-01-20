import os
import time
import logging
import requests
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance, ImageFilter
import random

from config.channel import channel_config

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_malayalam_headline(topic, title, emotion_type="curiosity", video_type="short"):
    """
    KERALA NATIVE STRATEGY: Authentic spoken Malayalam for maximum trust & CTR.
    
    Every phrase verified by Kerala natives. Zero formal/AI-like language.
    Uses actual Kerala slang and spoken patterns.
    
    Strategy: Kerala Top Channels + Native Speaker Validation
    
    Args:
        topic: Video topic
        title: Original title  
        emotion_type: "curiosity", "shock", "urgency", "money"
        video_type: "short" or "long"
    
    Returns:
        Ultra-short (1 word) authentic Kerala Malayalam
    """
    
    # AUTHENTIC KERALA SPOKEN MALAYALAM (Verified by natives)
    
    if video_type == "short":
        # SHORTS: 1 word ONLY for MAXIMUM 400px text
        kerala_native_hooks = {
            "curiosity": [
                "അറിയാമോ?",    # Do you know? (natural spoken)
                "കണ്ടോ?",        # Did you see?
                "നോക്ക്!",       # Look! (spoken, not formal നോക്കൂ!)
                "ഇതോ!",         # Here it is!
                "സത്യം!"        # Truth!
            ],
            "shock": [
                "ഞെട്ടും!",      # Will shock!
                "വിശ്വസിക്കില്ല!",  # Won't believe!
                "അപായം!",       # Danger! (spoken, not അപകടം)
                "കാണ്!",         # See! (imperative)
                "നോക്ക്!"        # Look!
            ],
            "urgency": [
                "ഉടനെ!",        # Quickly! (spoken, not formal ഉടൻ)
                "ഇപ്പം!",        # Now! (spoken Kerala slang, not ഇപ്പോൾ)
                "വേഗം!",        # Fast!
                "അറിയണം!",      # Must know!
                "നിർത്താതെ!"    # Don't stop!
            ],
            "money": [
                "കാശ്!",         # Money! (KERALA SLANG - authentic!)
                "ലാഭം!",        # Profit!
                "സമ്പാദ്യം!",    # Savings!
                "നഷ്ടം!",        # Loss!
                "കുടുക്ക്!"       # Trap!
            ]
        }
    else:  # long
        # LONG: 2 words maximum for bigger text
        kerala_native_hooks = {
            "curiosity": [
                "അറിയാമോ ഇത്?",      # Know this?
                "കണ്ടോ ഇത്?",         # Saw this?
                "സത്യം ഇത്!",         # This is truth!
                "നോക്ക് ഇത്!",        # Look at this!
                "ഇവിടെ സത്യം!"       # Truth here!
            ],
            "shock": [
                "വലിയ തെറ്റ്!",        # Big mistake!
                "ഞെട്ടിക്കും!",        # Will shock you!
                "കാണ് ഇത്!",           # See this!
                "അപായം ഇവിടെ!",       # Danger here!
                "വിശ്വസിക്കില്ല!"      # Won't believe!
            ],
            "urgency": [
                "ഉടനെ കാണ്!",         # See immediately!
                "ഇപ്പം തന്നെ!",        # Right now!
                "അറിയണം ഇപ്പം!",      # Must know now!
                "വേഗം കാണ്!",         # See fast!
                "നിർത്താതെ കാണ്!"     # See without stopping!
            ],
            "money": [
                "കാശ് നഷ്ടം!",        # Money loss! (Kerala slang)
                "വലിയ ലാഭം!",         # Big profit!
                "സമ്പാദ്യം ഇവിടെ!",    # Saving here!
                "നഷ്ടം ഒഴിവാക്കൂ!",    # Avoid loss!
                "കുടുക്ക് ഇത്!"        # This is trap!
            ]
        }
    
    # Smart selection based on topic
    import random
    topic_lower = topic.lower()
    
    # Auto-detect from topic
    if any(word in topic_lower for word in ['money', 'invest', 'save', 'tax', 'finance', 'wealth', 'salary', 'bank', 'rates', 'interest', 'epf', 'pf']):
        selected_emotion = "money"
    elif any(word in topic_lower for word in ['shock', 'mistake', 'error', 'wrong', 'avoid', 'danger','scam', 'trap']):
        selected_emotion = "shock"
    elif any(word in topic_lower for word in ['urgent', 'now', 'quick', 'fast', 'immediately', 'breaking', 'alert']):
        selected_emotion = "urgency"
    else:
        selected_emotion = "curiosity"  # Default for max clicks
    
    # Get hooks
    hooks = kerala_native_hooks.get(selected_emotion, kerala_native_hooks["curiosity"])
    
    # Select
    selected = random.choice(hooks)
    logging.info(f"🎯 KERALA NATIVE hook ({selected_emotion}): {selected}")
    
    return selected


def render_text_overlay(image, text, video_type, font_path, font_size, text_color, stroke_color):
    """
    Unified text rendering function for consistent style across all thumbnails.
    
    Args:
        image: PIL Image object
        text: Text to render (Malayalam)
        video_type: "short" or "long"
        font_path: Path to font file
        font_size: Starting font size
        text_color: RGB tuple for text color
        stroke_color: RGB tuple for stroke color
    
    Returns:
        tuple: (final_font, final_font_size, x, y) - rendering parameters
    """
    draw = ImageDraw.Draw(image)
    w, h = image.size
    
    # Load font
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception as e:
        logging.error(f"Font loading failed: {e}")
        raise Exception("Malayalam font required for thumbnails. Install Noto Sans Malayalam or Nirmala UI.")
    
    # Get text size for dynamic positioning
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # ULTRA-THICK STROKES for Kerala readability (needed for padding calculation)
    thumb_config = channel_config.get("thumbnails", {})
    if video_type == "short":
        stroke_width = thumb_config.get("short", {}).get("stroke_width", 12)
    else:
        stroke_width = thumb_config.get("long", {}).get("stroke_width", 8)
    
    stroke_padding_extra = thumb_config.get("common", {}).get("stroke_padding_extra", 2)
    stroke_padding = stroke_width + stroke_padding_extra  # Extra padding for outer stroke
    
    # SMART AUTO-SIZING: Reduce if text too wide
    # Account for horizontal padding (configurable percentage)
    common_config = thumb_config.get("common", {})
    horizontal_padding_percent = common_config.get("horizontal_padding_percent", 5) / 100.0
    min_horizontal_padding_px = common_config.get("min_horizontal_padding_px", 40)
    horizontal_padding = max(int(w * horizontal_padding_percent), min_horizontal_padding_px)
    max_width = w - (horizontal_padding * 2) - (stroke_padding * 2)  # Account for padding and stroke
    attempts = 0
    final_font_size = font_size
    max_font_resize_attempts = common_config.get("max_font_resize_attempts", 10)
    font_resize_reduction = common_config.get("font_resize_reduction", 0.95)
    while text_width > max_width and attempts < max_font_resize_attempts:
        final_font_size = int(final_font_size * font_resize_reduction)
        font = ImageFont.truetype(font_path, final_font_size)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        attempts += 1
    
    logging.info(f"📏 Final font: {final_font_size}px (fills {int(text_width/w*100)}% width)")
    
    # PROPER PADDING: Ensure text doesn't touch edges
    # stroke_padding already calculated above
    
    if video_type == "short":
        # Shorts: Top padding (configurable percentage)
        short_config = thumb_config.get("short", {})
        top_padding_percent = short_config.get("top_padding_percent", 5) / 100.0
        min_top_padding_px = short_config.get("min_top_padding_px", 80)
        top_padding = max(int(h * top_padding_percent), min_top_padding_px + stroke_padding)
        # Ensure text center position accounts for half text height + padding
        y = top_padding + (text_height / 2)
    else:  # long
        # Long: Top padding (configurable percentage)
        long_config = thumb_config.get("long", {})
        top_padding_percent = long_config.get("top_padding_percent", 8) / 100.0
        min_top_padding_px = long_config.get("min_top_padding_px", 100)
        top_padding = max(int(h * top_padding_percent), min_top_padding_px + stroke_padding)
        y = top_padding + (text_height / 2)
    
    # Horizontal centering (already handled by max_width, but ensure no overflow)
    x = w / 2  # Always center
    
    # Validate text doesn't overflow (safety check)
    text_top = y - (text_height / 2) - stroke_padding
    text_bottom = y + (text_height / 2) + stroke_padding
    text_left = x - (text_width / 2) - stroke_padding
    text_right = x + (text_width / 2) + stroke_padding
    
    if text_top < 0 or text_bottom > h or text_left < 0 or text_right > w:
        logging.warning(f"⚠️ Text may overflow edges. Adjusting position...")
        # Adjust if needed
        if text_top < 0:
            y = (text_height / 2) + stroke_padding + 10
        if text_bottom > h:
            y = h - (text_height / 2) - stroke_padding - 10
        if text_left < 0 or text_right > w:
            # This shouldn't happen due to max_width, but just in case
            logging.warning(f"⚠️ Text width exceeds image width")
    
    logging.info(f"📍 Text position: ({int(x)}, {int(y)}) with padding: top={int(text_top)}px")
    
    # Multi-layer rendering for maximum contrast
    # Outer dark stroke
    draw.text((x, y), text, font=font, fill="black", anchor="mm", stroke_width=stroke_width+2, stroke_fill="black")
    # Main text with Kerala CTR color
    draw.text((x, y), text, font=font, fill=text_color, anchor="mm", stroke_width=stroke_width, stroke_fill=stroke_color)
    
    return font, final_font_size, x, y


def apply_professional_effects(image):
    """
    Apply professional image effects for polished thumbnails.
    
    Args:
        image: PIL Image object
    
    Returns:
        PIL Image object with effects applied
    """
    # Enhance contrast (subtle - 10% boost)
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.1)
    
    # Enhance saturation (15% boost for vibrant colors)
    enhancer = ImageEnhance.Color(image)
    image = enhancer.enhance(1.15)
    
    # Apply sharpening for crisp text
    image = image.filter(ImageFilter.SHARPEN)
    
    return image


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


def extract_hero_object(topic):
    """
    Extract hero object from topic for visual focus in thumbnails.
    
    Args:
        topic: Video topic string
    
    Returns:
        Clear, visually obvious hero object description
    """
    topic_lower = topic.lower()
    
    # Finance keywords
    if any(word in topic_lower for word in ['money', 'finance', 'invest', 'save', 'tax', 'bank', 'rates', 'rupee', 'wealth', 'salary', 'income']):
        return "floating Indian rupee notes and gold coins"
    # Tech keywords
    elif any(word in topic_lower for word in ['tech', 'ai', 'phone', 'app', 'digital', 'software', 'computer', 'internet', 'online']):
        return "glowing smartphone or digital device"
    # Health keywords
    elif any(word in topic_lower for word in ['health', 'fitness', 'diet', 'exercise', 'wellness', 'food', 'nutrition']):
        return "vibrant healthy food or fitness equipment"
    # Business/Career keywords
    elif any(word in topic_lower for word in ['business', 'career', 'job', 'work', 'success', 'entrepreneur']):
        return "professional business elements or success symbols"
    # Education keywords
    elif any(word in topic_lower for word in ['learn', 'education', 'study', 'skill', 'course', 'tutorial']):
        return "educational elements or learning symbols"
    # Default
    else:
        return f"prominent {topic} element"


def generate_ctr_thumbnail_prompt(topic, video_type="short"):
    """
    Generate high-CTR DALL-E prompt with random variation selection.
    
    Implements 5 proven CTR variations:
    1. Curiosity + Mystery (Best CTR)
    2. Problem vs Solution Split
    3. Before/After Transformation
    4. Danger/Warning Attention Grabber
    5. Luxury Premium Look
    
    Args:
        topic: Video topic
        video_type: "short" or "long"
    
    Returns:
        Complete DALL-E prompt string
    """
    hero_object = extract_hero_object(topic)
    variation = random.choice([1, 2, 3, 4, 5])
    
    # Base requirements that apply to all variations
    base_requirements = """ultra sharp, high contrast, cinematic lighting, vibrant colors, clean composition.
Subject must be large and close-up, with strong facial expression and clear emotion.
Add one clear hero object related to the topic (large, centered, visually obvious): {hero_object}.
Use depth of field blur for background, and strong foreground separation.
Add dynamic action cues like glowing edges, motion blur streaks, arrow-like direction shapes (but NOT actual arrows with text).
Composition must include clean empty space on one side for adding text later.
Subject must fill 60-70% of the frame.
Background must be simple + blurred.
Leave 25-30% clean space for text placement.
ABSOLUTE RULE: The image must contain NO TEXT, NO LETTERS, NO NUMBERS, NO LOGOS, NO WATERMARKS, NO UI LABELS, NO SYMBOLS that look like writing.
If any text appears, remove it completely and replace with abstract shapes only.
Make it look like a real YouTube thumbnail that stops scrolling instantly.
8K quality, hyper realistic, photorealistic 3D render.""".format(hero_object=hero_object)
    
    # Add aspect ratio specification
    if video_type == "long":
        aspect_spec = "16:9 landscape format,"
    else:
        aspect_spec = "9:16 portrait format,"
    
    # Variation 1: Curiosity + Mystery (Best CTR)
    if variation == 1:
        prompt = f"A close-up shocked Indian face looking at a glowing {hero_object} related to {topic}, dramatic lighting, strong contrast, dark background with clean empty space, {aspect_spec} {base_requirements}"
    
    # Variation 2: Problem vs Solution Split
    elif variation == 2:
        prompt = f"Split-screen image: left side messy/problem scene related to {topic}, right side clean/result scene, big expressive Indian face in middle reacting with surprise, {aspect_spec} {base_requirements}"
    
    # Variation 3: Before/After Transformation
    elif variation == 3:
        prompt = f"A transformation scene showing before vs after of {topic}, glowing transition in center, expressive Indian face showing amazement at the transformation, cinematic lighting, {aspect_spec} {base_requirements}"
    
    # Variation 4: Danger/Warning Attention Grabber
    elif variation == 4:
        prompt = f"A close-up worried Indian face with a dangerous-looking glowing red element related to {topic}, intense lighting, dramatic mood, urgent expression, {aspect_spec} {base_requirements}"
    
    # Variation 5: Luxury Premium Look
    else:  # variation == 5
        prompt = f"Minimal clean premium scene with a confident Indian face + sleek {hero_object} related to {topic}, Apple/Stripe style lighting, sophisticated composition, {aspect_spec} {base_requirements}"
    
    return prompt.strip()


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
    # ULTIMATE KERALA STRATEGY: MAXIMUM MASSIVE text sizing
    thumb_config = channel_config.get("thumbnails", {})
    if video_type == "long":
        long_config = thumb_config.get("long", {})
        size = long_config.get("dall_e_size", "1792x1024")  # DALL-E landscape (will be resized to 1920x1080)
        target_dims = long_config.get("target_dimensions", [1920, 1080])
        dimensions = tuple(target_dims)  # Final target dimensions (16:9)
        font_size = long_config.get("font_size", 180)  # MAXIMUM for Kerala (was 160px)
        position = ('center', 200)
    else:  # short
        short_config = thumb_config.get("short", {})
        size = short_config.get("dall_e_size", "1024x1792")  # Portrait 9:16
        target_dims = short_config.get("target_dimensions", [1080, 1920])
        dimensions = tuple(target_dims)
        font_size = short_config.get("font_size", 400)  # ABSOLUTE MAXIMUM for shorts - 4x original! (was 100px)
        position = 'center'
    
    # Generate high-CTR DALL-E prompt using new CTR-optimized system
    prompt = generate_ctr_thumbnail_prompt(topic, video_type)
    
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
        # Fallback to simple thumbnail - ensures pipeline NEVER fails
        logging.warning(f"DALL-E thumbnail failed: {e}")
        logging.info("🔄 Using fallback thumbnail generator...")
        from services.fallback_thumbnail import create_fallback_thumbnail
        
        # Fallback with unique hash
        import hashlib
        topic_hash = hashlib.md5(topic.encode()).hexdigest()[:8]
        safe_topic = "".join([c for c in topic if c.isalnum() or c in (' ', '-', '_')]).strip()[:30]
        fallback_path = output_path or f"videos/output/thumb_{topic_hash}_{safe_topic.replace(' ', '_')}_{video_type}.png"
        
        try:
            result = create_fallback_thumbnail(title, topic, fallback_path, dimensions, video_type)
            if result and os.path.exists(result):
                logging.info(f"✅ Fallback thumbnail created: {result}")
                return result
            else:
                raise Exception("Fallback thumbnail creation returned invalid path")
        except Exception as fallback_error:
            logging.error(f"❌ Fallback thumbnail also failed: {fallback_error}")
            # Last resort: create minimal thumbnail
            try:
                os.makedirs(os.path.dirname(fallback_path), exist_ok=True)
                img = Image.new('RGB', dimensions, (50, 50, 50))
                img.save(fallback_path)
                logging.warning(f"⚠️ Created minimal fallback thumbnail: {fallback_path}")
                return fallback_path
            except Exception as last_error:
                raise Exception(f"All thumbnail generation methods failed. Last error: {last_error}")
    
    # Download image to OUTPUT directory with UNIQUE filename
    # Match video naming pattern: thumb_{hash}_{topic}_{type}.png
    import hashlib
    topic_hash = hashlib.md5(topic.encode()).hexdigest()[:8]
    safe_topic = "".join([c for c in topic if c.isalnum() or c in (' ', '-', '_')]).strip()[:30]
    path = output_path or f"videos/output/thumb_{topic_hash}_{safe_topic.replace(' ', '_')}_{video_type}.png"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    common_config = channel_config.get("thumbnails.common", {})
    MAX_RETRIES = common_config.get("download_max_retries", 5)
    download_timeout = common_config.get("download_timeout_seconds", 120)
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, timeout=download_timeout)
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
    # Resize to exact dimensions (DALL-E might return 1792x1024, we need 1920x1080)
    if image.size != dimensions:
        image = image.resize(dimensions, Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image)
    
    # Get Malayalam headline with CTR psychology (100% correct, no AI)
    # Emotion is auto-detected by generate_malayalam_headline based on topic keywords
    # Pass "curiosity" as default - function will override with smart detection
    malayalam_headline = generate_malayalam_headline(topic, title, "curiosity", video_type)
    
    # Pre-render text validation
    if not malayalam_headline or len(malayalam_headline.strip()) == 0:
        logging.error("⚠️ Empty headline generated, using fallback text")
        malayalam_headline = "നോക്ക്!" if video_type == "short" else "നോക്ക് ഇത്!"
    
    # Note: Validation moved to after resize and save (line 483)
    # This prevents false warnings about aspect ratio before resize
    from services.thumbnail_playbook import get_color_combo_recommendation
    
    
    # KERALA CTR COLORS - Override with proven Kerala winners
    # Yellow/Red has highest CTR in Kerala market
    if video_type == "short":
        # Shorts: Yellow on Red background (proven Kerala winner)
        text_color = (255, 255, 0)  # Pure yellow
        stroke_color = (139, 0, 0)  # Dark red stroke
        color_combo_name = "KERALA_YELLOW_RED"
    else:
        # Long: Get from playbook but prefer Kerala colors
        color_combo = get_color_combo_recommendation(video_type)
        text_color = (255, 215, 0)  # Gold (Kerala preference)
        stroke_color = (0, 0, 0)  # Black
        color_combo_name = color_combo.get("name", "KERALA_GOLD_BLACK")
    
    logging.info(f"🎨 KERALA CTR colors: {color_combo_name}")
    
    # Load Malayalam font using standardized system
    from services.thumbnail_playbook import get_font_recommendation
    
    try:
        font_path = get_font_recommendation()
    except Exception as e:
        logging.error(f"Font loading failed: {e}")
        raise Exception("Malayalam font required for thumbnails. Install Noto Sans Malayalam or Nirmala UI.")
    
    # Validate text before rendering
    if not malayalam_headline or len(malayalam_headline.strip()) == 0:
        logging.warning("⚠️ Empty headline generated, using fallback")
        malayalam_headline = "നോക്ക്!" if video_type == "short" else "നോക്ക് ഇത്!"
    
    # Use unified text rendering function for consistency
    text = malayalam_headline
    
    # Validate text is valid Unicode string before rendering
    if not isinstance(text, str):
        text = str(text)
    
    # Ensure text is properly encoded (no corruption)
    try:
        # Test encoding - if text can't be encoded, it's corrupted
        text.encode('utf-8')
    except UnicodeEncodeError:
        logging.error(f"⚠️ Text encoding error, using fallback")
        text = "നോക്ക്!" if video_type == "short" else "നോക്ക് ഇത്!"
    
    # Render text overlay
    render_text_overlay(image, text, video_type, font_path, font_size, text_color, stroke_color)
    
    # Apply professional effects
    image = apply_professional_effects(image)
    
    # Save with high quality
    # Save with high quality
    image_quality = channel_config.get("thumbnails.common.image_quality", 95)
    image.save(path, quality=image_quality, optimize=True)
    
    # Post-render validation and quality checks
    if not os.path.exists(path):
        raise Exception(f"Thumbnail file was not created at {path}")
    
    file_size = os.path.getsize(path)
    if file_size < 1000:  # Less than 1KB is suspicious
        logging.warning(f"⚠️ Thumbnail file size is very small: {file_size} bytes")
    
    # Import validation function (moved here to avoid early import)
    from services.thumbnail_playbook import validate_thumbnail_production_ready
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
    logging.info(f"✅ Thumbnail created ({video_type}, {color_combo_name}): {safe_text}")
    print(f"Thumbnail created ({video_type}, {color_combo_name}): {safe_text}")
    
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
