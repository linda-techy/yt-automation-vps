"""
Visual Decision Engine
Determines WHAT visual to generate and FROM WHERE based on intent
"""

import logging
from typing import Dict, List


# STRICT VISUAL DECISION RULES (Production)
VISUAL_DECISION_RULES = {
    "PERSON_STORY": {
        "source": "pixabay",
        "visual_type": "real_footage",
        "search_strategy": "semantic_human",
        "mandatory_keywords": ["Indian", "realistic", "natural lighting"],
        "avoid_keywords": ["studio", "stock", "posed"]
    },
    
    "HOW_IT_WORKS": {
        "source": "dalle",
        "visual_type": "diagram",
        "style": "educational",
        "mandatory_elements": ["minimal", "flat illustration", "simple shapes"],
        "forbidden_elements": ["cinematic", "fantasy", "complex scene"]
    },
    
    "MISTAKE_WARNING": {
        "source": "dalle",
        "visual_type": "symbolic",
        "style": "warning",
        "mandatory_elements": ["simple icon", "warning tone", "minimal"],
        "forbidden_elements": ["people", "locations", "text"]
    },
    
    "EMOTIONAL_REACTION": {
        "source": "pixabay",
        "visual_type": "facial",
        "search_strategy": "emotion_focused",
        "mandatory_keywords": ["close-up", "expression", "Indian"],
        "avoid_keywords": ["group", "landscape"]
    },
    
    "FACT_STATEMENT": {
        "source": "generated",
        "visual_type": "motion_graphics",
        "style": "minimal_text",
        "animation": "subtle"
    },
    
    "ADVICE_TIP": {
        "source": "pixabay",
        "visual_type": "lifestyle",
        "search_strategy": "neutral_context",
        "mandatory_keywords": ["Indian", "daily life", "simple"],
        "avoid_keywords": ["dramatic", "artistic"]
    }
}


def make_visual_decision(chunk):
    """
    Makes strict visual generation decision based on intent.
    
    Args:
        chunk: Audio chunk with intent classification
    
    Returns:
        Decision dict with source, prompt/query, and strict rules
    """
    
    intent = chunk.get("intent", "FACT_STATEMENT")
    rules = VISUAL_DECISION_RULES.get(intent)
    
    if not rules:
        logging.warning(f"Unknown intent: {intent}, using safe default")
        rules = VISUAL_DECISION_RULES["FACT_STATEMENT"]
    
    decision = {
        "source": rules["source"],
        "intent": intent,
        "visual_type": rules.get("visual_type"),
        "chunk_duration": chunk.get("duration", 10)
    }
    
    # Build decision based on source
    if rules["source"] == "pixabay":
        decision.update(_build_pixabay_decision_strict(chunk, rules))
    elif rules["source"] == "dalle":
        decision.update(_build_dalle_decision_strict(chunk, rules))
    elif rules["source"] == "generated":
        decision.update(_build_motion_graphics_decision(chunk, rules))
    
    logging.info(f"Visual decision: {decision['source']} ({intent})")
    
    return decision


def _build_pixabay_decision_strict(chunk, rules):
    """
    Builds STRICT Pixabay search with mandatory keywords.
    
    Format: "Indian person {emotion} {action}, realistic, natural lighting, no studio, no text"
    """
    
    text = chunk.get("text", "")
    emotion = _detect_emotion_strict(text)
    action = _detect_action_strict(text)
    
    # Build query with MANDATORY keywords
    mandatory = " ".join(rules.get("mandatory_keywords", []))
    avoid = rules.get("avoid_keywords", [])
    
    if rules.get("search_strategy") == "emotion_focused":
        # Emotional reaction: close-up facial expression
        query = f"{emotion} facial expression close-up, {mandatory}, authentic"
    elif rules.get("search_strategy") == "semantic_human":
        # Person story: realistic human in context
        query = f"{emotion} person {action}, {mandatory}, daily life context"
    else:
        # Neutral lifestyle
        query = f"{action} lifestyle, {mandatory}, simple scene"
    
    return {
        "search_query": query.strip(),
        "mandatory_keywords": rules.get("mandatory_keywords", []),
        "avoid_keywords": avoid,
        "search_strategy": rules.get("search_strategy")
    }


