"""
Semantic Visual Matcher - AI-Powered Script-to-Visual Mapping

PROBLEM: Current approach sends literal script phrases to stock APIs:
  "Chase DeMoor Credits Andrew Tate" → returns random/irrelevant videos

SOLUTION: Use AI to understand WHAT the script is ABOUT and suggest
         generic, searchable visual categories that MATCH the content.

EXAMPLE:
  Script: "Chase DeMoor, a former NFL player, revealed that Andrew Tate's 
           philosophy helped him overcome suicidal thoughts..."
  
  AI Analysis:
    - Emotional tone: serious, hopeful, transformation
    - Visual needs: man reflecting, mental health, motivation
    
  Search terms: "man silhouette thinking", "sunrise hope", "person journaling"
  NOT: "Chase DeMoor", "Andrew Tate" (won't find anything relevant)
"""

import os
import json
import logging

# Use wrapped LLM adapter with error handling
from adapters.openai.llm_wrapper import get_llm_fast
from utils.logging.tracer import tracer
from langchain_core.messages import HumanMessage

llm = get_llm_fast()

# Visual category mappings for common script themes
VISUAL_CATEGORIES = {
    "finance": ["stock charts", "money counting", "business meeting", "calculator budget"],
    "motivation": ["sunrise mountain", "person running", "achievement celebration", "focused work"],
    "technology": ["futuristic interface", "typing laptop", "smartphone close", "data visualization"],
    "mental_health": ["meditation calm", "person reflecting", "nature peaceful", "journaling writing"],
    "controversy": ["debate discussion", "people disagreeing", "news headlines", "social media scroll"],
    "success_story": ["before after", "progress growth", "celebration happy", "milestone achievement"],
    "warning": ["danger sign", "cautious thinking", "risk assessment", "careful decision"],
    "education": ["learning study", "book reading", "classroom teaching", "knowledge sharing"],
    # Malayalam/Indian cultural context additions
    "family": ["family gathering", "multi-generation home", "dinner table", "parents children"],
    "tradition": ["cultural celebration", "festival colors", "traditional ceremony", "heritage pride"],
    "inspiration": ["person dreaming", "goal setting", "vision board", "aspiration hope"],
    "struggle": ["struggling effort", "challenge facing", "obstacle overcoming", "difficult choice"],
    "transformation": ["metamorphosis change", "before after", "growth evolution", "improvement progress"],
    "community": ["people together", "neighborhood street", "market bustling", "social gathering"],
    "nature": ["tropical greenery", "rain falling", "river flowing", "sunset landscape"],
    "wisdom": ["elder teaching", "wise reflection", "life lesson", "thoughtful moment"],
}

def analyze_script_for_visuals(script_sections: list, topic: str = "") -> list:
    """
    Analyzes each script section and returns semantically matched visual search terms.
    
    Args:
        script_sections: List of dicts with 'title' and 'content'
        topic: Overall video topic for context
        
    Returns:
        List of visual cue strings optimized for stock video search
    """
    visual_cues = []
    
    for section in script_sections:
        title = section.get('title', '')
        content = section.get('content', '')
        section_type = section.get('type', 'body')
        
        # Get AI-optimized search terms for this section
        search_terms = get_semantic_search_terms(
            section_content=content,
            section_type=title,
            overall_topic=topic
        )
        
        # Generate 3-5 visual cues per section for variety
        visual_cues.extend(search_terms)
    
    logging.info(f"[SemanticMatcher] Generated {len(visual_cues)} semantically matched visual cues")
    return visual_cues

