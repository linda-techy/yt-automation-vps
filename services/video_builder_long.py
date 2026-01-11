import os
import gc
import logging
from moviepy.editor import VideoFileClip, ImageClip, concatenate_videoclips, AudioFileClip, CompositeVideoClip
from services.visual_effects import transform_clip, VisualEffects

def build_long_video_chunked(audio_path, asset_paths, script_data, output_path="videos/output/final_long.mp4"):
    """
    Builds a 10-minute video by rendering 60s chunks to avoid Memory Errors.
    STRICT MODE: Whisper REQUIRED for audio pacing - no fallback.
    """
    # 1. Audio Setup
    full_audio = AudioFileClip(audio_path)
    total_duration = full_audio.duration
    
    # Analyze Pacing with Whisper - STRICT, no fallback
    logging.info("Analyzing Audio Pacing with Whisper (STRICT MODE)...")
    from services.subtitle_engine import analyze_audio_timing
    scene_durations = analyze_audio_timing(audio_path, language="ml")
    
    # STRICT: Whisper MUST return valid scene durations
    if not scene_durations:
        raise Exception("Whisper audio analysis returned empty scene durations. NO FALLBACK ALLOWED.")

    # 2. Chunking Logic
    CHUNK_SIZE = 60 # seconds
    temp_chunks = []
    
    current_time = 0
    generated_duration = 0
    asset_index = 0
    
    # We need to map scenes to chunks. 
    # Simpler approach: Build clips for the whole timeline, BUT render subclips?
    # No, building the CompositeVideoClip for 10 mins is the memory hog.
    
    # We will iterate through time until total_duration.
    chunk_idx = 0
    
    while current_time < total_duration:
        chunk_end = min(current_time + CHUNK_SIZE, total_duration)
        chunk_duration = chunk_end - current_time
        
        logging.info(f"Rendering Chunk {chunk_idx}: {current_time:.1f}s to {chunk_end:.1f}s")
        
        # Build clips for this specific time range
        # We need to find which scenes fall into this chunk.
        # This is complex because a scene might straddle a chunk boundary.
        # EASIER STRATEGY: 
        # Just generate a subset of clips that sum up to ~60s.
        
        chunk_clips = []
        chk_runtime = 0
        
        # CRITICAL FIX: Validate sufficient unique assets BEFORE starting
        if asset_index >= len(asset_paths):
            raise Exception(
                f"❌ Ran out of unique assets at chunk {chunk_idx}. "
                f"Need more assets than {len(asset_paths)}. NO CYCLING."
            )
        
        while chk_runtime < chunk_duration and asset_index < len(asset_paths):
            scene_len = scene_durations[asset_index]
            
            # DIRECT MAPPING: One asset per scene, no cycling with %
            path = asset_paths[asset_index]  # ✅ FIXED: Direct index, not % cycling
            
            # Validate asset exists
            if not path or not os.path.exists(path):
                raise Exception(f"Asset not found: {path} (scene {asset_index})")
            
            # Create Clip - LANDSCAPE 16:9 for Traditional YouTube
            if path.endswith(('.mp4', '.mov')):
                clip = VideoFileClip(path).without_audio()
                # SAFE RESIZE: Ensure minimum dimensions before crop
                if clip.w < 1920 or clip.h < 1080:
                    # Scale up to cover 1920x1080 (maintain aspect ratio)
                    scale_w = 1920 / clip.w
                    scale_h = 1080 / clip.h
                    scale = max(scale_w, scale_h)
                    clip = clip.resize(scale)
                # Loop or trim to match scene duration
                if clip.duration < scene_len: 
                    clip = clip.loop(duration=scene_len)
                else: 
                    clip = clip.set_duration(scene_len)
                # CENTER CROP to exact 1920x1080
                x_center = clip.w / 2
                y_center = clip.h / 2
                clip = clip.crop(x1=x_center-960, y1=y_center-540, x2=x_center+960, y2=y_center+540)
            else:
                # Image (DALL-E generates 1024x1024, need to scale up)
                clip = ImageClip(path).set_duration(scene_len)
                # SAFE RESIZE: Scale up to cover 1920x1080
                if clip.w < 1920 or clip.h < 1080:
                    scale_w = 1920 / clip.w
                    scale_h = 1080 / clip.h
                    scale = max(scale_w, scale_h)
                    clip = clip.resize(scale)
                # CENTER CROP to exact 1920x1080
                x_center = clip.w / 2
                y_center = clip.h / 2
                clip = clip.crop(x1=x_center-960, y1=y_center-540, x2=x_center+960, y2=y_center+540)
                # Apply Zoom for visual interest
                vfx = VisualEffects()
                clip = vfx.apply_zoom_effect(clip, zoom_intensity="subtle")

            chunk_clips.append(clip)
            chk_runtime += scene_len
            asset_index += 1
            
            # If we overshoot significantly, we might need to trim the last clip?
            # For simplicity, let's just let chunks vary in size slightly (it's internal).
            # We just need to stop when we are 'near' the end of audio.
            if current_time + chk_runtime >= total_duration:
                break
        
        if not chunk_clips:
            break
            
        # Concat this chunk
        chunk_video = concatenate_videoclips(chunk_clips, method="compose")
        
        # Add Audio Segment for this chunk? 
        # No, simpler to add audio at the very end to the concatenated video.
        # But we need captions. Captions are best added per chunk if using word-level.
        # Actually, adding captions to 1-min chunks is safer.
        
        # FIXED: Create fresh audio clip for each chunk to avoid process issues
        actual_chunk_dur = chunk_video.duration
        
        # Load fresh audio clip and extract the specific segment
        chunk_audio = AudioFileClip(audio_path)
        audio_subclip = chunk_audio.subclip(current_time, min(current_time + actual_chunk_dur, total_duration))
        chunk_video = chunk_video.set_audio(audio_subclip)
        
        # Write Temp File
        temp_path = f"videos/temp/long_chunk_{chunk_idx}.mp4"
        chunk_video.write_videofile(temp_path, fps=24, codec='libx264', audio_codec='aac', threads=2, logger=None)
        temp_chunks.append(temp_path)
        
        # Clean up chunk resources
        chunk_audio.close()
        
        # CRITICAL: Clean up memory after each chunk
        for c in chunk_clips:
            try:
                c.close()
            except:
                pass
        chunk_video.close()
        audio_subclip.close()
        del chunk_clips, chunk_video, audio_subclip
        gc.collect()
        
        current_time += actual_chunk_dur
        chunk_idx += 1
    
    # 3. Polymerize
    logging.info("Stitching Long-Form Chunks...")
    clips = [VideoFileClip(p) for p in temp_chunks]
    final = concatenate_videoclips(clips)
    
    # Re-apply full master audio to ensure perfect sync (overwriting chunk audio)
    final = final.set_audio(full_audio)
    
    # Captions REMOVED - YouTube auto-CC will handle Malayalam subtitles
    # This provides better UX as viewers can toggle subtitles on/off
    logging.info("Subtitles will be provided by YouTube auto-CC")
    
    final.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac', threads=4)
    
    # Cleanup
    for c in clips: c.close()
    full_audio.close()
    for p in temp_chunks: os.remove(p)
    
    return output_path
