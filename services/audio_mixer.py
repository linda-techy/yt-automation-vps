import os
import random
import shutil
from moviepy.editor import AudioFileClip, CompositeAudioClip

from config.channel import channel_config

MUSIC_DIR = channel_config.get("audio.background_music.music_dir", "assets/music")

def get_random_music():
    if not os.path.exists(MUSIC_DIR):
        return None
    files = [f for f in os.listdir(MUSIC_DIR) if f.endswith(".mp3") or f.endswith(".wav")]
    if not files:
        return None
    return os.path.join(MUSIC_DIR, random.choice(files))

def mix_audio(voice_path, music_path=None, output_path="videos/temp/mixed_audio.mp3"):
    """
    Overlays background music on voiceover.
    STRICT MODE: Always creates output file at specified path.
    """
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    voice = AudioFileClip(voice_path)
    
    if not music_path:
        music_path = get_random_music()
        
    if not music_path:
        # No music available - copy voice to output path
        # This ensures the expected output file always exists
        print("[Audio Mixer] No background music found - using voice only")
        voice.write_audiofile(output_path, logger=None)
        voice.close()
        return output_path

    music = AudioFileClip(music_path)
    
    try:
        # Loop music if shorter than voice
        if music.duration < voice.duration:
            # Use audio_loop for compatibility with MoviePy versions
            from moviepy.audio.fx.all import audio_loop
            music = audio_loop(music, duration=voice.duration + 2)
            
        # Cut music to voice length
        music = music.subclip(0, voice.duration)
        
        # Lower volume (Background)
        vol = channel_config.get("audio.background_music.volume", 0.12)
        music = music.volumex(vol)
        
        # Boost voice volume for clarity
        voice_boosted = voice.volumex(1.5)
        
        # Composite
        final_audio = CompositeAudioClip([voice_boosted, music])
        final_audio.fps = 44100
        final_audio.write_audiofile(output_path, logger=None)
        print(f"[Audio Mixer] Mixed audio created: {output_path}")
        
        return output_path
    finally:
        voice.close()
        music.close()

if __name__ == "__main__":
    # Test block - pass is acceptable here
    pass