def _build_dalle_decision_strict(chunk, rules):
    """
    Builds STRICT DALL-E prompt (educational only, no artistic).
    
    Template enforces:
    - Minimal flat illustration
    - Educational style
    - Simple colors
    - No text, no background clutter
    """
    
    text = chunk.get("text", "")
    concept = _extract_simple_concept(text)
    
    # Mandatory elements
    mandatory = ", ".join(rules.get("mandatory_elements", []))
    forbidden = rules.get("forbidden_elements", [])
    
    # Build strict prompt
    if rules.get("style") == "educational":
        # How it works: diagram/explainer
        prompt = f"""Minimal flat illustration explaining {concept}.
Educational style, {mandatory}, no text, simple colors, clear focus, white background.
Avoid: {", ".join(forbidden)}."""
    
    elif rules.get("style") == "warning":
        # Mistake warning: symbolic icon
        prompt = f"""Simple symbolic illustration showing {concept}.
Warning tone, {mandatory}, clean symbol, professional colors.
Avoid: {", ".join(forbidden)}."""
    
    else:
        # Generic educational
        prompt = f"""Minimal clean visual for {concept}.
{mandatory}, simple design, educational.
Avoid: {", ".join(forbidden)}."""
    
    return {
        "dalle_prompt": prompt.strip(),
        "dalle_style": rules.get("style"),
        "dalle_size": "1792x1024",  # Landscape
        "mandatory_elements": rules.get("mandatory_elements", []),
        "forbidden_elements": forbidden
    }


def make_visual_decision(chunk):
    """
    Makes decision about visual generation based on chunk intent.
    
    Args:
        chunk: Audio chunk with intent classification
    
    Returns:
        {
            "source": "pixabay" | "dalle" | "generated",
            "strategy": "...",
            "search_query": "..." (if Pixabay),
            "prompt": "..." (if DALL-E),
            "filters": {...},
            "fallback": {...}
        }
    """
    
    intent = chunk.get("intent", "fact_statement")
    rules = VISUAL_DECISION_RULES.get(intent, VISUAL_DECISION_RULES["fact_statement"])
    
    decision = {
        "source": rules["source"],
        "intent": intent,
        "chunk_duration": chunk.get("duration", 10)
    }
    
    # Build decision based on source
    if rules["source"] == "pixabay":
        decision.update(_build_pixabay_decision(chunk, rules))
    elif rules["source"] == "dalle":
        decision.update(_build_dalle_decision(chunk, rules))
    elif rules["source"] == "generated":
        decision.update(_build_motion_graphics_decision(chunk, rules))
    
    # Add fallback strategy
    if "alternative_source" in rules:
        decision["fallback"] = {
            "source": rules["alternative_source"],
            "reason": "primary_source_failed"
        }
    
    logging.info(f"Visual decision: {decision['source']} for intent '{intent}'")
    
    return decision


def _build_pixabay_decision(chunk, rules):
    """
    Builds Pixabay search decision with semantic query.
    """
    
    # Extract context from chunk
    text = chunk.get("text", "")
    topic = chunk.get("topic", "")
    
    # Detect emotion, action, context
    emotion = _detect_emotion(text)
    action = _detect_action(text)
    context = _extract_context(topic)
    
    # Build semantic search query
    template = rules.get("search_template", "{emotion} {action}")
    query = template.format(
        emotion=emotion,
        ethnicity="Indian",  # Prefer culturally relevant
        action=action,
        context=context
    )
    
    return {
        "search_query": query.strip(),
        "search_strategy": rules.get("search_strategy", "semantic"),
        "filters": rules.get("filters", {}),
        "avoid_keywords": rules.get("avoid", [])
    }


def _build_dalle_decision(chunk, rules):
    """
    Builds DALL-E prompt with controlled generation.
    """
    
    text = chunk.get("text", "")
    topic = chunk.get("topic", "")
    
    # Extract concept
    concept = _extract_core_concept(text, topic)
    
    # Build prompt
    template = rules.get("prompt_template", "Minimal illustration of {concept}")
    prompt = template.format(
        concept=concept,
        topic=topic,
        mistake_concept=concept if "mistake" in chunk.get("intent", "") else "",
        item_a=concept.split("vs")[0] if "vs" in concept else concept,
        item_b=concept.split("vs")[1] if "vs" in concept else ""
    )
    
    return {
        "dalle_prompt": prompt,
        "dalle_style": rules.get("style", "minimal"),
        "dalle_size": rules.get("size", "1024x1024"),
        "avoid_elements": rules.get("avoid", [])
    }


def _build_motion_graphics_decision(chunk, rules):
    """
    Builds motion graphics specification.
    """
    
    text = chunk.get("text", "")
    
    # Extract key phrases
    keywords = _extract_keywords(text)
    
    return {
        "type": "motion_graphics",
        "keywords": keywords[:5],  # Max 5 keywords
        "style": rules.get("style", "minimal"),
        "animation": rules.get("animation", "subtle"),
        "background": "gradient"
    }


