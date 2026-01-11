"""
Fallback Thumbnail Generator

Creates professional fallback thumbnails when DALL-E fails.
Uses PIL to create high-quality text-based thumbnails.

Ensures pipeline NEVER fails due to thumbnail generation.
"""

import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import logging

def create_fallback_thumbnail(title, topic, output_path="videos/output/fallback_thumb.png"):
    """
    Create a professional fallback thumbnail using PIL.
    
    Args:
        title: Video title (Malayalam or English)
        topic: Topic for background color selection
        output_path: Where to save the thumbnail
    
    Returns:
        Path to created thumbnail
    """
    try:
        # Create 9:16 image (1080x1920 for shorts, will be resized for long)
        width, height = 1080, 1920
        
        # Color scheme based on topic keywords
        if any(word in topic.lower() for word in ['tech', 'ai', 'technology']):
            bg_color = (30, 30, 50)  # Dark blue
            accent = (100, 200, 255)  # Light blue
        elif any(word in topic.lower() for word in ['news', 'breaking', 'update']):
            bg_color = (50, 20, 20)  # Dark red
            accent = (255, 100, 100)  # Light red
        elif any(word in topic.lower() for word in ['money', 'finance', 'stock']):
            bg_color = (20, 40, 20)  # Dark green
            accent = (100, 255, 150)  # Light green
        else:
            bg_color = (40, 40, 40)  # Dark gray
            accent = (255, 200, 50)  # Gold
        
        # Create base image
        img = Image.new('RGB', (width, height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Add gradient overlay
        for y in range(height):
            alpha = int(255 * (y / height) * 0.3)
            line_color = tuple(min(255, c + alpha//2) for c in bg_color)
            draw.line([(0, y), (width, y)], fill=line_color)
        
        # Load Malayalam-supporting font
        font_paths = [
            "C:/Windows/Fonts/NirmalaUI-Bold.ttf",
            "C:/Windows/Fonts/NirmalaUI.ttf",
            "C:/Windows/Fonts/arialbd.ttf"
        ]
        
        font_large = None
        for fp in font_paths:
            try:
                font_large = ImageFont.truetype(fp, 120)
                break
            except:
                continue
        
        if not font_large:
            font_large = ImageFont.load_default()
        
        # Truncate title if too long
        display_title = title[:50] if len(title) > 50 else title
        
        # Calculate text position (centered)
        bbox = draw.textbbox((0, 0), display_title, font=font_large)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        # Draw text with shadow/glow
        # Shadow
        shadow_offset = 8
        draw.text((x + shadow_offset, y + shadow_offset), display_title, font=font_large, fill=(0, 0, 0, 180))
        
        # Main text
        draw.text((x, y), display_title, font=font_large, fill=accent)
        
        # Add "AUTO-GENERATED" watermark (small, bottom corner)
        try:
            font_small = ImageFont.truetype(font_paths[0], 30)
        except:
            font_small = font_large
        
        watermark = "AUTO"
        draw.text((width - 150, height - 80), watermark, font=font_small, fill=(150, 150, 150))
        
        # Save
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img.save(output_path, quality=95)
        
        logging.info(f"[Fallback Thumb] Created: {output_path}")
        return output_path
    
    except Exception as e:
        logging.error(f"[Fallback Thumb] Failed to create fallback: {e}")
        # Last resort: create solid color image
        try:
            img = Image.new('RGB', (1080, 1920), (50, 50, 50))
            img.save(output_path)
            return output_path
        except:
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
