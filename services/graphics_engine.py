"""
Graphics and Infographics Engine for Content Enrichment

Creates data visualizations, animated text overlays, and custom graphics
to add unique value beyond stock footage compilation.
"""

import os
from moviepy.editor import TextClip, ColorClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
import random

class GraphicsEngine:
    """Generate custom graphics and overlays for unique value"""
    
    @staticmethod
    def create_stat_overlay(text, value, duration, start_time, position=('center', 300)):
        """
        Create animated statistic overlay
        Example: "95% of people" with animated counting
        """
        try:
            # Main stat text
            stat_clip = TextClip(
                value,
                fontsize=120,
                color='yellow',
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=4
            )
            stat_clip = stat_clip.set_pos(position).set_duration(duration).set_start(start_time)
            
            # Label text
            label_clip = TextClip(
                text,
                fontsize=50,
                color='white',
                font='Arial',
                stroke_color='black',
                stroke_width=2
            )
            label_pos = (position[0], position[1] + 100 if isinstance(position[1], int) else 'center')
            label_clip = label_clip.set_pos(label_pos).set_duration(duration).set_start(start_time)
            
            # Pop-in animation
            stat_clip = stat_clip.resize(lambda t: min(1 + 0.5 * t * 5, 1.2))
            
            return [stat_clip, label_clip]
        except Exception as e:
            print(f"Stat overlay failed: {e}")
            return []
    
    @staticmethod
    def create_title_card(title, subtitle="", duration=2.0, bgcolor=(20, 20, 40)):
        """
        Create intro/section title card
        """
        try:
            # Background
            bg = ColorClip(size=(1080, 1920), color=bgcolor).set_duration(duration)
            
            # Title
            title_clip = TextClip(
                title,
                fontsize=90,
                color='white',
                font='Arial-Bold',
                method='caption',
                size=(900, None),
                align='center'
            )
            title_clip = title_clip.set_pos(('center', 700)).set_duration(duration)
            
            clips = [bg, title_clip]
            
            if subtitle:
                subtitle_clip = TextClip(
                    subtitle,
                    fontsize=50,
                    color='lightgray',
                    font='Arial',
                    method='caption',
                    size=(800, None),
                    align='center'
                )
                subtitle_clip = subtitle_clip.set_pos(('center', 950)).set_duration(duration)
                clips.append(subtitle_clip)
            
            return CompositeVideoClip(clips)
        except Exception as e:
            print(f"Title card failed: {e}")
            return None
    
    @staticmethod
    def create_point_highlight(point_number, point_text, duration, start_time):
        """
        Animated point highlight (e.g., "Point 1:", "Tip 2:")
        """
        try:
            # Point number badge
            badge = TextClip(
                f"#{point_number}",
                fontsize=80,
                color='black',
                font='Arial-Bold',
                bg_color='yellow',
                method='caption',
                size=(150, 150)
            )
            badge = badge.set_pos((100, 200)).set_duration(duration).set_start(start_time)
            
            # Point text
            text_clip = TextClip(
                point_text,
                fontsize=60,
                color='white',
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=2,
                method='caption',
                size=(750, None),
                align='left'
            )
            text_clip = text_clip.set_pos((280, 200)).set_duration(duration).set_start(start_time)
            
            # Slide-in animation
            badge = badge.set_position(lambda t: (100 - 100 * max(1 - t * 5, 0), 200))
            
            return [badge, text_clip]
        except Exception as e:
            print(f"Point highlight failed: {e}")
            return []
    
    @staticmethod
    def add_progress_bar(video_duration, position=('center', 1850)):
        """
        Add progress bar at bottom for engagement
        """
        try:
            # Progress bar background
            bg_bar = ColorClip(size=(1000, 15), color=(100, 100, 100)).set_opacity(0.5)
            bg_bar = bg_bar.set_pos(position).set_duration(video_duration)
            
            # Animated progress
            def make_progress_clip(t):
                progress = t / video_duration
                width = int(1000 * progress)
                return ColorClip(size=(width, 15), color=(255, 215, 0)).set_opacity(0.8)
            
            # This would need custom implementation
            # For now, return static bar
            return bg_bar
        except Exception as e:
            print(f"Progress bar failed: {e}")
            return None

def enrich_video_with_graphics(video_clip, script_data, enable_graphics=True):
    """
    Add custom graphics overlays based on script content
    
    Args:
        video_clip: Base video
        script_data: Dict with script, on_screen_text, etc.
        enable_graphics: Toggle graphics on/off
    """
    if not enable_graphics:
        return video_clip
    
    gfx = GraphicsEngine()
    overlay_clips = []
    
    # Add on-screen text if available
    if 'on_screen_text' in script_data and script_data['on_screen_text']:
        points = script_data['on_screen_text']
        segment_duration = video_clip.duration / len(points)
        
        for i, point in enumerate(points):
            start_time = i * segment_duration
            point_clips = gfx.create_point_highlight(i + 1, point, segment_duration, start_time)
            overlay_clips.extend(point_clips)
    
    # Compose final video with overlays
    if overlay_clips:
        try:
            final = CompositeVideoClip([video_clip] + overlay_clips)
            return final
        except Exception as e:
            print(f"Graphics composition failed: {e}")
            return video_clip
    
    return video_clip

if __name__ == "__main__":
    # Test block - pass is acceptable here
    pass