def _detect_emotion(text):
    """
    Detects primary emotion from text.
    """
    emotion_keywords = {
        "confused": ["പിഴവ്", "തെറ്റ്", "ആശയക്കുഴപ്പം"],
        "happy": ["സന്തോഷം", "നല്ല", "മികച്ച"],
        "shocked": ["ഞെട്ടിക്കുന്ന", "അതിശയം", "വിശ്വസിക്കാൻ"],
        "worried": ["ആശങ്ക", "പ്രശ്നം", "അപകടം"],
        "focused": ["ശ്രദ്ധ", "പ്രധാനം", "ഗൗരവം"]
    }
    
    for emotion, keywords in emotion_keywords.items():
        if any(kw in text for kw in keywords):
            return emotion
    
    return "neutral"


def _detect_action(text):
    """
    Detects primary action from text.
    """
    action_keywords = {
        "thinking": ["ചിന്തിക്കുക", "ആലോചിക്കുക"],
        "explaining": ["വിശദീകരിക്കുക", "പറയുക"],
        "working": ["പ്രവർത്തിക്കുക", "ചെയ്യുക"],
        "learning": ["പഠിക്കുക", "മനസ്സിലാക്കുക"]
    }
    
    for action, keywords in action_keywords.items():
        if any(kw in text for kw in keywords):
            return action
    
    return "focused"


def _extract_context(topic):
    """
    Extracts visual context from topic.
    """
    context_map = {
        "technology": "office technology",
        "programming": "coding workspace",
        "business": "professional setting",
        "education": "learning environment"
    }
    
    for key, context in context_map.items():
        if key in topic.lower():
            return context
    
    return "professional"


def _extract_core_concept(text, topic):
    """
    Extracts core concept for DALL-E.
    """
    # Simple extraction - first 50 chars or topic
    return topic or text[:50].strip()


def _extract_keywords(text):
    """
    Extracts key Malayalam words for motion graphics.
    """
    # Remove common filler words and extract nouns/verbs
    words = text.split()
    # Simple heuristic: words longer than 4 chars
    keywords = [w for w in words if len(w) > 4][:5]
    return keywords


def _detect_emotion_strict(text):
    """
    Detects primary emotion using strict Malayalam patterns.
    """
    emotion_patterns = {
        "confused": ["പിഴവ്", "ആശയക്കുഴപ്പം", "മനസ്സിലായില്ല"],
        "worried": ["ആശങ്ക", "ഭയം", "പ്രശ്നം"],
        "shocked": ["ഞെട്ടി", "അതിശയം", "വിശ്വസിക്കാൻ"],
        "happy": ["സന്തോഷം", "നല്ല", "മികച്ച"],
        "focused": ["ശ്രദ്ധ", "പ്രധാനം", "കൃത്യം"]
    }
    
    for emotion, patterns in emotion_patterns.items():
        if any(p in text for p in patterns):
            return emotion
    
    return "neutral"


def _detect_action_strict(text):
    """
    Detects primary action using strict Malayalam patterns.
    """
    action_patterns = {
        "thinking": ["ചിന്തിക്കുക", "ആലോചിക്കുക"],
        "explaining": ["വിശദീകരിക്കുക", "പറയുക"],
        "working": ["പ്രവർത്തിക്കുക", "ചെയ്യുക"],
        "learning": ["പഠിക്കുക", "മനസ്സിലാക്കുക"]
    }
    
    for action, patterns in action_patterns.items():
        if any(p in text for p in patterns):
            return action
    
    return "neutral"


def _extract_simple_concept(text):
    """
    Extracts simple concept for DALL-E (first meaningful phrase).
    """
    # Remove common fillers
    words = text.replace("ഇവിടെ", "").replace("ആണ്", "").strip()
    # Return first 50 chars
    return words[:50].strip() or "concept"


if __name__ == "__main__":
    # Test decision making
    test_chunk = {
        "text": "ഇവിടെ ആളുകൾ സാധാരണയായി ചെയ്യുന്ന വലിയ പിഴവ് ഇതാണ്",
        "intent": "MISTAKE_WARNING",
        "topic": "programming mistakes",
        "duration": 25.5
    }
    
    decision = make_visual_decision(test_chunk)
    
    print("\n" + "="*60)
    print("VISUAL DECISION")
    print("="*60)
    print(f"Source: {decision['source']}")
    print(f"Intent: {decision['intent']}")
    if 'dalle_prompt' in decision:
        print(f"DALL-E Prompt: {decision['dalle_prompt']}")
    if 'search_query' in decision:
        print(f"Pixabay Query: {decision['search_query']}")
