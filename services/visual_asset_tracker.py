"""
Visual Asset Deduplication Engine

Tracks which visual assets have been used across videos to prevent:
1. Same Pixabay video appearing in multiple videos
2. Similar AI-generated scenes across content
3. Repetitive visual patterns that hurt YPP

YPP REQUIREMENT: YouTube flags channels that reuse the same stock footage
across multiple videos as "low-quality compilation content."
"""

import os
import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Set, Optional

VISUAL_HISTORY_FILE = "channel/visual_asset_history.json"
MAX_HISTORY_DAYS = 30  # Keep track of visuals used in last 30 days

def load_visual_history() -> dict:
    """Load visual asset usage history."""
    if not os.path.exists(VISUAL_HISTORY_FILE):
        return {"assets": [], "last_cleanup": None}
    
    try:
        with open(VISUAL_HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"[VisualTracker] Failed to load history: {e}")
        return {"assets": [], "last_cleanup": None}

def save_visual_history(history: dict):
    """Save visual asset usage history."""
    os.makedirs(os.path.dirname(VISUAL_HISTORY_FILE), exist_ok=True)
    try:
        with open(VISUAL_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logging.error(f"[VisualTracker] Failed to save history: {e}")

def generate_asset_fingerprint(asset_path: str, query: str = None) -> str:
    """
    Generate a fingerprint for an asset based on:
    - For Pixabay: The search query used (normalized)
    - For AI: The prompt hash
    - For files: The filename pattern
    """
    if "pixabay_" in asset_path:
        # Use query as fingerprint for Pixabay
        if query:
            return f"pixabay:{query.lower().strip()}"
        return f"pixabay:{os.path.basename(asset_path)}"
    
    elif "ai_scene_" in asset_path:
        # For AI images, use prompt hash
        if query:
            prompt_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            return f"ai:{prompt_hash}"
        return f"ai:{os.path.basename(asset_path)}"
    
    else:
        # Generic file
        return f"file:{os.path.basename(asset_path)}"

def is_visual_recently_used(query: str, asset_type: str = "pixabay") -> bool:
    """
    Check if a visual (by query/prompt) was used recently.
    
    Args:
        query: Search query or prompt
        asset_type: "pixabay" or "ai"
    
    Returns:
        True if visual was used in the last 30 days
    """
    history = load_visual_history()
    cutoff = datetime.now() - timedelta(days=MAX_HISTORY_DAYS)
    
    fingerprint = f"{asset_type}:{query.lower().strip()}"
    
    for asset in history.get("assets", []):
        if asset["fingerprint"] == fingerprint:
            try:
                used_at = datetime.fromisoformat(asset["used_at"])
                if used_at > cutoff:
                    logging.warning(f"[VisualTracker] Visual recently used: '{query[:40]}...'")
                    return True
            except:
                pass
    
    return False

def get_used_visual_queries(days: int = MAX_HISTORY_DAYS) -> Set[str]:
    """Get all visual queries used in the last N days."""
    history = load_visual_history()
    cutoff = datetime.now() - timedelta(days=days)
    
    used_queries = set()
    for asset in history.get("assets", []):
        try:
            used_at = datetime.fromisoformat(asset["used_at"])
            if used_at > cutoff:
                query = asset.get("query", "")
                if query:
                    used_queries.add(query.lower().strip())
        except:
            pass
    
    return used_queries

def record_visual_usage(query: str, asset_path: str, asset_type: str = "pixabay", 
                       video_topic: str = None):
    """
    Record that a visual asset was used.
    
    Args:
        query: Search query or prompt used
        asset_path: Local path to downloaded asset
        asset_type: "pixabay" or "ai"
        video_topic: Topic of the video (for context)
    """
    history = load_visual_history()
    
    fingerprint = f"{asset_type}:{query.lower().strip()}"
    
    entry = {
        "fingerprint": fingerprint,
        "query": query,
        "asset_type": asset_type,
        "asset_path": asset_path,
        "video_topic": video_topic,
        "used_at": datetime.now().isoformat()
    }
    
    history["assets"].append(entry)
    save_visual_history(history)
    
    logging.debug(f"[VisualTracker] Recorded: {asset_type} → '{query[:30]}...'")

def cleanup_old_history():
    """Remove entries older than MAX_HISTORY_DAYS."""
    history = load_visual_history()
    cutoff = datetime.now() - timedelta(days=MAX_HISTORY_DAYS)
    
    original_count = len(history.get("assets", []))
    
    history["assets"] = [
        asset for asset in history.get("assets", [])
        if datetime.fromisoformat(asset.get("used_at", "1970-01-01")) > cutoff
    ]
    
    history["last_cleanup"] = datetime.now().isoformat()
    save_visual_history(history)
    
    removed = original_count - len(history["assets"])
    if removed > 0:
        logging.info(f"[VisualTracker] Cleaned {removed} old entries")

def get_alternative_query(original_query: str, niche: str = "Technology") -> str:
    """
    Generate an alternative search query if original was recently used.
    Uses AI to create a semantically similar but different query.
    """
    # Use wrapped LLM adapter
    from adapters.openai.llm_wrapper import get_llm_fast
    from utils.logging.tracer import tracer
    from langchain_core.messages import HumanMessage
    
    llm_alt = get_llm_fast()
    
    prompt = f"""Generate 1 alternative search query for stock video/images.

Original: "{original_query}"
Niche: {niche}

Requirements:
- Same concept/meaning
- Different keywords
- Still relevant to the topic

Return ONLY the alternative query, nothing else."""
    
    try:
        response = llm_alt.invoke(
            [HumanMessage(content=prompt)],
            trace_id=tracer.get_trace_id(),
            compress_context=True
        )
        
        alternative = response.content.strip()
        logging.info(f"[VisualTracker] Alternative: '{original_query[:30]}' → '{alternative[:30]}'")
        return alternative
        
    except Exception as e:
        logging.warning(f"[VisualTracker] Alternative generation failed: {e}")
        # Simple fallback: add modifiers
        modifiers = ["cinematic", "dramatic", "futuristic", "modern", "closeup"]
        import random
        return f"{random.choice(modifiers)} {original_query}"

def deduplicate_visual_cues(visual_cues: List[str], video_topic: str = None) -> List[str]:
    """
    Process visual cues to avoid recently used queries.
    
    Args:
        visual_cues: Original list of visual cues from script
        video_topic: Current video topic
    
    Returns:
        Deduplicated visual cues with alternatives where needed
    """
    used_queries = get_used_visual_queries()
    deduplicated = []
    
    # Get niche from config
    try:
        from config.channel import channel_config
        niche = channel_config.niche
    except:
        niche = "Technology"
    
    for cue in visual_cues:
        cue_lower = cue.lower().strip()
        
        if cue_lower in used_queries:
            # Generate alternative
            alternative = get_alternative_query(cue, niche)
            deduplicated.append(alternative)
            logging.info(f"[VisualTracker] Replaced duplicate: '{cue[:30]}...'")
        else:
            deduplicated.append(cue)
    
    return deduplicated

def get_visual_stats() -> dict:
    """Get visual asset usage statistics."""
    history = load_visual_history()
    
    by_type = {}
    for asset in history.get("assets", []):
        asset_type = asset.get("asset_type", "unknown")
        by_type[asset_type] = by_type.get(asset_type, 0) + 1
    
    return {
        "total_assets": len(history.get("assets", [])),
        "by_type": by_type,
        "last_cleanup": history.get("last_cleanup"),
        "tracking_days": MAX_HISTORY_DAYS
    }

if __name__ == "__main__":
    print("Visual Asset Tracker Test")
    print("=" * 50)
    print(json.dumps(get_visual_stats(), indent=2))
