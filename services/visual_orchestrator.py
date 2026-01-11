"""
Audio-Driven Visual Orchestrator
Coordinates the complete visual generation pipeline based on audio chunks
"""

import logging
from services.visual_intent_classifier import batch_classify_chunks
from services.visual_decision_engine import make_visual_decision
from services.visual_validator import validate_visual_audio_sync
from typing import List, Dict


def generate_visuals_from_audio(audio_chunks, topic=None):
    """
    Main orchestrator: Generates visuals for each audio chunk.
    
    This is THE NEW WAY - chunk-by-chunk, intent-driven.
    
    Process:
    1. Classify intent for each chunk
    2. Make visual decision (Pixabay/DALL-E/Generated)
    3. Generate visuals
    4. Validate alignment
    
    Args:
        audio_chunks: Semantic chunks from audio_transcriber + semantic_chunker
        topic: Optional overall topic for context
    
    Returns:
        List of visual specifications ready for video assembly
    """
    
    logging.info(f"🎬 Generating visuals for {len(audio_chunks)} audio chunks...")
    
    # Step 1: Classify intent
    chunks_with_intent = batch_classify_chunks(audio_chunks)
    
    # Step 2: Make decisions
    visual_decisions = []
    for chunk in chunks_with_intent:
        decision = make_visual_decision(chunk)
        visual_decisions.append(decision)
    
    # Step 3: Generate visuals (delegated to bg_generator or DALL-E)
    visual_specs = []
    for i, decision in enumerate(visual_decisions):
        spec = _generate_single_visual(decision, audio_chunks[i])
        visual_specs.append(spec)
    
    # Step 4: Validate
    validation = validate_visual_audio_sync(visual_specs, audio_chunks)
    
    if not validation["passed"]:
        logging.warning(f"⚠️ Validation issues: {validation['issues']}")
        # Continue anyway, but log warnings
    else:
        logging.info(f"✅ Visual-audio sync validated (score: {validation['score']:.2f})")
    
    return visual_specs


def _generate_single_visual(decision, audio_chunk):
    """
    Generates a single visual based on decision.
    
    Routes to appropriate generator:
    - Pixabay → bg_generator with enhanced search
    - DALL-E → dalle with controlled prompt
    - Generated → motion_graphics_generator
    """
    
    source = decision.get("source")
    
    if source == "pixabay":
        return _generate_pixabay_visual(decision, audio_chunk)
    elif source == "dalle":
        return _generate_dalle_visual(decision, audio_chunk)
    elif source == "generated":
        return _generate_motion_graphic(decision, audio_chunk)
    else:
        logging.warning(f"Unknown source: {source}, using fallback")
        return _generate_fallback_visual(audio_chunk)


def _generate_pixabay_visual(decision, chunk):
    """
    Generates Pixabay visual with semantic search.
    
    Uses enhanced search query from decision engine.
    """
    
    from services.bg_generator import search_pixabay_videos
    
    search_query = decision.get("search_query", "")
    duration = chunk.get("duration", 10)
    
    logging.info(f"   Pixabay search: '{search_query}'")
    
    try:
        # Search with semantic query
        videos = search_pixabay_videos(search_query, min_duration=duration-2, max_duration=duration+2)
        
        if videos:
            return {
                "source": "pixabay",
                "type": "real_footage",
                "url": videos[0]["url"],
                "duration": duration,
                "search_quality": 1.0,
                "intent": decision.get("intent")
            }
        else:
            logging.warning(f"   No Pixabay results for '{search_query}', using fallback")
            return _generate_fallback_visual(chunk)
            
    except Exception as e:
        logging.error(f"Pixabay generation failed: {e}")
        return _generate_fallback_visual(chunk)


def _generate_dalle_visual(decision, chunk):
    """
    Generates DALL-E visual with controlled prompts.
    """
    
    from services.bg_generator import generate_dalle_image
    
    prompt = decision.get("dalle_prompt", "")
    size = decision.get("dalle_size", "1024x1024")
    
    logging.info(f"   DALL-E: '{prompt[:60]}...'")
    
    try:
        image_url = generate_dalle_image(prompt, size=size)
        
        return {
            "source": "dalle",
            "type": "educational",
            "url": image_url,
            "duration": chunk.get("duration", 10),
            "prompt": prompt,
            "intent": decision.get("intent")
        }
        
    except Exception as e:
        logging.error(f"DALL-E generation failed: {e}")
        return _generate_fallback_visual(chunk)


def _generate_motion_graphic(decision, chunk):
    """
    Generates motion graphic with keywords.
    
    Clean fallback for fact statements.
    """
    
    keywords = decision.get("keywords", [])
    duration = chunk.get("duration", 10)
    
    logging.info(f"   Motion graphic: {keywords}")
    
    return {
        "source": "generated",
        "type": "motion_graphics",
        "keywords": keywords,
        "duration": duration,
        "style": decision.get("style", "minimal"),
        "animation": decision.get("animation", "subtle"),
        "intent": decision.get("intent")
    }


def _generate_fallback_visual(chunk):
    """
    Safe fallback when all else fails.
    
    Creates minimal motion graphic instead of using wrong footage.
    """
    
    text = chunk.get("text", "")
    duration = chunk.get("duration", 10)
    
    # Extract key words from Malayalam text
    words = text.split()[:5]
    
    logging.info(f"   Using fallback motion graphic")
    
    return {
        "source": "generated",
        "type": "motion_graphics",
        "keywords": words,
        "duration": duration,
        "style": "gradient_minimal",
        "is_fallback": True,
        "intent": chunk.get("intent", "fact_statement")
    }


if __name__ == "__main__":
    # Test orchestrator
    test_audio_chunks = [
        {
            "text": "ഇവിടെ ആളുകൾ സാധാരണയായി ചെയ്യുന്ന വലിയ പിഴവ് ഇതാണ്",
            "start": 10.0,
            "end": 35.0,
            "duration": 25.0,
            "topic": "programming mistakes"
        },
        {
            "text": "സോഫ്റ്റ്‌വെയർ എഞ്ചിനീയറിംഗ് പ്രോസസ് എങ്ങനെ പ്രവർത്തിക്കുന്നു",
            "start": 35.0,
            "end": 60.0,
            "duration": 25.0,
            "topic": "software engineering"
        }
    ]
    
    visuals = generate_visuals_from_audio(test_audio_chunks, topic="Malayalam Tech")
    
    print("\n" + "="*60)
    print("GENERATED VISUALS")
    print("="*60)
    for i, visual in enumerate(visuals):
        print(f"\n{i+1}. Source: {visual['source']} | Type: {visual['type']}")
        print(f"   Duration: {visual['duration']}s | Intent: {visual.get('intent', 'N/A')}")
        if 'url' in visual:
            print(f"   URL: {visual['url'][:50]}...")
        if 'keywords' in visual:
            print(f"   Keywords: {visual['keywords']}")
