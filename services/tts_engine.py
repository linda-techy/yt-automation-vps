import os
import asyncio
import edge_tts
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI only if needed
openai_client = None

async def generate_voice_edge(text, voice, output_path):
    """Generates audio using edge-tts (Free, High Quality)"""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def normalize_text_for_pronunciation(text):
    """
    Replaces common acronyms with dotted versions to force letter-by-letter pronunciation.
    Extensible list for Malayalam/English TTS context.
    """
    import re
    
    # Dictionary of words that need explicit pronunciation helpers
    replacements = {
        "AI": "A.I.",
        "GPT": "G.P.T.",
        "CEO": "C.E.O.",
        "CTO": "C.T.O.",
        "CFO": "C.F.O.",
        "MBA": "M.B.A.",
        "API": "A.P.I.",
        "URL": "U.R.L.",
        "USB": "U.S.B.",
        "CPU": "C.P.U.",
        "GPU": "G.P.U.",
        "RAM": "R.A.M.",
        "ROM": "R.O.M.",
        "SEO": "S.E.O.",
        "DIY": "D.I.Y.",
        "IoT": "I.o.T.",
        "5G": "Five G",
        "ML": "M.L.",
        "AR": "A.R.",
        "VR": "V.R.",
        "NFT": "N.F.T.",
        "DAO": "D.A.O.",
        "DeFi": "D.F.I.",
        "CRM": "C.R.M.",
        "ERP": "E.R.P.",
        "SaaS": "S.A.A.S.",
        "IT": "I.T.",
        "HR": "H.R.",
        "PR": "P.R.",
        "UI": "U.I.",
        "UX": "U.X.",
        "PDF": "P.D.F.",
        "FAQ": "F.A.Q.",
        # Add more here as discovered
    }
    
    # 1. Replace explicit dictionary matches (using word boundaries)
    for word, replacement in replacements.items():
        # \b ensures we don't replace "PAIN" with "PA.I.N" when matching "AI"
        pattern = r'\b' + re.escape(word) + r'\b'
        text = re.sub(pattern, replacement, text)
        
    return text

def generate_voice(text, output_path="videos/temp/voice.mp3"):
    """
    Generates audio from text using Edge TTS (default) or OpenAI TTS.
    Returns the absolute path to the generated audio file.
    """
    try:
        from config.channel import channel_config
        
        # Pre-process text to fix pronunciation issues (e.g. AI -> A.I.)
        text = normalize_text_for_pronunciation(text)
        
        engine = channel_config.get("audio.engine", "edge-tts")
        
        # Default high-quality realistic voices for Edge-TTS
        # en-US-GuyNeural, en-US-AvaNeural, en-US-EmmaNeural
        selected_voice = channel_config.voice_id
        
        print(f"Using TTS Engine: {engine} | Voice: {selected_voice}")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        if engine == "openai":
            global openai_client
            if openai_client is None:
                openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            response = openai_client.audio.speech.create(
                model="tts-1-hd",
                voice=selected_voice if selected_voice in ["onyx", "alloy", "echo", "fable", "nova", "shimmer"] else "onyx",
                input=text
            )
            response.stream_to_file(output_path)
        else:
            # Run edge-tts asynchronously
            asyncio.run(generate_voice_edge(text, selected_voice, output_path))

        return output_path
    except Exception as e:
        print(f"TTS Error: {e}")
        return None

def generate_voice_long(text, output_path="videos/temp/voice_long.mp3"):
    """
    Handles long-form text by chunking, generating segments, and concatenation.
    Essential for 8-10 min videos to avoid API timeouts.
    """
    try:
        from moviepy.editor import concatenate_audioclips, AudioFileClip
        import glob
        
        # 1. Chunk Text (Split by newlines or approx 500 chars)
        chunks = [c.strip() for c in text.split('\n') if c.strip()]
        
        audio_files = []
        full_audio_clips = []
        
        print(f"Processing Long-Form Audio: {len(chunks)} chunks")
        
        for i, chunk in enumerate(chunks):
            chunk_path = f"videos/temp/chunk_{i}.mp3"
            
            # Use existing single-gen function
            res = generate_voice(chunk, output_path=chunk_path)
            
            if res and os.path.exists(res):
                audio_files.append(res)
                full_audio_clips.append(AudioFileClip(res))
                print(f"Generated Chunk {i+1}/{len(chunks)}")
            else:
                print(f"Failed to generate chunk {i}: {chunk[:50]}...")
                
        if not full_audio_clips:
            return None
            
        # 2. Concatenate
        final_audio = concatenate_audioclips(full_audio_clips)
        final_audio.write_audiofile(output_path)
        
        # Cleanup clips to close file handles
        for c in full_audio_clips: 
            c.close()
            
        return output_path
        
    except Exception as e:
        print(f"Long-Form TTS Error: {e}")
        return None

if __name__ == "__main__":
    generate_voice("This is a test of the automatic voice generation system.")
