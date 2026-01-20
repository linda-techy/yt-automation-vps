import os
import random
import logging
from moviepy.editor import VideoFileClip, ImageClip, concatenate_videoclips, CompositeVideoClip, AudioFileClip, CompositeAudioClip
from moviepy.audio.fx.all import audio_normalize
from config.channel import channel_config
# Subtitles removed - relying on YouTube auto-CC
# from services.subtitle_engine import add_dynamic_captions

def ken_burns_effect(clip, zoom_ratio=0.04):
    """
    Applies a slow zoom effect to an ImageClip.
    """
    w, h = clip.size
    
    # Randomly choose zoom in or out
    def effect(get_frame, t):
        img = get_frame(t)
        # Calculate scale factor based on time
        # Linear zoom: 1.0 to 1.0 + zoom_ratio
        current_scale = 1 + (zoom_ratio * (t / clip.duration))
        
        # New dimensions
        new_w = int(w * current_scale)
        new_h = int(h * current_scale)
        
        # Crop logic: Center crop the scaled image to original size? 
        # MoviePy resize is easier.
        # Actually, simpler way in MoviePy without accessing raw frames:
        # Resize clip over time.
        return img # Placeholder if we don't implement raw numpy resize here.
    
    # Proper MoviePy Ken Burns is complex with just 'fl'. 
    # Simpler: Resize the clip to 1.1x and slide it or just resize over time.
    # Let's use resize lambda.
    
    return clip.resize(lambda t : 1 + 0.04 * (t / clip.duration))

