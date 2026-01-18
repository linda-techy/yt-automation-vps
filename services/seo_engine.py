"""
Dynamic SEO Engine - Config-Driven Metadata Generation

Generates Title, Description, and Tags dynamically based on:
- Channel Config (Language, Niche, Persona)
- Topic settings

Uses AI to craft engaging, SEO-optimized metadata with token optimization.
"""

import os
import json
import logging
from dotenv import load_dotenv

# Import channel configuration
try:
    from config.channel import channel_config
    CONFIG_LOADED = True
except ImportError:
    CONFIG_LOADED = False
    print("[SEO] WARNING: channel_config not found")

load_dotenv()

# Use wrapped LLM with error handling
from adapters.openai.llm_wrapper import get_llm_fast
from utils.prompts.registry import registry
from utils.logging.tracer import tracer
from langchain_core.messages import HumanMessage

llm = get_llm_fast()


def get_seo_prompt(topic: str) -> str:
    """Generate dynamic SEO prompt using registry."""
    return registry.get_seo_prompt(topic)


def generate_seo(topic: str) -> dict:
    """Generate optimized SEO metadata for the given topic."""
    prompt = get_seo_prompt(topic)
    
    try:
        response = llm.invoke(
            [HumanMessage(content=prompt)],
            trace_id=tracer.get_trace_id(),
            compress_context=True
        )
        seo_content = response.content.strip()
    except Exception as e:
        logging.error(f"[SEO] Error generating metadata: {e}")
        seo_content = f"Title: {topic}\n\nDescription: {topic}\n#Viral"

    # Parse the response
    title = topic
    description = topic
    tags = []
    
    try:
        # Try to parse structured format
        if "Title:" in seo_content:
            parts = seo_content.split("Title:")
            if len(parts) > 1:
                title_part = parts[1].split("\n")[0].strip()
                title = title_part if title_part else topic
        
        if "Description:" in seo_content:
            desc_part = seo_content.split("Description:")[1]
            if "Hashtags:" in desc_part:
                description = desc_part.split("Hashtags:")[0].strip()
            else:
                description = desc_part.strip()
        
        if "Hashtags:" in seo_content:
            tags_part = seo_content.split("Hashtags:")[1].strip()
            # Extract hashtags
            tags = [tag.strip("#").strip() for tag in tags_part.split("#") if tag.strip()]
    except Exception as e:
        logging.warning(f"[SEO] Parsing failed: {e}, using defaults")
    
    # Add Dynamic Footer from Config
    footer = ""
    if CONFIG_LOADED:
        try:
            footer = channel_config.get("seo.description_footer", "").format(
                channel_handle=channel_config.channel_handle,
                copyright_year=channel_config.get("channel.copyright_year", 2025)
            )
            if footer:
                description += "\n\n" + footer
        except Exception as e:
            logging.debug(f"[SEO Engine] Failed to add footer: {e}")
    
    # Default tags if none found
    if not tags:
        if CONFIG_LOADED:
            tags = channel_config.get("seo.default_tags", [])
        if not tags:
            tags = ["Viral", "Trending", "Tech"]
    
    result = {
        "title": title,
        "description": description,
        "tags": tags[:10]  # YouTube limit
    }
    
    logging.info(f"[SEO] Generated metadata: {title[:50]}...")
    return result


if __name__ == "__main__":
    # Test
    test_topic = "AI Revolution 2026"
    seo = generate_seo(test_topic)
    print(json.dumps(seo, indent=2, ensure_ascii=False))
