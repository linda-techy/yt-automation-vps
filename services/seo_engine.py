"""
Dynamic SEO Engine - Config-Driven Metadata Generation

Generates Title, Description, and Tags dynamically based on:
- Channel Config (Language, Niche, Persona)
- Topic settings

Uses AI to craft engaging, SEO-optimized metadata.
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# Import channel configuration
try:
    from config.channel import channel_config
    CONFIG_LOADED = True
except ImportError:
    CONFIG_LOADED = False
    print("[SEO] WARNING: channel_config not found")

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_seo_prompt(topic: str) -> str:
    """Generate dynamic SEO prompt based on channel config."""
    if CONFIG_LOADED:
        ctx = {
            "channel": channel_config.channel_name,
            "language": channel_config.get("channel.language", "en"),
            "language_name": _get_language_name(channel_config.get("channel.language", "en")),
            "niche": channel_config.niche,
            "country": channel_config.get("channel.country", "US")
        }
    else:
        ctx = {
            "channel": "My Channel",
            "language_name": "English",
            "niche": "Tech",
            "country": "US"
        }
        
    return f"""You are a YouTube SEO Expert for the "{ctx['channel']}" channel.
NICHE: {ctx['niche']}
TARGET AUDIENCE: {ctx['language_name']} speakers in {ctx['country']}

TOPIC: {topic}

Create high-CTR YouTube video metadata:

RULES:
1. Title: Catchy, under 70 chars. Mix {ctx['language_name']} and English if common (e.g., Manglish/Hinglish).
2. Description: 
   - 2 paragraph summary in {ctx['language_name']}.
   - Explain value/hook clearly.
   - Professional tone.
3. Hashtags: 5-7 relevant tags (include niche and language tags).

Return in this format:
Title: [Your Title Here]

Description:
[Your Description Here]

Hashtags:
#Tag1 #Tag2 ...
"""

def _get_language_name(code: str) -> str:
    lang_map = {
        "ml": "Malayalam", "hi": "Hindi", "ta": "Tamil", "en": "English",
        "es": "Spanish", "fr": "French", "de": "German"
    }
    return lang_map.get(code.lower(), "English")


def generate_seo(topic: str) -> str:
    """Generate optimized SEO metadata for the given topic."""
    prompt = get_seo_prompt(topic)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        seo_content = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[SEO] Error generating metadata: {e}")
        seo_content = f"Title: {topic}\n\nDescription: {topic}\n#Viral"

    # Add Dynamic Footer from Config
    footer = ""
    if CONFIG_LOADED:
        footer = f"""
------------------------------------------------
{channel_config.get("seo.description_footer", "").format(
    channel_handle=channel_config.channel_handle,
    channel_name=channel_config.channel_name,
    copyright_year=channel_config.get("channel.copyright_year", 2025)
)}
        """
    
    # Append footer
    return seo_content + "\n" + footer


if __name__ == "__main__":
    t = "DeepSeek vs ChatGPT: Who Won?"
    print(generate_seo(t))
