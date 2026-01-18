"""
Topic Engine - AI-Driven Topic Discovery

Uses ONLY the niche from channel_config.yaml to:
1. AI generates trending search terms for that niche
2. Fetches real news using those terms
3. AI evaluates viral potential
4. Returns the best topic for content creation

NO HARDCODED KEYWORDS - fully intelligent and adaptive!
"""

import json
import logging
import os
from datetime import datetime
from difflib import SequenceMatcher

# Import channel configuration
try:
    from config.channel import channel_config, is_topic_allowed
except ImportError:
    channel_config = None
    is_topic_allowed = lambda x: True
    print("[TopicEngine] WARNING: channel_config not found")

HISTORY_FILE = "channel/topic_history.json"


def load_history() -> list:
    """Load topic usage history."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.debug(f"[Topic Engine] Failed to load history: {e}")
        return []


def save_history(history: list):
    """Save topic usage history."""
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def is_topic_used(topic: str, history: list) -> bool:
    """Check if topic was recently used (70% similarity threshold)."""
    for entry in history:
        ratio = SequenceMatcher(None, topic.lower(), entry.get("topic", "").lower()).ratio()
        if ratio > 0.70:
            logging.info(f"[Topic] Similar to previous: '{entry['topic'][:40]}' ({ratio:.0%})")
            return True
    return False


def get_topic() -> str:
    """
    Get the best viral topic for content creation.
    
    Uses AI-powered discovery based on channel niche:
    1. AI generates search terms from niche
    2. Fetches trending news
    3. AI evaluates viral potential
    4. Returns best unique topic
    
    Returns:
        str: Topic title for video creation
    
    Raises:
        Exception: If no suitable topic found (STRICT MODE)
    """
    from services.news_engine import get_best_viral_topic, get_latest_news
    
    # Get niche from config
    niche = channel_config.niche if channel_config else "Technology"
    print(f"[TopicEngine] AI discovering topics for: '{niche}'")
    
    history = load_history()
    
    # Try AI-powered viral topic selection first
    try:
        best_topic = get_best_viral_topic(niche)
        
        if best_topic:
            title = best_topic.get('title', '')
            
            # Check if allowed and not used
            if is_topic_allowed(title) and not is_topic_used(title, history):
                # Record usage
                history.append({
                    "topic": title,
                    "date": datetime.now().isoformat(),
                    "niche": niche,
                    "viral_score": best_topic.get('viral_score', 0),
                    "source": best_topic.get('source_keyword', 'AI Discovery')
                })
                save_history(history)
                
                print(f"[TopicEngine] SELECTED: {title[:60]}...")
                print(f"[TopicEngine] Viral Score: {best_topic.get('viral_score', 0)}/10")
                return title
    
    except Exception as e:
        logging.warning(f"[TopicEngine] AI viral selection failed: {e}")
    
    # Fallback: Get news and pick first unused
    try:
        news_items = get_latest_news(niche, max_results=5)
        
        for item in news_items:
            title = item.get('title', '')
            
            if not title:
                continue
            
            if not is_topic_allowed(title):
                continue
            
            if is_topic_used(title, history):
                continue
            
            # Found good topic
            history.append({
                "topic": title,
                "date": datetime.now().isoformat(),
                "niche": niche,
                "source": item.get('source_keyword', 'News')
            })
            save_history(history)
            
            print(f"[TopicEngine] SELECTED: {title[:60]}...")
            return title
    
    except Exception as e:
        logging.error(f"[TopicEngine] News fetch failed: {e}")
    
    # STRICT MODE: No fallbacks
    raise Exception(f"STRICT MODE: No suitable topics found for niche '{niche}'. Check news API connectivity.")


def get_topic_suggestions(count: int = 5) -> list:
    """
    Get multiple topic suggestions for preview/manual selection.
    
    Args:
        count: Number of suggestions
    
    Returns:
        List of topic dicts with title, viral_score, etc.
    """
    from services.news_engine import get_latest_news, evaluate_topic_viral_potential
    
    niche = channel_config.niche if channel_config else "Technology"
    news_items = get_latest_news(niche, max_results=count * 2)
    history = load_history()
    
    suggestions = []
    for item in news_items:
        title = item.get('title', '')
        
        if not title or not is_topic_allowed(title) or is_topic_used(title, history):
            continue
        
        suggestions.append({
            "title": title,
            "source": item.get('source_keyword', 'Unknown'),
            "url": item.get('url', item.get('href', '')),
            "niche": niche
        })
        
        if len(suggestions) >= count:
            break
    
    return suggestions


if __name__ == "__main__":
    print("AI Topic Discovery Test")
    print("=" * 50)
    
    if channel_config:
        print(f"Channel: {channel_config.channel_name}")
        print(f"Niche: {channel_config.niche}")
    
    print("\nDiscovering best topic...")
    try:
        topic = get_topic()
        print(f"\nFinal Topic: {topic}")
    except Exception as e:
        print(f"Error: {e}")
