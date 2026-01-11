
from services.tts_engine import generate_voice
import asyncio
import os

print("Generating Malayalam Test Audio...")
text = "നമസ്കാരം, ഫിൻമൈൻഡ് മലയാളത്തിലേക്ക് സ്വാഗതം. ഇതൊരു പരീക്ഷണ ശബ്ദമാണ്."
# "Hello, welcome to FinMind Malayalam. This is a test voice."

output_file = "videos/temp/test_malayalam.mp3"

if os.path.exists(output_file):
    os.remove(output_file)

# The generate_voice function in tts_engine handles the async call internally if engine is edge-tts
# But looking at tts_engine.py:
# if engine == "openai": ...
# else: asyncio.run(generate_voice_edge(...))
# So we can just call generate_voice synchronous wrapper.

try:
    path = generate_voice(text, output_file)
    if path and os.path.exists(path):
        size = os.path.getsize(path)
        print(f"SUCCESS: Generated {path} ({size} bytes)")
    else:
        print("FAILURE: File not created.")
except Exception as e:
    print(f"ERROR: {e}")
