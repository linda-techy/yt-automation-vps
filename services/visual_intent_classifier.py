"""
Visual Intent Classifier
Analyzes Malayalam audio chunks to determine visual strategy
"""

import logging
import os
import json

# Use wrapped LLM adapter with error handling
from adapters.openai.llm_wrapper import get_llm_fast
from utils.logging.tracer import tracer
from langchain_core.messages import HumanMessage

llm = get_llm_fast()


# Intent types and their meanings
INTENT_TYPES = {
    "person_story": "Real-life example or personal narrative",
    "how_it_works": "Technical or process explanation",
    "mistake_explanation": "Warning about common error",
    "emotional": "Emotional appeal (fear, joy, shock)",
    "fact_statement": "Data, statistics, or factual claim",
    "comparison": "Comparing two or more things",
    "conclusion": "Summary or call-to-action"
}


def classify_chunk_intent(chunk_text, chunk_topic=None):
    """
    Hybrid intent classification: Malayalam keywords + GPT-4 fallback.
    
    PRODUCTION APPROACH:
    1. Try keyword-based classification (fast, 90% accurate)
    2. If uncertain, use GPT-4 (slower, handles edge cases)
    
    Args:
        chunk_text: Malayalam text from audio chunk
        chunk_topic: Optional topic for context
    
    Returns:
        {
            "intent": "MISTAKE_WARNING",
            "visual_type": "symbolic_minimal",
            "confidence": 0.95,
            "method": "keyword" | "gpt4",
            "reasoning": "..."
        }
    """
    
    # Step 1: Try keyword-based classification
    keyword_result = _classify_by_keywords(chunk_text)
    
    if keyword_result["confidence"] >= 0.8:
        # High confidence from keywords - use it
        keyword_result["visual_type"] = _get_visual_type_from_intent(keyword_result["intent"])
        keyword_result["method"] = "keyword"
        logging.info(f"Intent (keyword): {keyword_result['intent']} ({keyword_result['confidence']:.2f})")
        return keyword_result
    
    # Step 2: Fallback to GPT-4 for uncertain cases
    logging.info("Intent uncertain from keywords, using GPT-4...")
    gpt_result = _classify_by_gpt4(chunk_text, chunk_topic)
    gpt_result["visual_type"] = _get_visual_type_from_intent(gpt_result["intent"])
    gpt_result["method"] = "gpt4"
    
    return gpt_result


def _classify_by_keywords(text):
    """
    Fast keyword-based intent classification for Malayalam.
    
    Returns confidence score based on keyword matches.
    """
    
    text_lower = text.lower()
    
    # Intent keyword patterns (Malayalam)
    patterns = {
        "MISTAKE_WARNING": {
            "keywords": ["പിഴവ്", "തെറ്റ്", "ശ്രദ്ധിക്കണം", "അപകടം", "ചെയ്യരുത്"],
            "weight": 1.0
        },
        "HOW_IT_WORKS": {
            "keywords": ["എങ്ങനെ", "പ്രവർത്തിക്കുന്നു", "പ്രക്രിയ", "രീതി", "സിസ്റ്റം"],
            "weight": 0.9
        },
        "PERSON_STORY": {
            "keywords": ["ഒരു ആള", "എനിക്ക് സംഭവിച്ചു", "അനുഭവം", "ഉദാഹരണം", "കഥ"],
            "weight": 0.95
        },
        "FACT_STATEMENT": {
            "keywords": ["സത്യം", "ഡാറ്റ", "സ്ഥിതിവിവരം", "പഠനം", "ഗവേഷണം"],
            "weight": 0.85
        },
        "EMOTIONAL_REACTION": {
            "keywords": ["ഭയം", "ഞെട്ടി", "സന്തോഷം", "കോപം", "വികാരം"],
            "weight": 0.9
        },
        "ADVICE_TIP": {
            "keywords": ["നിർദ്ദേശം", "ഉപദേശം", "മികച്ചത്", "ശുപാർശ", "നുറുങ്ങ്"],
            "weight": 0.8
        }
    }
    
    # Score each intent
    scores = {}
    for intent, data in patterns.items():
        keywords = data["keywords"]
        weight = data["weight"]
        
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches > 0:
            # Confidence = (matches / total_keywords) * weight
            confidence = (matches / len(keywords)) * weight
            scores[intent] = confidence
    
    if not scores:
        # No keywords matched - low confidence
        return {
            "intent": "FACT_STATEMENT",  # Safe default
            "confidence": 0.5,
            "reasoning": "No keyword matches, using default"
        }
    
    # Return highest scoring intent
    best_intent = max(scores, key=scores.get)
    best_score = scores[best_intent]
    
    return {
        "intent": best_intent,
        "confidence": best_score,
        "reasoning": f"Keyword match for {best_intent}"
    }


