"""
Visual Effects Engine for YPP-Compliant Video Transformations

This module applies heavy visual transformations to prevent "reused content" flags.
YouTube requires significant transformation beyond simple compilation of stock footage.

NOTE: For PRODUCTION-GRADE zoom effects with ZERO black borders guaranteed,
use zoom_effects_ffmpeg.py which implements crop → overscan → zoom → scale approach.
This module provides MoviePy-based effects for lighter processing.
"""

import os
import random
from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip
import numpy as np

class VisualEffects:
    """Applies professional transformations to video clips"""
    
    @staticmethod
    def apply_color_grading(clip, preset="cinematic"):
        """
        Apply color grading to transform the look
        Presets: cinematic, vibrant, moody, warm, cool
        """
        def color_transform(image):
            if preset == "cinematic":
                # Teal and Orange look
                image[:, :, 0] = np.clip(image[:, :, 0] * 1.1 - 10, 0, 255)  # Red
                image[:, :, 1] = np.clip(image[:, :, 1] * 0.95, 0, 255)      # Green
                image[:, :, 2] = np.clip(image[:, :, 2] * 1.15, 0, 255)      # Blue
            elif preset == "vibrant":
                # Increase saturation
                image = np.clip(image * 1.2, 0, 255)
            elif preset == "moody":
                # Darker, desaturated
                image = np.clip(image * 0.8, 0, 255)
            elif preset == "warm":
                # Orange/yellow tint
                image[:, :, 0] = np.clip(image[:, :, 0] * 1.15, 0, 255)
                image[:, :, 1] = np.clip(image[:, :, 1] * 1.05, 0, 255)
            elif preset == "cool":
                # Blue tint
                image[:, :, 2] = np.clip(image[:, :, 2] * 1.15, 0, 255)
            return image
        
        return clip.fl_image(color_transform)
    
    @staticmethod
    def apply_zoom_effect(clip, zoom_intensity="medium"):
        """
        Ken Burns zoom effect with GUARANTEED ZERO BLACK BORDERS.
        
        PRODUCTION APPROACH - OVERSCAN METHOD:
        ==========================================
        Problem: Zoom out shows black borders because content runs out
        Solution: Pre-scale content larger (overscan), zoom within that buffer
        
        Steps:
        1. Pre-scale content to 1.4x (40% overscan buffer)
        2. Apply zoom WITHIN that overscan (zoom range always < 1.4x)
        3. Crop and resize to target size
        
        Result: Content ALWAYS fills frame, mathematically impossible to show borders
        
        Args:
            clip: VideoClip or ImageClip
            zoom_intensity: "subtle", "medium", "intense"
        
        Returns:
            Clip with smooth Ken Burns effect, ZERO black borders guaranteed
        """
        
        # Zoom configurations - all stay within overscan buffer
        zoom_configs = {
            "subtle": {"min_scale": 1.00, "max_scale": 1.08},   # 0-8% zoom
            "medium": {"min_scale": 1.00, "max_scale": 1.20},   # 0-20% zoom
            "intense": {"min_scale": 1.00, "max_scale": 1.35}   # 0-35% zoom
        }
        
        config = zoom_configs.get(zoom_intensity, zoom_configs["medium"])
        
        # CRITICAL: OVERSCAN FACTOR - must be > max zoom scale
        OVERSCAN = 1.4  # 40% buffer - GUARANTEES no borders even at max zoom
        
        # Store original target size
        target_w, target_h = clip.size
        
        # Step 1: PRE-SCALE (overscan) - creates buffer zone
        overscan_w = int(target_w * OVERSCAN)
        overscan_h = int(target_h * OVERSCAN)
        clip_overscan = clip.resize((overscan_w, overscan_h))
        
        # Step 2: Random zoom direction
        import random
        direction = random.choice(["in", "out"])
        
        if direction == "in":
            # Zoom IN: grow from min to max
            start_scale = config["min_scale"]
            end_scale = config["max_scale"]
        else:
            # Zoom OUT: shrink from max to min
            start_scale = config["max_scale"]
            end_scale = config["min_scale"]
        
        def overscan_zoom(get_frame, t):
            """
            Apply zoom by cropping from overscan content.
            This is MATHEMATICALLY GUARANTEED to never show black borders.
            """
            frame = get_frame(t)
            
            # Calculate current zoom level (linear interpolation)
            progress = min(t / clip.duration, 1.0) if clip.duration > 0 else 0
            current_scale = start_scale + (end_scale - start_scale) * progress
            
            # Frame dimensions (overscan size - larger than target)
            frame_h, frame_w = frame.shape[:2]
            
            # Calculate crop dimensions
            # Higher scale = larger crop = more zoom
            crop_h = int(target_h * current_scale)
            crop_w = int(target_w * current_scale)
            
            # Ensure crop doesn't exceed overscan dimensions (safety check)
            crop_h = min(crop_h, frame_h)
            crop_w = min(crop_w, frame_w)
            
            # Center crop coordinates
            y_center = frame_h // 2
            x_center = frame_w // 2
            
            y1 = max(0, y_center - crop_h // 2)
            y2 = min(frame_h, y1 + crop_h)
            x1 = max(0, x_center - crop_w // 2)
            x2 = min(frame_w, x1 + crop_w)
            
            # Crop from overscan content
            cropped = frame[y1:y2, x1:x2]
            
            # Resize cropped region back to TARGET size
            # This step fills the frame completely
            from PIL import Image
            import numpy as np
            
            img = Image.fromarray(cropped)
            img = img.resize((target_w, target_h), Image.LANCZOS)
            
            return np.array(img)
        
        # Apply transformation
        return clip_overscan.fl(overscan_zoom)
    
    @staticmethod
    def apply_pan_effect(clip, direction="random"):
        """
        Pan across the video for dynamic movement
        Directions: left, right, up, down, random
        """
        w, h = clip.size
        
        if direction == "random":
            direction = random.choice(["left", "right", "up", "down"])
        
        def position_func(t):
            progress = t / clip.duration
            if direction == "left":
                x = int(-w * 0.1 * progress)
                return (x, 0)
            elif direction == "right":
                x = int(w * 0.1 * progress)
                return (x, 0)
            elif direction == "up":
                y = int(-h * 0.1 * progress)
                return (0, y)
            else:  # down
                y = int(h * 0.1 * progress)
                return (0, y)
        
        return clip.set_position(position_func)
    
    @staticmethod
    def apply_vignette(clip, strength=0.3):
        """
        Add vignette effect for cinematic look
        """
        w, h = clip.size
        
        # Create radial gradient mask
        def make_vignette_frame(t):
            frame = np.zeros((h, w, 3), dtype=np.uint8)
            center_x, center_y = w // 2, h // 2
            
            for y in range(h):
                for x in range(w):
                    # Calculate distance from center
                    dist = np.sqrt((x - center_x)**2 + (y - center_y)**2)
                    max_dist = np.sqrt(center_x**2 + center_y**2)
                    
                    # Create vignette (darker at edges)
                    vignette_val = 1 - (dist / max_dist) * strength
                    frame[y, x] = int(255 * vignette_val)
            
            return frame
        
        # This is computationally expensive, so we'll use a simpler overlay approach
        # For production, consider pre-rendering the vignette
        return clip  # Placeholder - implement if needed
    
    @staticmethod
    def add_overlay_gradient(clip, color=(0, 0, 0), opacity=0.2):
        """
        Add subtle gradient overlay for depth
        """
        gradient = ColorClip(size=clip.size, color=color).set_opacity(opacity).set_duration(clip.duration)
        return CompositeVideoClip([clip, gradient])
    
    @staticmethod
    def apply_smart_crop(clip, target_ratio=9/16):
        """
        Intelligent cropping that follows motion or focuses on center
        """
        w, h = clip.size
        current_ratio = w / h
        
        if abs(current_ratio - target_ratio) < 0.01:
            return clip  # Already correct ratio
        
        if current_ratio > target_ratio:
            # Too wide, crop horizontally
            new_w = int(h * target_ratio)
            x_center = w // 2
            return clip.crop(x1=x_center - new_w//2, x2=x_center + new_w//2)
        else:
            # Too tall, crop vertically
            new_h = int(w / target_ratio)
            y_center = h // 2
            return clip.crop(y1=y_center - new_h//2, y2=y_center + new_h//2)

def transform_clip(clip, transformation_profile="dynamic"):
    """
    Main function to apply a set of transformations
    
    Profiles:
    - dynamic: Zoom + color grading + subtle effects
    - cinematic: Professional film look
    - energetic: High saturation, quick movements
    - minimal: Subtle transformations only
    """
    vfx = VisualEffects()
    
    if transformation_profile == "dynamic":
        clip = vfx.apply_color_grading(clip, preset=random.choice(["cinematic", "vibrant"]))
        clip = vfx.apply_zoom_effect(clip, zoom_intensity="medium")
    
    elif transformation_profile == "cinematic":
        clip = vfx.apply_color_grading(clip, preset="cinematic")
        clip = vfx.apply_zoom_effect(clip, zoom_intensity="subtle")
    
    elif transformation_profile == "energetic":
        clip = vfx.apply_color_grading(clip, preset="vibrant")
        clip = vfx.apply_zoom_effect(clip, zoom_intensity="intense")
    
    elif transformation_profile == "minimal":
        clip = vfx.apply_color_grading(clip, preset=random.choice(["warm", "cool"]))
    
    return clip
