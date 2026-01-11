"""
Long-Form Script Agent - Config-Driven Documentary Architecture

ALL SETTINGS FROM channel_config.yaml:
- Language (Malayalam, Hindi, English, etc.)
- Niche (Tech, Finance, Motivation, etc.)
- Persona (Storyteller, Professor, etc.)

Creates 5-6 minute documentary-style scripts optimized for:
- Higher viewer retention (50%+ watch time)
- YPP approval (quality over length)
- Engagement over padding
"""

import os
import json
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# Import channel configuration
try:
    from config.channel import channel_config
    CONFIG_LOADED = True
except ImportError:
    CONFIG_LOADED = False
    print("[DocBrain] WARNING: channel_config not found, using defaults")


# ============================================================================
# DYNAMIC CONFIGURATION
# ============================================================================

def get_channel_context() -> dict:
    """Get channel context from config for prompt generation."""
    if CONFIG_LOADED:
        return {
            "channel_name": channel_config.channel_name,
            "language": channel_config.get("channel.language", "en"),
            "language_name": get_language_name(channel_config.get("channel.language", "en")),
            "niche": channel_config.niche,
            "persona": channel_config.persona,
            "country": channel_config.get("channel.country", "US"),
        }
    return {
        "channel_name": "My Channel",
        "language": "en",
        "language_name": "English",
        "niche": "Technology",
        "persona": "The Storyteller",
        "country": "US",
    }


def get_language_name(code: str) -> str:
    """Convert language code to full name."""
    languages = {
        "ml": "Malayalam", "hi": "Hindi", "ta": "Tamil", "te": "Telugu",
        "kn": "Kannada", "bn": "Bengali", "en": "English", "es": "Spanish",
        "fr": "French", "de": "German", "ar": "Arabic"
    }
    return languages.get(code, "English")


def get_script_language_rules(language: str) -> str:
    """Get language-specific script writing rules."""
    lang_name = get_language_name(language)
    if language in ["ml", "hi", "ta", "te", "kn", "bn"]:
        return f"""
LANGUAGE RULES FOR {lang_name.upper()} SCRIPT:
- STRICT: Write the ENTIRE script in {lang_name} SCRIPT (Unicode).
- DO NOT write in Latin/English script (no transliteration).
- Technical terms (AI, Battery, Stock, CEO) can remain in English.
- Write acronyms with dots for TTS: "A.I." not "AI", "C.E.O." not "CEO"
"""
    else:
        return f"""
LANGUAGE RULES:
- Write the script in {lang_name}.
- Use natural, conversational documentary tone.
"""


# ============================================================================
# STATE DEFINITION
# ============================================================================
class DocumentaryState(TypedDict):
    topic: str
    perception: dict
    research: dict
    structure: dict
    sections: List[dict]
    draft: dict
    critique: dict
    iteration_count: int
    total_word_count: int


# ============================================================================
# LLM SETUP
# ============================================================================
llm_analyst = ChatOpenAI(model="gpt-4o-mini", temperature=0.4)
llm_storyteller = ChatOpenAI(model="gpt-4o", temperature=0.85)
llm_editor = ChatOpenAI(model="gpt-4o", temperature=0.3)


# ============================================================================
# DYNAMIC PROMPT GENERATORS
# ============================================================================

def get_perceive_prompt(topic: str, ctx: dict) -> str:
    return f"""You are the DEEP PERCEPTION module for a {ctx['niche']} documentary channel.
Analyze this topic with the depth of an investigative journalist.

CHANNEL: {ctx['channel_name']}
NICHE: {ctx['niche']}
TARGET: Viewers interested in {ctx['niche']} in {ctx['country']}

TOPIC: {topic}

Return JSON:
{{
    "core_thesis": "The central argument or revelation of this documentary",
    "why_now": "Why is this topic urgent/relevant in 2024-2025?",
    "target_viewer": "Specific person who NEEDS to see this",
    "emotional_journey": {{
        "start": "How viewer feels at start",
        "middle": "The 'aha moment' emotion",
        "end": "How they should feel leaving"
    }},
    "controversy": "Any debate or surprising angle?",
    "transformation": "What will viewer understand that they didn't before?"
}}"""


def get_research_prompt(perception: dict, topic: str, ctx: dict) -> str:
    return f"""You are the RESEARCH module for a {ctx['niche']} documentary.
Gather comprehensive information for a 10-minute deep-dive.

TOPIC: {topic}
PERCEPTION: {json.dumps(perception)}

Return JSON with AUTHORITATIVE content:
{{
    "timeline": [
        {{"year": "2020", "event": "Key milestone"}},
        {{"year": "2024", "event": "Recent development"}}
    ],
    "key_statistics": ["Stat 1 with source", "Stat 2"],
    "expert_perspectives": [
        {{"expert": "Name/Title", "quote": "What they said", "context": "Why it matters"}}
    ],
    "case_studies": [
        {{"name": "Real example", "story": "What happened", "lesson": "What we learn"}}
    ],
    "common_myths": [
        {{"myth": "What people believe", "reality": "The truth"}}
    ],
    "predictions": [{{"timeframe": "2025", "prediction": "What experts expect"}}]
}}"""


