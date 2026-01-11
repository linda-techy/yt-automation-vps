"""
Malayalam Audio Transcription with Whisper
High-accuracy Malayalam STT with cleanup and segmentation
"""

import whisper
import os
import logging
import re
from typing import Dict, List


# Malayalam filler words to remove
MALAYALAM_FILLERS = [
    "അല്ലേ",  # isn't it
    "അതെ",  # yes (when used as filler)
    "എന്നാൽ",  # then (when excessive)
    "ഉം",  # um
    "ആ",  # uh
    "എന്ന്",  # that (when repetitive)
]


def transcribe_malayalam_audio(audio_path, context_hint=None, remove_fillers=True):
    """
    High-accuracy Malayalam transcription using Whisper AI.
    
    Args:
        audio_path: Path to audio file (mp3, wav, m4a, etc.)
        context_hint: Optional topic context for better accuracy (e.g., "technology news")
        remove_fillers: Remove common Malayalam filler words
    
    Returns:
        {
            "text": "full cleaned transcript",
            "text_raw": "original transcript",
            "segments": [
                {
                    "text": "segment text",
                    "start": 15.2,
                    "end": 42.8,
                    "words": [...]  # word-level if available
                }
            ],
            "language": "ml",
            "duration": 328.5
        }
    """
    
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    logging.info(f"🎤 Transcribing Malayalam audio: {audio_path}")
    
    # Load Whisper model
    # Use 'base' for speed, 'small' for accuracy, 'medium'/'large' for best quality
    try:
        model = whisper.load_model("small")  # Good balance for Malayalam
    except Exception as e:
        logging.warning(f"Failed to load 'small' model, trying 'base': {e}")
        model = whisper.load_model("base")
    
    # Transcribe with Malayalam-specific settings
    initial_prompt = None
    if context_hint:
        # Provide context to improve accuracy
        initial_prompt = f"Malayalam {context_hint} content with technical terms and spoken language."
    
    result = model.transcribe(
        audio_path,
        language="ml",  # Malayalam language code
        task="transcribe",
        initial_prompt=initial_prompt,
        word_timestamps=True,  # Get word-level timestamps
        verbose=False
    )
    
    # Extract segments
    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "text": seg["text"].strip(),
            "start": seg["start"],
            "end": seg["end"],
            "words": seg.get("words", [])
        })
    
    # Full transcript
    raw_text = " ".join([s["text"] for s in segments])
    
    # Clean transcript
    cleaned_text = raw_text
    if remove_fillers:
        cleaned_text = remove_filler_words(raw_text)
    
    duration = result.get("duration", 0)
    
    logging.info(f"✅ Transcribed {duration:.1f}s audio → {len(segments)} segments")
    logging.info(f"   Raw: {len(raw_text)} chars, Cleaned: {len(cleaned_text)} chars")
    
    return {
        "text": cleaned_text,
        "text_raw": raw_text,
        "segments": segments,
        "language": result.get("language", "ml"),
        "duration": duration
    }


def remove_filler_words(text):
    """
    Remove common Malayalam filler words while preserving meaning.
    
    Args:
        text: Malayalam text
    
    Returns:
        Cleaned text
    """
    cleaned = text
    
    # Remove filler words (case-sensitive for Malayalam)
    for filler in MALAYALAM_FILLERS:
        # Remove standalone fillers (with space boundaries)
        cleaned = re.sub(rf'\b{filler}\b', '', cleaned)
    
    # Remove multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Remove leading/trailing spaces
    cleaned = cleaned.strip()
    
    return cleaned


def normalize_malayalam_text(text):
    """
    Normalize slang and variations to standard spoken Malayalam.
    
    Common normalizations:
    - Slang → spoken Malayalam
    - English transliterations → Malayalam
    
    Args:
        text: Raw Malayalam text
    
    Returns:
        Normalized text
    """
    
    # Common slang normalizations (extend as needed)
    normalizations = {
        "ok": "ശരി",
        "super": "മികച്ചത്",
        "sorry": "ക്ഷമിക്കണം",
        # Add more as patterns emerge
    }
    
    normalized = text
    for slang, proper in normalizations.items():
        normalized = normalized.replace(slang, proper)
    
    return normalized


def split_into_sentences(text):
    """
    Split Malayalam text into sentences.
    
    Malayalam sentence boundaries:
    - Period (.)
    - Question mark (?)
    - Exclamation (!)
    
    Returns:
        List of sentences
    """
    # Split on sentence boundaries
    sentences = re.split(r'[.?!]+', text)
    
    # Clean up
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return sentences


def validate_transcription_quality(transcript_result, min_words=10):
    """
    Validates transcription quality.
    
    Checks:
    - Minimum word count
    - Malayalam characters present
    - Segment continuity
    
    Returns:
        dict with validation results
    """
    issues = []
    
    text = transcript_result.get("text", "")
    segments = transcript_result.get("segments", [])
    
    # Check word count
    word_count = len(text.split())
    if word_count < min_words:
        issues.append(f"Too few words: {word_count} (minimum {min_words})")
    
    # Check for Malayalam characters
    has_malayalam = any('\u0d00' <= char <= '\u0d7f' for char in text)
    if not has_malayalam:
        issues.append("No Malayalam characters detected")
    
    # Check segment continuity
    if len(segments) > 1:
        for i in range(len(segments) - 1):
            gap = segments[i+1]["start"] - segments[i]["end"]
            if gap > 5.0:  # More than 5 second gap
                issues.append(f"Large gap detected: {gap:.1f}s between segments {i} and {i+1}")
    
    passed = len(issues) == 0
    return {
        "passed": passed,
        "issues": issues,
        "word_count": word_count,
        "segment_count": len(segments),
        "has_malayalam": has_malayalam
    }


if __name__ == "__main__":
    # Test transcription
    import sys
    
    if len(sys.argv) > 1:
        test_audio = sys.argv[1]
        
        if os.path.exists(test_audio):
            result = transcribe_malayalam_audio(test_audio, context_hint="test content")
            
            print("\n" + "="*60)
            print("TRANSCRIPTION RESULT")
            print("="*60)
            print(f"\nDuration: {result['duration']:.1f}s")
            print(f"Segments: {len(result['segments'])}")
            print(f"\nCleaned Text:\n{result['text'][:500]}...")
            print(f"\nRaw Text:\n{result['text_raw'][:500]}...")
            
            # Validation
            validation = validate_transcription_quality(result)
            print(f"\n✅ Validation: {'PASSED' if validation['passed'] else 'FAILED'}")
            if validation['issues']:
                print(f"Issues: {validation['issues']}")
        else:
            print(f"Error: File not found: {test_audio}")
    else:
        print("Usage: python audio_transcriber.py <audio_file>")
