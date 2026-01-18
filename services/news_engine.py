"""
AI-Powered Topic Discovery Engine

SMART TOPIC SELECTION BASED ONLY ON NICHE:
1. Read niche from channel_config.yaml
2. AI generates trending search terms for that niche
3. Fetch news using those terms
4. AI evaluates viral potential of each topic
5. Return the best topic for content creation

NO HARDCODED KEYWORDS - fully dynamic based on configured niche!
"""

import json
import logging
from datetime import datetime
from ddgs import DDGS

# Import channel configuration
try:
    from config.channel import channel_config
    CONFIG_LOADED = True
except ImportError:
    CONFIG_LOADED = False
    logging.warning("[NewsEngine] WARNING: channel_config not found")

# Use wrapped LLM adapter with error handling
from adapters.openai.llm_wrapper import get_llm_fast
from utils.logging.tracer import tracer
from langchain_core.messages import HumanMessage

llm = get_llm_fast()


def generate_search_terms(niche: str) -> list:
    """
    Use AI to generate trending search terms for the given niche.
    
    Args:
        niche: Channel niche (e.g., "Technology & Motivation", "Finance")
    
    Returns:
        List of 5-7 search terms optimized for finding viral content
    """
    current_year = datetime.now().year
    next_year = current_year + 1
    
    prompt = f"""You are a YouTube trend analyst. Generate 6 search terms to find VIRAL, TRENDING news for a "{niche}" YouTube channel.

REQUIREMENTS:
- Terms should find CURRENT, BREAKING news (not evergreen)
- Focus on what's trending RIGHT NOW in {niche}
- Include "{current_year}" or "{next_year}" for recency
- Mix: breakthroughs, controversies, predictions, discoveries
- Terms should be in English (for news search)

Return ONLY a JSON array of 6 search strings:
["term 1", "term 2", "term 3", "term 4", "term 5", "term 6"]"""

    try:
        response = llm.invoke(
            [HumanMessage(content=prompt)],
            trace_id=tracer.get_trace_id(),
            compress_context=True
        )
        
        content = response.content.strip()
        if "```" in content:
            content = content.split("```")[1].replace("json", "").strip()
        
        terms = json.loads(content)
        logging.info(f"[AI Topics] Generated {len(terms)} search terms for '{niche}'")
        return terms
        
    except Exception as e:
        logging.error(f"[AI Topics] Search term generation failed: {e}")
        # Fallback - use niche directly
        current_year = datetime.now().year
        return [
            f"{niche} breakthrough {current_year}",
            f"{niche} news today",
            f"Latest {niche} discovery",
            f"{niche} future predictions {current_year+1}"
        ]


def evaluate_topic_viral_potential(topics: list, niche: str) -> dict:
    """
    Use AI to evaluate which topic has the highest viral potential.
    
    Args:
        topics: List of topic dicts with 'title'
        niche: Channel niche
    
    Returns:
        Best topic dict with viral score and reasoning
    """
    if not topics:
        return None
    
    topics_text = "\n".join([f"{i+1}. {t.get('title', 'Unknown')}" for i, t in enumerate(topics[:10])])
    
    prompt = f"""You are a YouTube content strategist for a "{niche}" channel.
    
Evaluate these news topics and pick the ONE with highest viral potential:

{topics_text}

VIRAL CRITERIA:
1. Curiosity Gap - Does it make people WANT to know more?
2. Emotional Trigger - Fear, excitement, surprise, hope?
3. Relevance - Does it affect viewers personally?
4. Shareability - Would people share this?
5. Controversy - Is there debate or strong opinions?
6. Timeliness - Is this breaking/urgent?

Return JSON:
{{
    "best_index": 1,
    "viral_score": 8.5,
    "reasoning": "Why this topic will go viral",
    "hook_angle": "Suggested video hook approach",
    "thumbnail_concept": "Eye-catching thumbnail idea"
}}"""

    try:
        response = llm.invoke(
            [HumanMessage(content=prompt)],
            trace_id=tracer.get_trace_id(),
            compress_context=True
        )
        
        content = response.content.strip()
        if "```" in content:
            content = content.split("```")[1].replace("json", "").strip()
        
        result = json.loads(content)
        best_index = result.get("best_index", 1) - 1
        
        if 0 <= best_index < len(topics):
            selected = topics[best_index]
            selected["viral_score"] = result.get("viral_score", 7.0)
            selected["reasoning"] = result.get("reasoning", "")
            selected["hook_angle"] = result.get("hook_angle", "")
            return selected
        
        return topics[0]
        
    except Exception as e:
        logging.error(f"[AI Topics] Viral evaluation failed: {e}")
        return topics[0] if topics else None


def get_latest_news(niche: str = None, max_results: int = 3) -> list:
    """
    Fetch trending news for the configured niche.
    
    Args:
        niche: Override niche (uses config if not provided)
        max_results: Max results per search term
    
    Returns:
        List of news dicts with title, url, body
    """
    # Get niche from config if not provided
    if not niche and CONFIG_LOADED:
        niche = channel_config.niche
    elif not niche:
        niche = "Technology"
    
    logging.info(f"[AI Topics] Discovering topics for niche: '{niche}'")
    
    # Step 1: AI generates search terms based on niche
    search_terms = generate_search_terms(niche)
    
    # Step 2: Fetch news for each term
    all_results = []
    
    for term in search_terms:
        try:
            results = DDGS().news(
                query=term, 
                region="wt-wt", 
                safesearch="moderate",
                timelimit="w",  # Last week
                max_results=max_results
            )
            for r in results:
                r['source_keyword'] = term
                r['niche'] = niche
                all_results.append(r)
                
        except Exception as e:
            logging.warning(f"[AI Topics] News fetch error for '{term}': {e}")
            continue
    
    logging.info(f"[AI Topics] Fetched {len(all_results)} news items")
    return all_results


def get_best_viral_topic(niche: str = None) -> dict:
    """
    Get the single best viral topic for content creation.
    
    This is the main function to call - combines:
    1. AI-generated search terms
    2. News fetching
    3. AI viral potential evaluation
    
    Returns:
        Best topic dict with title, viral_score, reasoning, etc.
    """
    # Get niche from config
    if not niche and CONFIG_LOADED:
        niche = channel_config.niche
    elif not niche:
        niche = "Technology"
    
    # Fetch news
    news_items = get_latest_news(niche, max_results=3)
    
    if not news_items:
        raise Exception(f"No news found for niche: {niche}")
    
    # AI evaluates viral potential
    best = evaluate_topic_viral_potential(news_items, niche)
    
    if not best:
        raise Exception("AI topic evaluation failed")
    
    logging.info(f"[AI Topics] BEST TOPIC: {best.get('title', 'Unknown')[:60]}...")
    logging.info(f"[AI Topics] Viral Score: {best.get('viral_score', 0)}/10")
    
    return best


# Backwards compatibility alias
def get_latest_tech_news(max_results: int = 3) -> list:
    """Legacy function - now uses AI-driven discovery."""
    return get_latest_news(max_results=max_results)


if __name__ == "__main__":
    print("AI Topic Discovery Test")
    print("=" * 50)
    
    if CONFIG_LOADED:
        print(f"Channel: {channel_config.channel_name}")
        print(f"Niche: {channel_config.niche}")
    
    print("\nDiscovering best viral topic...")
    topic = get_best_viral_topic()
    print(json.dumps(topic, indent=2, default=str))