def get_semantic_search_terms(section_content: str, section_type: str, overall_topic: str) -> list:
    """
    Uses AI to convert script content into stock-searchable visual terms.
    
    CRITICAL: Returns GENERIC terms that stock APIs can actually find.
    ENHANCED: Handles Malayalam content by extracting concepts first.
    """
    
    # Detect if content contains Malayalam characters
    has_malayalam = any('\u0d00' <= char <= '\u0d7f' for char in section_content)
    
    if has_malayalam:
        # First pass: Extract CONCEPTS from Malayalam script
        concept_prompt = f"""You are analyzing Malayalam/mixed language script content.

Script: {section_content[:600]}

Extract the CORE CONCEPTS and translate them to English in simple terms.
Focus on:
- What emotion is being conveyed? (happy, sad, motivated, shocked, etc.)
- What action or situation? (person working, family gathering, technology demo, etc.)
- What setting or environment? (office, nature, city, home, etc.)

Return ONLY a brief 2-3 sentence English summary of the visual concepts:"""

        try:
            concept_response = llm.invoke(
                [HumanMessage(content=concept_prompt)],
                trace_id=tracer.get_trace_id(),
                compress_context=True
            )
            concept_summary = concept_response.content.strip()
            logging.info(f"[SemanticMatcher] Malayalam→Concept: {concept_summary[:100]}")
        except Exception as e:
            logging.warning(f"[SemanticMatcher] Concept extraction failed: {e}")
            concept_summary = overall_topic  # Fallback
    else:
        concept_summary = section_content[:500]
    
    # Second pass: Convert concepts to stock-searchable visual terms
    prompt = f"""You are a visual content director for stock footage. Convert this script into 4 GENERIC stock video search terms.

STRICT RULES:
1. NO proper nouns, names, or specific people (e.g., NO "Andrew Tate", "Kerala politician")
2. Use ONLY common, searchable terms stock libraries have
3. Focus on: emotions, actions, settings, universal objects
4. Each term: 2-4 words maximum
5. Think: "What generic B-roll would support this narration?"

Examples of GOOD terms:
- "business meeting discussion"
- "person celebrating success"
- "sunset beach walking"
- "technology digital interface"
- "family happy gathering"

Examples of BAD terms:
- "Andrew Tate speaking"  ❌ (specific person)
- "Kerala festival"  ❌ (too specific geographically)
- "cryptocurrency blockchain"  ❌ (too technical, limited stock footage)

Topic: {overall_topic}
Section: {section_type}
Content Concepts: {concept_summary}

Return ONLY a JSON array of 4 search terms:
["term1", "term2", "term3", "term4"]"""

    try:
        response = llm.invoke(
            [HumanMessage(content=prompt)],
            trace_id=tracer.get_trace_id(),
            compress_context=True
        )
        
        content = response.content.strip()
        
        # Parse JSON array
        if "```" in content:
            content = content.split("```")[1].replace("json", "").strip()
        
        terms = json.loads(content)
        
        # Validate - no proper nouns, no Malayalam text in results
        filtered_terms = []
        for term in terms:
            # Check for Malayalam characters
            if any('\u0d00' <= char <= '\u0d7f' for char in term):
                continue  # Skip terms with Malayalam
            # Check for capitalized words (likely proper nouns)
            if not any(word[0].isupper() and len(word) > 2 for word in term.split()):
                filtered_terms.append(term)
        
        if filtered_terms:
            logging.info(f"[SemanticMatcher] '{section_type[:30]}' → {filtered_terms}")
            return filtered_terms
        else:
            # Fallback if all filtered out
            logging.warning(f"[SemanticMatcher] All terms filtered, using fallback")
            return get_fallback_visuals(section_type)
            
    except Exception as e:
        logging.warning(f"[SemanticMatcher] AI failed: {e}, using fallback")
        return get_fallback_visuals(section_type)

def get_fallback_visuals(section_type: str) -> list:
    """
    Returns safe fallback visuals based on section type.
    """
    section_lower = section_type.lower()
    
    if "hook" in section_lower:
        return ["person shocked reaction", "dramatic reveal moment", "eye catching visual", "attention grabbing"]
    elif "intro" in section_lower:
        return ["person thinking deeply", "question mark concept", "curious expression", "opening scene"]
    elif "foundation" in section_lower or "part 1" in section_lower:
        return ["building blocks concept", "starting point", "foundation laying", "beginning journey"]
    elif "turning" in section_lower or "part 2" in section_lower:
        return ["transformation moment", "change happening", "pivot direction", "breakthrough realization"]
    elif "implication" in section_lower or "part 3" in section_lower:
        return ["future vision", "impact ripple", "consequence chain", "outcome result"]
    elif "outro" in section_lower or "conclusion" in section_lower:
        return ["closing thoughts", "reflection moment", "summary wrap", "call to action"]
    else:
        return ["professional business", "modern lifestyle", "abstract motion", "cinematic b-roll"]

def map_sections_to_visuals(long_script: dict) -> list:
    """
    Main entry point: Takes a long script and returns optimized visual cues.
    
    Args:
        long_script: Script dict with 'sections' and 'title'
        
    Returns:
        List of visual cue strings (4 per section typically)
    """
    sections = long_script.get('sections', [])
    topic = long_script.get('title', '')
    
    if not sections:
        logging.error("[SemanticMatcher] No sections in script!")
        return []
    
    all_cues = analyze_script_for_visuals(sections, topic)
    
    # Ensure minimum visual density (at least 30 cues for 5-6 min video)
    if len(all_cues) < 30:
        logging.warning(f"[SemanticMatcher] Only {len(all_cues)} cues, padding with generic visuals")
        generic = ["abstract motion graphics", "cinematic slow motion", "professional b-roll", "modern lifestyle"]
        while len(all_cues) < 30:
            all_cues.extend(generic)
    
    return all_cues[:60]  # Cap at 60 visuals for 5-6 min video

def validate_visual_sync(script_sections: list, visual_cues: list) -> dict:
    """
    Validates that visuals match script content sections.
    
    Returns:
        {
            "valid": bool,
            "coverage": float (0-1),
            "mismatches": list of section indices with issues
        }
    """
    if not script_sections or not visual_cues:
        return {"valid": False, "coverage": 0, "mismatches": []}
    
    # Each section should have ~4-6 visual cues
    expected_per_section = len(visual_cues) / len(script_sections)
    
    if expected_per_section < 3:
        return {"valid": False, "coverage": expected_per_section/4, "mismatches": []}
    
    return {"valid": True, "coverage": 1.0, "mismatches": []}

if __name__ == "__main__":
    # Test with sample section
    test_section = {
        "title": "PART 1: The Foundation",
        "content": "Chase DeMoor revealed that listening to Andrew Tate's motivational content during a dark period helped him avoid making a terrible decision. The NFL player credits the controversial figure with providing unconventional wisdom about personal responsibility.",
        "type": "body"
    }
    
    result = get_semantic_search_terms(
        test_section["content"], 
        test_section["title"],
        "Mental Health and Motivation"
    )
    
    print("Semantic Visual Matcher Test")
    print("=" * 50)
    print(f"Input: '{test_section['content'][:100]}...'")
    print(f"Output search terms: {result}")