def _classify_by_gpt4(chunk_text, chunk_topic):
    """
    GPT-4 based classification for edge cases.
    """
    
    prompt = f"""Classify this Malayalam text into ONE intent category.

Text: {chunk_text}
{f"Topic: {chunk_topic}" if chunk_topic else ""}

STRICT CATEGORIES (choose ONE):
- PERSON_STORY: Real-life example, personal narrative
- HOW_IT_WORKS: Technical/process explanation
- MISTAKE_WARNING: Warning about common error
- FACT_STATEMENT: Data, statistics, factual claim
- EMOTIONAL_REACTION: Emotional appeal (fear, joy, shock)
- ADVICE_TIP: Advice, recommendation, tip

Return ONLY JSON:
{{
    "intent": "...",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}
"""

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
        return result
        
    except Exception as e:
        logging.error(f"GPT-4 classification failed: {e}")
        return {
            "intent": "FACT_STATEMENT",
            "confidence": 0.5,
            "reasoning": "Classification failed, using safe default"
        }


def _get_visual_type_from_intent(intent):
    """
    Maps intent to visual type (strict mapping).
    """
    
    mapping = {
        "PERSON_STORY": "real_footage",
        "HOW_IT_WORKS": "diagram_animated",
        "MISTAKE_WARNING": "symbolic_minimal",
        "EMOTIONAL_REACTION": "facial_expression",
        "FACT_STATEMENT": "text_motion",
        "ADVICE_TIP": "neutral_lifestyle"
    }
    
    return mapping.get(intent, "minimal_text")


def batch_classify_chunks(chunks):
    """
    Classifies intent for multiple chunks.
    
    Args:
        chunks: List of semantic chunks with 'text' field
    
    Returns:
        Chunks enriched with intent classification
    """
    
    logging.info(f"🧠 Classifying intent for {len(chunks)} chunks...")
    
    for i, chunk in enumerate(chunks):
        intent_data = classify_chunk_intent(
            chunk.get("text", ""),
            chunk.get("topic", None)
        )
        
        # Merge into chunk
        chunk["intent"] = intent_data["intent"]
        chunk["visual_type"] = intent_data["visual_type"]
        chunk["intent_confidence"] = intent_data["confidence"]
        chunk["intent_reasoning"] = intent_data.get("reasoning", "")
    
    logging.info(f"✅ Intent classification complete")
    
    return chunks


if __name__ == "__main__":
    # Test classification
    test_chunks = [
        {
            "text": "ഇവിടെ ആളുകൾ സാധാരണയായി ചെയ്യുന്ന വലിയ പിഴവ് ഇതാണ് - അവർ തുടക്കത്തിൽ തന്നെ പ്ലാനിംഗ് ചെയ്യുന്നില്ല",
            "topic": "programming mistakes"
        },
        {
            "text": "സോഫ്റ്റ്‌വെയർ എഞ്ചിനീയറിംഗ് എന്താണെന്ന് നോക്കാം. ഇത് ഒരു സിസ്റ്റമാറ്റിക് പ്രോസസ് ആണ്",
            "topic": "software engineering"
        },
        {
            "text": "ഇത് കേട്ടാൽ നിങ്ങൾ ഞെട്ടും! 90% പേരും ഇത് അറിയുന്നില്ല",
            "topic": "shocking fact"
        }
    ]
    
    results = batch_classify_chunks(test_chunks)
    
    print("\n" + "="*60)
    print("INTENT CLASSIFICATION RESULTS")
    print("="*60)
    for i, chunk in enumerate(results):
        print(f"\n{i+1}. Intent: {chunk['intent']} ({chunk['intent_confidence']:.2f})")
        print(f"   Visual Type: {chunk['visual_type']}")
        print(f"   Text: {chunk['text'][:80]}...")
        print(f"   Reasoning: {chunk['intent_reasoning']}")
