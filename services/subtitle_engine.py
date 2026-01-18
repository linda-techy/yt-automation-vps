"""
Advanced Subtitle Engine with Whisper AI Integration

This module provides YPP-compliant captions with:
- Accurate Malayalam transcription
- Perfect sync with audio
- Animated caption styles
- Unicode rendering support
"""

import os
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    
from moviepy.editor import TextClip, CompositeVideoClip


def get_malayalam_font():
    """
    Returns a verified font path that supports Malayalam script.
    Prioritizes bundled fonts, then system fonts, then auto-downloads.
    """
    import platform
    os_type = platform.system().lower()
    
    # Get project root for bundled fonts
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fonts_dir = os.path.join(project_root, "fonts")
    bundled_font = os.path.join(fonts_dir, "NotoSansMalayalam-Regular.ttf")
    
    # Priority 1: Bundled font (guaranteed to work)
    if os.path.exists(bundled_font):
        print(f"[Font] Using bundled: NotoSansMalayalam-Regular.ttf")
        return bundled_font
    
    # Priority 2: System fonts
    if os_type == "windows":
        font_paths = [
            r"C:\Windows\Fonts\NirmalaUI.ttf",
            r"C:\Windows\Fonts\Nirmala.ttf",
        ]
    else:  # Linux/Ubuntu VPS
        font_paths = [
            "/usr/share/fonts/truetype/noto/NotoSansMalayalam-Regular.ttf",
            "/usr/share/fonts/truetype/lohit-malayalam/Lohit-Malayalam.ttf",
            "/usr/share/fonts/noto/NotoSansMalayalam-Regular.ttf",
        ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            print(f"[Font] Using system: {os.path.basename(font_path)}")
            return font_path
    
    # Priority 3: AUTO-DOWNLOAD if no font found (VPS fallback)
    print("[Font] No Malayalam font found. Auto-downloading...")
    try:
        import requests
        os.makedirs(fonts_dir, exist_ok=True)
        
        font_url = "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansMalayalam/NotoSansMalayalam-Regular.ttf"
        response = requests.get(font_url, timeout=30)
        response.raise_for_status()
        
        with open(bundled_font, 'wb') as f:
            f.write(response.content)
        
        print(f"[Font] ✅ Downloaded: NotoSansMalayalam-Regular.ttf ({len(response.content)//1024}KB)")
        return bundled_font
        
    except Exception as e:
        print(f"[Font] ⚠️ Auto-download failed: {e}")
        print("[Font] ⚠️ Subtitles may not render correctly!")
        return "DejaVu-Sans" if os_type != "windows" else "Arial"


def transcribe_with_whisper(audio_path, language="ml"):
    """
    Use Whisper AI for accurate Malayalam transcription with timestamps
    """
    if not WHISPER_AVAILABLE:
        return None
    
    try:
        model = whisper.load_model("base")  # or "small" for better accuracy
        result = model.transcribe(audio_path, language=language, word_timestamps=True)
        return result
    except Exception as e:
        print(f"Whisper transcription failed: {e}")
        return None

def add_dynamic_captions(video_clip, script_text, use_whisper=True, audio_path=None):
    """
    Overlays text on the video with YPP-compliant quality.
    
    STRICT MODE: Whisper AI is REQUIRED - no fallback allowed.
    """
    duration = video_clip.duration
    
    # Whisper is REQUIRED - no fallback
    if not WHISPER_AVAILABLE:
        raise Exception("Whisper AI is not installed. Run: pip install openai-whisper")
    
    if not audio_path:
        raise Exception("audio_path is required for Whisper transcription")
    
    whisper_result = transcribe_with_whisper(audio_path, language="ml")
    if whisper_result and 'segments' in whisper_result:
        return create_whisper_captions(video_clip, whisper_result)
    else:
        raise Exception("Whisper transcription failed - no valid segments returned")

def create_whisper_captions(video_clip, whisper_result):
    """
    Create dynamic word-level captions (Karaoke/Hormozi style)
    """
    text_clips = []
    font_path = get_malayalam_font()
    
    # Check if we have word timestamps
    has_words = any('words' in seg for seg in whisper_result['segments'])
    
    if has_words:
        print("[Subtitle] Generating WORD-LEVEL animations (High Energy)...")
        for segment in whisper_result['segments']:
            for word_data in segment.get('words', []):
                word = word_data['word'].strip()
                start = word_data['start']
                end = word_data['end']
                
                if not word: continue
                
                # Enforce minimum duration for visibility
                if end - start < 0.2:
                    end = start + 0.2
                
                try:
                    # Alternating colors for emphasis (Yellow / White)
                    # or highlight specific keywords? For now, random pop or static yellow.
                    color = 'yellow' 
                    stroke_width = 3
                    
                    # Create Clip
                    txt = TextClip(
                        word, 
                        fontsize=90,  # Larger for single words
                        color=color,
                        font=font_path, 
                        stroke_color='black', 
                        stroke_width=stroke_width,
                        method='caption', 
                        align='center',
                        size=(900, None)
                    )
                    
                    txt = txt.set_pos('center').set_start(start).set_duration(end - start)
                    
                    # POP Animation - FIX: Lambda closure bug
                    # Without default arg, all lambdas would reference same 't' variable
                    def make_resize_func():
                        return lambda t: 1 + 0.2 * min(t*10, 1)
                    
                    txt = txt.resize(make_resize_func())
                    
                    text_clips.append(txt)
                except Exception as e:
                    print(f"Word caption failed: {e}")
                    continue
    else:
        # Fallback to Segment/Phrase level
        print("[Subtitle] Word timestamps missing. Falling back to PHRASE-LEVEL.")
        for segment in whisper_result['segments']:
            text = segment['text'].strip()
            start_time = segment['start']
            end_time = segment['end']
            if not text: continue
            
            try:
                txt = TextClip(
                    text, 
                    fontsize=70, 
                    color='yellow',
                    font=font_path, 
                    stroke_color='black', 
                    stroke_width=3,
                    method='caption', 
                    size=(900, None),
                    align='center'
                )
                txt = txt.set_pos(('center', 800)).set_duration(end_time - start_time).set_start(start_time)
                txt = txt.resize(lambda t: 1 + 0.05 * min(t * 10, 1))
                text_clips.append(txt)
            except Exception as e:
                logging.warning(f"[Subtitle Engine] Failed to create caption clip: {e}", exc_info=True)

    if text_clips:
        # Ensure we don't have overlapping clips fighting for Z-index? 
        # CompositeVideoClip handles layers.
        final = CompositeVideoClip([video_clip] + text_clips)
        return final
    else:
        return video_clip

def create_basic_captions(video_clip, script_text, duration):
    """
    Fallback: Estimate word timing based on duration
    Improved chunking algorithm
    """
    words = script_text.split()
    
    # Dynamic chunk size based on video length
    chunk_size = max(2, min(5, int(len(words) / (duration / 3))))  # ~3s per chunk
    chunks = [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]
    
    chunk_duration = duration / len(chunks)
    text_clips = []
    
    for i, chunk in enumerate(chunks):
        try:
            # High-contrast, readable captions for Malayalam
            txt = TextClip(
                chunk, 
                fontsize=70, 
                color='white', 
                font='Nirmala-UI', 
                stroke_color='black', 
                stroke_width=2, 
                method='caption', 
                size=(900, None),
                align='center'
            )
            txt = txt.set_pos(('center', 800)).set_duration(chunk_duration).set_start(i * chunk_duration)
            text_clips.append(txt)
        except Exception as e:
            print(f"Caption failed: {e}")
            continue
        
    if text_clips:
        final = CompositeVideoClip([video_clip] + text_clips)
        return final
    else:
        return video_clip

def analyze_audio_timing(audio_path, language="ml", target_pace_min=3.0, target_pace_max=6.0):
    """
    Analyzes audio using Whisper to find optimal cut points based on sentence boundaries.
    Returns a list of duration floats for each scene.
    
    STRICT MODE: Whisper REQUIRED - no fallback.
    """
    if not WHISPER_AVAILABLE:
        raise Exception("Whisper AI is not installed. Run: pip install openai-whisper")

    try:
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, language=language, word_timestamps=True)
        
        segments = result.get('segments', [])
        cut_points = []
        current_segment_start = 0.0
        
        for seg in segments:
            # Each segment usually corresponds to a sentence or phrase
            end_time = seg['end']
            duration = end_time - current_segment_start
            
            # If the current accumulated segment is long enough, cut here
            if duration >= target_pace_min:
                cut_points.append(duration)
                current_segment_start = end_time
            # If it's too long (e.g. a run-on sentence), we might force a cut? 
            # For now, let's respect sentence boundaries unless it exceeds MAX significantly.
            # If a single sentence is 15s, we might need to split it? 
            # Whisper segments are usually reasonable length.
            
        # Handle remaining time
        total_duration = result['segments'][-1]['end']
        remaining = total_duration - current_segment_start
        if remaining > 0.5: # specific threshold to avoid tiny clips
            cut_points.append(remaining)
        elif cut_points:
            # Add remaining tiny bit to last clip
            cut_points[-1] += remaining
            
        return cut_points
    except Exception as e:
        print(f"Audio analysis failed: {e}")
        return []

if __name__ == "__main__":
    # Test block - pass is acceptable here
    pass
