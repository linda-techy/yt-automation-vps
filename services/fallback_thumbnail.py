"""
Fallback Thumbnail Generator

Creates professional fallback thumbnails when DALL-E fails.
Uses PIL to create high-quality text-based thumbnails with Malayalam text.

Ensures pipeline NEVER fails due to thumbnail generation.
"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance
import logging

def create_fallback_thumbnail(title, topic, output_path="videos/output/fallback_thumb.png", dimensions=None, video_type="short"):
    """
    Create a professional fallback thumbnail using PIL with Malayalam text.
    
    Args:
        title: Video title (used for context)
        topic: Topic for background color selection and headline generation
        output_path: Where to save the thumbnail
        dimensions: Tuple (width, height) - if None, uses default based on video_type
        video_type: "short" (9:16) or "long" (16:9)
    
    Returns:
        Path to created thumbnail
    """
    try:
        # Determine dimensions
        if dimensions:
            width, height = dimensions
        elif video_type == "long":
            width, height = 1920, 1080
        else:  # short
            width, height = 1080, 1920
        
        # Import Malayalam headline generator
        from services.thumbnail_generator import generate_malayalam_headline
        
        # Generate Malayalam headline (100% correct, no AI)
        import random
        emotion = random.choice(["curiosity", "shock", "urgency", "money"])
        malayalam_text = generate_malayalam_headline(topic, title, emotion, video_type)
        
        # KERALA CTR COLORS - Same as main generator
        if video_type == "short":
            bg_color = (139, 0, 0)  # Dark red background (Kerala winner)
            text_color = (255, 255, 0)  # Pure yellow
            stroke_color = (139, 0, 0)  # Dark red stroke
        else:  # long
            bg_color = (0, 0, 0)  # Black background
            text_color = (255, 215, 0)  # Gold
            stroke_color = (0, 0, 0)  # Black
        
        # Create base image with gradient
        img = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Add subtle gradient overlay for depth
        for y in range(height):
            alpha = int(255 * (y / height) * 0.2)
            line_color = tuple(min(255, max(0, c + alpha//3)) for c in bg_color)
            draw.line([(0, y), (width, y)], fill=line_color)
        
        # Load font using same system as main generator
        from services.thumbnail_playbook import get_font_recommendation
        
        # Font size based on video type
        if video_type == "short":
            font_size = 400  # Same as main generator
        else:  # long
            font_size = 180  # Same as main generator
        
        font_path = None
        try:
            font_path = get_font_recommendation()
            font = ImageFont.truetype(font_path, font_size)
        except Exception as e:
            logging.error(f"Font loading failed in fallback: {e}")
            # Last resort fallback
            font_paths = [
                "C:/Windows/Fonts/NirmalaUI-Bold.ttf",
                "C:/Windows/Fonts/NirmalaUI.ttf",
                "fonts/NotoSansMalayalam-Regular.ttf"
            ]
            font = None
            for fp in font_paths:
                try:
                    if os.path.exists(fp):
                        font_path = fp  # Store for later use
                        font = ImageFont.truetype(fp, font_size)
                        break
                except:
                    continue
            if not font:
                font = ImageFont.load_default()
                font_path = None  # Default font has no path
        
        # Get text size for dynamic positioning
        text = malayalam_text
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # ULTRA-THICK STROKES for readability (needed for padding calculation)
        stroke_width = 12 if video_type == "short" else 8
        stroke_padding = stroke_width + 2  # Extra padding for outer stroke
        
        # Auto-size if too wide (same logic as main generator)
        # Account for horizontal padding (5% on each side = 10% total)
        # Plus stroke padding on each side
        horizontal_padding = max(int(width * 0.05), 40)  # 5% or minimum 40px per side
        max_width = width - (horizontal_padding * 2) - (stroke_padding * 2)  # Account for padding and stroke
        attempts = 0
        while text_width > max_width and attempts < 10 and font_path:
            font_size = int(font_size * 0.95)
            try:
                font = ImageFont.truetype(font_path, font_size)
            except:
                # If font reload fails, break to avoid infinite loop
                break
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            attempts += 1
        
        # PROPER PADDING: Same as main generator - ensure text doesn't touch edges
        # stroke_padding already calculated above
        
        if video_type == "short":
            # Shorts: Top padding (5% of height, minimum 80px to account for stroke)
            top_padding = max(int(height * 0.05), 80 + stroke_padding)
            y = top_padding + (text_height / 2)
        else:  # long
            # Long: Top padding (8% of height, minimum 100px)
            top_padding = max(int(height * 0.08), 100 + stroke_padding)
            y = top_padding + (text_height / 2)
        
        # Horizontal centering
        x = width / 2  # Always center
        
        # Validate text doesn't overflow (safety check)
        text_top = y - (text_height / 2) - stroke_padding
        text_bottom = y + (text_height / 2) + stroke_padding
        
        if text_top < 0:
            y = (text_height / 2) + stroke_padding + 10
        if text_bottom > height:
            y = height - (text_height / 2) - stroke_padding - 10
        
        # Multi-layer rendering for maximum contrast (same as main generator)
        # Outer dark stroke
        draw.text((x, y), text, font=font, fill="black", anchor="mm", stroke_width=stroke_width+2, stroke_fill="black")
        # Main text with Kerala CTR color
        draw.text((x, y), text, font=font, fill=text_color, anchor="mm", stroke_width=stroke_width, stroke_fill=stroke_color)
        
        # Apply professional effects (sharpening, contrast, saturation)
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.1)  # 10% more contrast
        
        # Enhance saturation
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(1.15)  # 15% more saturation
        
        # Apply sharpening
        img = img.filter(ImageFilter.SHARPEN)
        
        # Save
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path, quality=95, optimize=True)
        
        logging.info(f"[Fallback Thumb] Created: {output_path} with text: {text}")
        return output_path
    
    except Exception as e:
        logging.error(f"[Fallback Thumb] Failed to create fallback: {e}")
        # Last resort: create solid color image with correct dimensions
        try:
            # Determine dimensions for last resort
            if dimensions:
                width, height = dimensions
            elif video_type == "long":
                width, height = 1920, 1080
            else:  # short
                width, height = 1080, 1920
            
            img = Image.new('RGB', (width, height), (50, 50, 50))
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            img.save(output_path)
            logging.warning(f"[Fallback Thumb] Created minimal fallback: {output_path}")
            return output_path
        except Exception as last_error:
            logging.error(f"[Fallback Thumb] Last resort also failed: {last_error}")
            return None


if __name__ == "__main__":
    # Test
    print("Testing fallback thumbnail generator...")
    
    test_cases = [
        ("AI വിപ്ലവം 2026: നിങ്ങൾ അറിയേണ്ടത്", "AI Technology"),
        ("Stock Market Crash Coming?", "Finance News"),
        ("Breaking: New Discovery!", "Breaking News")
    ]
    
    for i, (title, topic) in enumerate(test_cases):
        path = create_fallback_thumbnail(title, topic, f"test_thumb_{i}.png")
        print(f"Created: {path}")