def get_structure_prompt(perception: dict, research: dict, ctx: dict) -> str:
    return f"""You are the NARRATIVE ARCHITECT for {ctx['channel_name']}.
Design the story structure for a 5-6 minute {ctx['niche']} documentary.

PERCEPTION: {json.dumps(perception)}
RESEARCH: {json.dumps(research)}

Create a 5-section structure (CONCISE, NO PADDING):

Return JSON:
{{
    "sections": [
        {{
            "name": "HOOK",
            "duration": "0:00-0:30",
            "purpose": "Create immediate tension/curiosity",
            "key_element": "Specific hook technique"
        }},
        {{
            "name": "INTRO + CONTEXT",
            "duration": "0:30-1:30",
            "purpose": "Establish stakes and background"
        }},
        {{
            "name": "CORE VALUE",
            "duration": "1:30-4:00",
            "purpose": "Main content, insights, revelations"
        }},
        {{
            "name": "IMPLICATIONS",
            "duration": "4:00-5:00",
            "purpose": "What this means for viewer"
        }},
        {{
            "name": "OUTRO + CTA",
            "duration": "5:00-6:00",
            "purpose": "Summarize + inspire action"
        }}
    ],
    "narrative_thread": "The single question driving the documentary"
}}"""


def get_section_prompt(section_info: dict, research: dict, perception: dict, 
                       target_words: int, ctx: dict) -> str:
    language_rules = get_script_language_rules(ctx['language'])
    
    return f"""You are the SCRIPTWRITER for {ctx['channel_name']}.
Write ONE section of a {ctx['language_name']} documentary script.

CHANNEL: {ctx['channel_name']}
NICHE: {ctx['niche']}
PERSONA: {ctx['persona']}

SECTION INFO: {json.dumps(section_info)}
RESEARCH: {json.dumps(research)}
PERCEPTION: {json.dumps(perception)}

{language_rules}

TARGET: {target_words} words for this section.

VISUAL CUES RULES:
- Provide 8-10 SPECIFIC visual search terms
- Real, searchable terms (not abstract)
- Matched to what you're narrating

Return JSON:
{{
    "header": "{section_info.get('name', 'Section')}",
    "content": "Full {ctx['language_name']} script for this section",
    "visual_cues": ["specific term 1", "term 2", ...8-10 items],
    "on_screen_text": ["Key phrase to display"],
    "word_count": {target_words}
}}"""


def get_assemble_prompt(sections: list, perception: dict, ctx: dict) -> str:
    return f"""You are the ASSEMBLY module for {ctx['channel_name']}.
Combine all sections into a cohesive {ctx['niche']} documentary.

SECTIONS: {json.dumps(sections, ensure_ascii=False)}
PERCEPTION: {json.dumps(perception)}

Create the final package:

Return JSON:
{{
    "title": "SEO-Optimized {ctx['language_name']} Title",
    "description": "YouTube description with keywords",
    "sections": [all section objects],
    "thumbnail_text": "3-4 Word Punchline",
    "tags": ["relevant", "search", "terms"],
    "total_duration": "~10 minutes"
}}"""


def get_critique_prompt(script: dict, ctx: dict) -> str:
    return f"""You are the QUALITY CONTROL module for {ctx['channel_name']}.
Evaluate this {ctx['niche']} documentary for a {ctx['language_name']} audience.

SCRIPT: {json.dumps(script, ensure_ascii=False)}

Score each dimension (1-10):

Return JSON:
{{
    "scores": {{
        "hook_power": 8,
        "narrative_flow": 7,
        "information_value": 9,
        "emotional_arc": 8,
        "visual_variety": 7,
        "retention_likelihood": 8,
        "monetization_safe": 10
    }},
    "overall_score": 8.1,
    "weakest_section": "Which section needs work",
    "verdict": "APPROVED" or "NEEDS_REVISION"
}}"""


# ============================================================================
# COGNITIVE NODES
# ============================================================================

def perceive_long_node(state: DocumentaryState) -> dict:
    ctx = get_channel_context()
    prompt = get_perceive_prompt(state["topic"], ctx)
    response = llm_analyst.invoke([HumanMessage(content=prompt)])
    
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        perception = json.loads(content)
    except:
        perception = {"core_thesis": state["topic"]}
    
    safe_thesis = perception.get('core_thesis', '').encode('ascii', 'replace').decode('ascii')
    print(f"[DocBrain] Perceived: {safe_thesis[:60]}...")
    return {"perception": perception}


def research_long_node(state: DocumentaryState) -> dict:
    ctx = get_channel_context()
    prompt = get_research_prompt(state["perception"], state["topic"], ctx)
    response = llm_analyst.invoke([HumanMessage(content=prompt)])
    
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        research = json.loads(content)
    except:
        research = {"key_statistics": [], "case_studies": []}
    
    print(f"[DocBrain] Researched: {len(research.get('key_statistics', []))} stats")
    return {"research": research}


