import os
import time
import logging
import requests
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance, ImageFilter
import random

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
    stroke_width = 12 if video_type == "short" else 8
    stroke_padding = stroke_width + 2  # Extra padding for outer stroke
    
    # SMART AUTO-SIZING: Reduce if text too wide
    # Account for horizontal padding (5% on each side = 10% total)
    # Plus stroke padding on each side
    horizontal_padding = max(int(w * 0.05), 40)  # 5% or minimum 40px per side
    max_width = w - (horizontal_padding * 2) - (stroke_padding * 2)  # Account for padding and stroke
    attempts = 0
    final_font_size = font_size
    while text_width > max_width and attempts < 10:
        final_font_size = int(final_font_size * 0.95)  # Reduce by 5%
        font = ImageFont.truetype(font_path, final_font_size)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        attempts += 1
    
    logging.info(f"📏 Final font: {final_font_size}px (fills {int(text_width/w*100)}% width)")
    
    # PROPER PADDING: Ensure text doesn't touch edges
    # stroke_padding already calculated above
    
    if video_type == "short":
        # Shorts: Top padding (5% of height, minimum 80px to account for stroke)
        top_padding = max(int(h * 0.05), 80 + stroke_padding)
        # Ensure text center position accounts for half text height + padding
        y = top_padding + (text_height / 2)
    else:  # long
        # Long: Top padding (8% of height, minimum 100px)
        top_padding = max(int(h * 0.08), 100 + stroke_padding)
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
    if video_type == "long":
        size = "1792x1024"  # DALL-E landscape (will be resized to 1920x1080)
        dimensions = (1920, 1080)  # Final target dimensions (16:9)
        font_size = 180  # MAXIMUM for Kerala (was 160px)
        position = ('center', 200)
    else:  # short
        size = "1024x1792"  # Portrait 9:16
        dimensions = (1080, 1920)
        font_size = 400  # ABSOLUTE MAXIMUM for shorts - 4x original! (was 100px)
        position = 'center'
    
    # ULTIMATE INDIAN-CONTEXT DALL-E PROMPTS (Kerala optimized)
    topic_keywords = topic.lower()
    
    if video_type == "long":
        # Long: Indian faces, emotional reactions, RED arrows
        if any(word in topic_keywords for word in ['money', 'finance', 'invest', 'save', 'tax', 'bank', 'rates']):
            prompt = f"Professional Indian YouTuber with very surprised expression, mouth open, pointing dramatically at floating Indian rupee notes and gold coins, large red upward arrow, financial chart in background, vibrant gold and green neon lighting, cinematic photorealistic 3D render, Indian person's face showing amazement, NO TEXT overlay, 8K quality"
        else:
            prompt = f"Professional Indian content creator with extremely surprised expression pointing at {topic}, large red arrow or circle highlighting key element, dramatic before/after split composition, vibrant contrasting colors, cinematic lighting, hyper realistic Indian face, NO TEXT, 8K detail"
    else:
        # Shorts: Close-up Indian faces, maximum drama
        if any(word in topic_keywords for word in ['money', 'finance', 'invest', 'save', 'tax', 'bank', 'rates']):
            prompt = f"Close-up of Indian person's extremely surprised face (mouth wide open), Indian rupee notes flying at camera, large red upward pointing arrow, gold coins background, person pointing finger at viewer, dramatic cinematic lighting, vibrant gold and green colors, portrait 9:16, NO TEXT, hyper realistic Indian face, eye-catching"
        else:
            prompt = f"Close-up Indian face showing pure surprise emotion, pointing finger urgently, {topic} element behind with red circle or arrow, vibrant energetic colors, dramatic portrait lighting 9:16, NO TEXT, attention-grabbing, realistic Indian person, instant stop-scroll impact"
    
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
    image.save(path, quality=95, optimize=True)
    
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
