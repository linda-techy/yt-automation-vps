import os
import asyncio
import logging
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
        logging.error(f"[TTS] Voice generation failed: {e}")
        print(f"TTS Error: {e}")
        return None

def generate_voice_long(text, output_path="videos/temp/voice_long.mp3"):
    """
    Handles long-form text by chunking, generating segments, and concatenation.
    Essential for 8-10 min videos to avoid API timeouts.
    
    Raises:
        Exception: If voice generation fails (no silent failures)
    """
    from moviepy.editor import concatenate_audioclips, AudioFileClip
    
    chunk_files = []  # Track for cleanup
    audio_clips = []  # Track for cleanup
    
    try:
        # 1. Chunk Text (Split by newlines or approx 500 chars)
        chunks = [c.strip() for c in text.split('\n') if c.strip()]
        
        if not chunks:
            raise ValueError("No text content to convert to speech")
        
        logging.info(f"[TTS-Long] Processing {len(chunks)} chunks")
        print(f"Processing Long-Form Audio: {len(chunks)} chunks")
        
        # 2. Generate each chunk
        for i, chunk in enumerate(chunks):
            chunk_path = f"videos/temp/chunk_{i}.mp3"
            
            try:
                # Use existing single-gen function
                res = generate_voice(chunk, output_path=chunk_path)
                
                if not res:
                    raise Exception(f"Chunk {i} generation returned None")
                
                if not os.path.exists(res):
                    raise FileNotFoundError(f"Chunk file not created: {res}")
                
                # Validate audio file is not empty
                file_size = os.path.getsize(res)
                if file_size < 1000:  # Less than 1KB is suspicious
                    raise ValueError(f"Chunk {i} audio file too small ({file_size} bytes)")
                
                chunk_files.append(res)
                audio_clips.append(AudioFileClip(res))
                logging.info(f"[TTS-Long] Chunk {i+1}/{len(chunks)} complete ({file_size} bytes)")
                print(f"Generated Chunk {i+1}/{len(chunks)}")
                
            except Exception as e:
                logging.error(f"[TTS-Long] Chunk {i} failed: {e}")
                raise Exception(f"Failed to generate chunk {i}/{len(chunks)}: {str(e)}")
        
        if not audio_clips:
            raise Exception("No audio chunks generated successfully")
        
        # 3. Concatenate all chunks
        logging.info(f"[TTS-Long] Concatenating {len(audio_clips)} audio chunks...")
        final_audio = concatenate_audioclips(audio_clips)
        
        # 4. Write final output
        logging.info(f"[TTS-Long] Writing final audio to {output_path}")
        final_audio.write_audiofile(output_path, logger=None)  # Suppress moviepy verbose logging
        
        # 5. Validate output file
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Final audio file not created: {output_path}")
        
        final_size = os.path.getsize(output_path)
        if final_size < 10000:  # Less than 10KB is suspicious
            raise ValueError(f"Final audio file too small ({final_size} bytes)")
        
        logging.info(f"[TTS-Long] Success! Final audio: {final_size/1024:.1f}KB")
        print(f"[SUCCESS] Long-form audio generated: {final_size/1024:.1f}KB")
        
        return output_path
        
    except Exception as e:
        logging.error(f"[TTS-Long] FAILED: {str(e)}", exc_info=True)
        raise Exception(f"Long-form voice generation failed: {str(e)}")
        
    finally:
        # Cleanup: Close all audio clips to release file handles
        for clip in audio_clips:
            try:
                clip.close()
            except:
                pass

if __name__ == "__main__":
    generate_voice("This is a test of the automatic voice generation system.")