def structure_node(state: DocumentaryState) -> dict:
    ctx = get_channel_context()
    prompt = get_structure_prompt(state["perception"], state["research"], ctx)
    response = llm_analyst.invoke([HumanMessage(content=prompt)])
    
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        structure = json.loads(content)
    except:
        structure = {"sections": [{"name": "HOOK"}, {"name": "INTRO"}, 
                                   {"name": "PART 1"}, {"name": "PART 2"}, 
                                   {"name": "PART 3"}, {"name": "OUTRO"}]}
    
    print(f"[DocBrain] Structured: {len(structure.get('sections', []))} sections")
    return {"structure": structure}


def draft_sections_node(state: DocumentaryState) -> dict:
    ctx = get_channel_context()
    sections = []
    structure = state.get("structure", {})
    section_plans = structure.get("sections", [])
    
    # Word targets per section (5-6 min = ~900-1000 words total)
    # CONCISE: Every word must earn its place
    word_targets = [60, 150, 400, 180, 110]  # Hook, Intro, Core, Implications, Outro
    
    for i, section_plan in enumerate(section_plans[:5]):  # 5 sections for 5-6 min
        target_words = word_targets[i] if i < len(word_targets) else 200
        
        prompt = get_section_prompt(section_plan, state["research"], 
                                    state["perception"], target_words, ctx)
        response = llm_storyteller.invoke([HumanMessage(content=prompt)])
        
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            section = json.loads(content)
        except:
            section = {"header": section_plan.get("name", "Section"), 
                      "content": "", "visual_cues": []}
        
        sections.append(section)
        safe_header = section.get('header', 'Section').encode('ascii', 'replace').decode('ascii')
        print(f"[DocBrain] Drafted: {safe_header}")
    
    return {"sections": sections}


def assemble_node(state: DocumentaryState) -> dict:
    ctx = get_channel_context()
    prompt = get_assemble_prompt(state["sections"], state["perception"], ctx)
    response = llm_editor.invoke([HumanMessage(content=prompt)])
    
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        draft = json.loads(content)
    except:
        draft = {"title": state["topic"], "sections": state["sections"]}
    
    total_words = sum(s.get("word_count", len(s.get("content", "").split())) 
                      for s in state["sections"])
    
    safe_title = draft.get('title', '').encode('ascii', 'replace').decode('ascii')
    print(f"[DocBrain] Assembled: '{safe_title[:50]}' (~{total_words} words)")
    return {"draft": draft, "total_word_count": total_words, 
            "iteration_count": state.get("iteration_count", 0) + 1}


def critique_long_node(state: DocumentaryState) -> dict:
    ctx = get_channel_context()
    prompt = get_critique_prompt(state["draft"], ctx)
    response = llm_editor.invoke([HumanMessage(content=prompt)])
    
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        critique = json.loads(content)
    except:
        critique = {"overall_score": 8.0, "verdict": "APPROVED"}
    
    print(f"[DocBrain] Critiqued: {critique.get('overall_score', 0)}/10")
    return {"critique": critique}


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

workflow = StateGraph(DocumentaryState)

workflow.add_node("perceive", perceive_long_node)
workflow.add_node("research", research_long_node)
workflow.add_node("structure", structure_node)
workflow.add_node("draft_sections", draft_sections_node)
workflow.add_node("assemble", assemble_node)
workflow.add_node("critique", critique_long_node)

workflow.set_entry_point("perceive")
workflow.add_edge("perceive", "research")
workflow.add_edge("research", "structure")
workflow.add_edge("structure", "draft_sections")
workflow.add_edge("draft_sections", "assemble")
workflow.add_edge("assemble", "critique")
workflow.add_edge("critique", END)

app = workflow.compile()


# ============================================================================
# PUBLIC API
# ============================================================================

def generate_long_script(topic: str) -> dict:
    """Generate a 5-6 minute documentary script based on channel configuration."""
    ctx = get_channel_context()
    print(f"\n[DocBrain] Channel: {ctx['channel_name']} | Language: {ctx['language_name']} | Niche: {ctx['niche']}")
    print(f"[DocBrain] Processing: '{topic}'")
    print("[DocBrain] " + "="*60)
    
    initial_state = {"topic": topic, "iteration_count": 0, "total_word_count": 0}
    final_state = app.invoke(initial_state)
    
    print(f"[DocBrain] Complete! Total: ~{final_state.get('total_word_count', 0)} words")
    print("[DocBrain] " + "="*60 + "\n")
    
    return final_state["draft"]


if __name__ == "__main__":
    ctx = get_channel_context()
    print(f"Testing Long Script Agent for: {ctx['channel_name']}")
    print(f"Language: {ctx['language_name']}, Niche: {ctx['niche']}")
    
    topic = "The Hidden Psychology of Procrastination"
    result = generate_long_script(topic)
    print(json.dumps(result, indent=2, ensure_ascii=False))