def build_final_video(audio_path, asset_paths, script_data, output_path="videos/output/final_short.mp4"):
    """
    Cinematic Faceless Video Builder with YPP-Compliant Transformations:
    Audio + Video/Slides + Captions + Custom Graphics
    
    Args:
        audio_path: Path to audio file
        asset_paths: List of video/image paths
        script_data: Dict with 'script', 'on_screen_text', etc. (or just string for backward compat)
        output_path: Where to save final video
    """
    # Handle backward compatibility
    if isinstance(script_data, str):
        script_text = script_data
        script_data = {"script": script_data}
    else:
        script_text = script_data.get("script", "")
    
    # 1. Audio
    audio_clip = AudioFileClip(audio_path)
    audio_clip = audio_clip.fx(audio_normalize)
    total_duration = audio_clip.duration
    
    # 2. Assets & Pacing (Semantic Visual Synchronization)
    if not asset_paths:
        raise Exception("No assets provided")
        
    # Get optimal scene durations from Whisper
    from services.subtitle_engine import analyze_audio_timing
    logging.info("Analyzing audio for Semantic Pacing (Whisper REQUIRED)...")
    scene_durations = analyze_audio_timing(audio_path, language="ml")
    
    # STRICT: No fallback - Whisper must return valid scene durations
    if not scene_durations:
        raise Exception("Whisper audio analysis returned empty scene durations")
    
    # RETENTION FIX: Split long scenes to prevent images staying too long
    # Problem: 10-15s static DALL-E image = boring, kills retention
    # Solution: Cap each visual at 4.5s max, require multiple visuals for long scenes
    from services.scene_optimizer import optimize_scene_durations
    scene_durations = optimize_scene_durations(scene_durations, max_image_duration=4.5)
    
    logging.info(f"Optimized pacing: {len(scene_durations)} scenes, "
                 f"avg {sum(scene_durations)/len(scene_durations):.1f}s per visual")
    
    # CRITICAL FIX: Ensure we have enough UNIQUE assets for all scenes
    # NO CYCLING - prevents "same image 4 times" issue
    if len(asset_paths) < len(scene_durations):
        raise Exception(
            f"❌ Insufficient unique assets: Need {len(scene_durations)} scenes, "
            f"only have {len(asset_paths)} assets. Generate more visuals. NO ASSET RECYCLING."
        )
    
    clips = []
    
    for i, duration in enumerate(scene_durations):
        # DIRECT MAPPING: One asset per scene, no cycling with %
        path = asset_paths[i]  # ✅ FIXED: Direct index, not i % len
        
        # STRICT: No fallback - asset MUST exist
        if not path or not os.path.exists(path):
            raise Exception(f"Asset not found at path: {path} (scene {i})")
        elif path.endswith(('.mp4', '.mov', '.avi')):
            # Handle Video with HEAVY TRANSFORMATIONS
            # Load video, loop if too short, trim if too long
            src_clip = VideoFileClip(path).without_audio()
            
            # Loop logic
            if src_clip.duration < duration:
                src_clip = src_clip.loop(duration=duration)
            else:
                src_clip = src_clip.set_duration(duration)
                
            clip = src_clip
            
            # Resize and Crop to 9:16
            w, h = clip.size
            target_ratio = 1080/1920
            if w/h > target_ratio:
                # Too wide
                new_w = int(h * target_ratio)
                clip = clip.crop(x_center=w/2, width=new_w)
            else:
                # Too tall
                new_h = int(w / target_ratio)
                clip = clip.crop(y_center=h/2, height=new_h)
            clip = clip.resize(newsize=(1080, 1920))
            
            # APPLY VISUAL TRANSFORMATIONS (Varying profiles for diversity)
            from services.visual_effects import transform_clip
            transformation_profiles = ["dynamic", "cinematic", "energetic"]
            # Use scene index to ensure variety, not cycling
            profile = transformation_profiles[min(i, len(transformation_profiles)-1)]
            clip = transform_clip(clip, transformation_profile=profile)
            
        else:
            # Handle Image
            clip = ImageClip(path).set_duration(duration).resize(height=1920)
            clip = clip.crop(x1=clip.w/2 - 540, y1=0, width=1080, height=1920)
            
            # Apply Ken Burns with variety
            from services.visual_effects import VisualEffects
            vfx = VisualEffects()
            clip = vfx.apply_zoom_effect(clip, zoom_intensity="medium")
            
            # Vary color grading per scene for diversity
            color_presets = ["cinematic", "warm", "vibrant", "cool"]
            preset = color_presets[min(i % len(color_presets), len(color_presets)-1)]
            clip = vfx.apply_color_grading(clip, preset=preset)
        
        clips.append(clip)
        
    # Concatenate Clips
    video = concatenate_videoclips(clips, method="compose")
    
    # Ensure final video exactly matches audio duration (handling float rounding errors)
    if video.duration > total_duration:
        video = video.subclip(0, total_duration)
    
    video = video.set_audio(audio_clip)
    
    # Add Transition SFX (Whoosh)
    sfx_path = "assets/sfx/whoosh.mp3"
    if os.path.exists(sfx_path):
        try:
            sfx_clip = AudioFileClip(sfx_path).volumex(0.3)
            sfx_audios = [video.audio]
            current_time = 0
            # Use actual scene durations instead of undefined variable
            for dur in scene_durations[:-1]:
                current_time += dur
                sfx_audios.append(sfx_clip.set_start(max(0, current_time - 0.15)))
            video = video.set_audio(CompositeAudioClip(sfx_audios))
        except Exception as e:
            logging.warning(f"SFX failed: {e}")
    
    video = video.set_duration(total_duration)
    
    # 3. Captions REMOVED - YouTube auto-CC will handle Malayalam subtitles
    # This allows viewers to toggle subtitles on/off for better UX
    final_video = video
    
    # 3.5 Add Custom Graphics for Unique Value (YPP Requirement)
    try:
        from services.graphics_engine import enrich_video_with_graphics
        final_video = enrich_video_with_graphics(final_video, script_data, enable_graphics=True)
    except Exception as e:
        logging.warning(f"Graphics enrichment skipped: {e}")
    
    # 4. Add Watermark
    try:
        from moviepy.editor import TextClip
        from config.channel import channel_config
        wm_text = channel_config.watermark_text
        txt_clip = TextClip(wm_text, fontsize=40, color='white', font='Arial-Bold').set_opacity(0.3)
        txt_clip = txt_clip.set_position(('right', 'bottom')).set_duration(final_video.duration).margin(right=20, bottom=20, opacity=0)
        final_video = CompositeVideoClip([final_video, txt_clip])
    except Exception as e:
        logging.debug(f"[Video Builder] Failed to add watermark: {e}")
    
    # Write
    video_building_config = channel_config.get("video_building.short", {})
    fps = video_building_config.get("fps", 24)
    codec = video_building_config.get("codec", "libx264")
    audio_codec = video_building_config.get("audio_codec", "aac")
    threads = video_building_config.get("threads", 4)
    final_video.write_videofile(output_path, fps=fps, codec=codec, audio_codec=audio_codec, threads=threads)
    
    # Cleanup
    final_video.close()
    video.close()
    audio_clip.close()
    for c in clips: c.close()
    
    return output_path

if __name__ == "__main__":
    # Test block - pass is acceptable here
    pass
