"""
Advanced Script Agent - Config-Driven Brain-Like Architecture

This module implements a multi-stage thinking process that:
1. Reads channel configuration (language, niche, persona)
2. Dynamically generates prompts based on config
3. Produces scripts matching the configured channel identity

ALL SETTINGS ARE DYNAMIC FROM channel_config.yaml:
- Language (Malayalam, Hindi, English, etc.)
- Niche (Tech, Motivation, Finance, etc.)
- Persona (Storyteller, Professor, Hype Beast, etc.)
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
    print("[ScriptAgent] WARNING: channel_config not found, using defaults")
    
from services.feedback_loop import get_feedback_adjustments


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
            "topic_keywords": channel_config.topic_keywords,
            "feedback_tuning": get_feedback_adjustments() # Dynamic tuning from analytics
        }
    return {
        "channel_name": "My Channel",
        "language": "en",
        "language_name": "English",
        "niche": "Technology",
        "persona": "The Storyteller",
        "country": "US",
        "topic_keywords": ["Technology"],
    }


def get_language_name(code: str) -> str:
    """Convert language code to full name."""
    languages = {
        "ml": "Malayalam",
        "hi": "Hindi",
        "ta": "Tamil",
        "te": "Telugu",
        "kn": "Kannada",
        "bn": "Bengali",
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
        "ar": "Arabic"
    }
    return languages.get(code, "English")


def get_script_language_rules(language: str) -> str:
    """Get language-specific script writing rules."""
    if language in ["ml", "hi", "ta", "te", "kn", "bn"]:  # Indic languages
        return f"""
LANGUAGE RULES FOR {get_language_name(language).upper()} SCRIPT:
- STRICT: Write the ENTIRE script in {get_language_name(language)} SCRIPT (Unicode).
- DO NOT write in Latin/English script (no transliteration).
- Technical terms (AI, Battery, Stock) can remain in English.
- Write acronyms with dots for TTS: "A.I." not "AI"
- Example format: Unicode script with embedded English keywords.

WRONG: "AI nte future nammal chinthikkunnathinekkal..." (Romanized - WRONG)
CORRECT: Full {get_language_name(language)} Unicode script with English tech terms only.
"""
    else:
        return f"""
LANGUAGE RULES:
- Write the script in {get_language_name(language)}.
- Use natural, conversational tone.
- Technical terms should be explained simply.
"""


# ============================================================================
# STATE DEFINITION
# ============================================================================
class CognitiveState(TypedDict):
    topic: str
    perception: dict
    research: dict
    ideas: List[dict]
    draft: dict
    critique: str
    iteration_count: int
    confidence_score: float
    quality_flags: List[str]


# ============================================================================
# LLM SETUP
# ============================================================================
llm_fast = ChatOpenAI(model="gpt-4o-mini", temperature=0.5)
llm_creative = ChatOpenAI(model="gpt-4o", temperature=0.8)
llm_precise = ChatOpenAI(model="gpt-4o", temperature=0.3)


# ============================================================================
# DYNAMIC PROMPT GENERATORS
# ============================================================================

def get_perceive_prompt(topic: str, ctx: dict) -> str:
    return f"""You are the PERCEPTION module of a content brain for a {ctx['niche']} YouTube channel.
Your job: Deeply understand what this topic means and why people care.

CHANNEL: {ctx['channel_name']}
NICHE: {ctx['niche']}
TARGET AUDIENCE: Viewers interested in {ctx['niche']} in {ctx['country']}

TOPIC: {topic}

Analyze and return JSON:
{{
    "core_concept": "One sentence: What is this topic really about?",
    "emotional_hook": "What emotion will grab viewers? (curiosity/fear/excitement/hope)",
    "target_audience": "Who specifically cares about this? Be specific.",
    "current_relevance": "Why does this matter RIGHT NOW?",
    "controversy_angle": "Is there a debate or surprise here?",
    "transformation_promise": "What will viewers learn/gain?"
}}"""


def get_research_prompt(perception: dict, ctx: dict) -> str:
    return f"""You are the KNOWLEDGE RETRIEVAL module for a {ctx['niche']} content channel.
Based on this perception, gather relevant facts and angles.

PERCEPTION: {json.dumps(perception)}

Return JSON with knowledge that would make this script AUTHORITATIVE:
{{
    "key_facts": ["Fact 1 with numbers/dates", "Fact 2", "Fact 3"],
    "expert_quotes": ["Quote that adds credibility"],
    "common_misconceptions": ["What most people get wrong"],
    "surprising_angle": "Something unexpected about this topic",
    "story_elements": ["Real example or case study"],
    "data_points": ["Statistics that shock or convince"]
}}"""


def get_ideate_prompt(perception: dict, research: dict, ctx: dict) -> str:
    return f"""You are the CREATIVE IDEATION module for a {ctx['niche']} YouTube Short.

CHANNEL: {ctx['channel_name']}
LANGUAGE: {ctx['language_name']}
PERSONA: {ctx['persona']}

PERCEPTION: {json.dumps(perception)}
RESEARCH: {json.dumps(research)}

For a 60-second YouTube Short, generate 3 different creative approaches:

Return JSON:
{{
    "angles": [
        {{
            "hook_style": "Question/Contrast/Story/Revelation",
            "opening_line": "First 5 seconds in {ctx['language_name']}",
            "emotional_arc": "Start emotion → End emotion",
            "unique_value": "Why this approach works"
        }}
    ],
    "recommended_angle": 0,
    "reasoning": "Why this angle is best for engagement"
}}"""


def get_draft_prompt(perception: dict, research: dict, angle: dict, ctx: dict) -> str:
    language_rules = get_script_language_rules(ctx['language'])
    
    return f"""You are the SCRIPTWRITING module for {ctx['channel_name']}.

CHANNEL IDENTITY:
- Name: {ctx['channel_name']}
- Niche: {ctx['niche']}
- Language: {ctx['language_name']}
- Persona: {ctx['persona']}

PERCEPTION: {json.dumps(perception)}
RESEARCH: {json.dumps(research)}
CREATIVE ANGLE: {json.dumps(angle)}

{language_rules}

SCRIPT STRUCTURE (50-70 words, 8-10 sentences):
- Sentence 1-2: HOOK (matches creative angle)
- Sentence 3-4: CONTEXT (why this matters)
- Sentence 5-6: CORE VALUE (the insight)
- Sentence 7-8: PROOF/EXAMPLE
- Sentence 9-10: CTA + THOUGHT-PROVOKER

Return JSON:
{{
    "title": "Catchy title in {ctx['language_name']}",
    "script": "Full script in {ctx['language_name']}",
    "visual_cues": ["Specific", "Searchable", "Terms", "For", "Each", "Scene"],
    "on_screen_text": ["Key phrase 1", "Key phrase 2"],
    "comment_question": "Engaging question in {ctx['language_name']}",
    "thumbnail_text": "2-3 Words maximum"
}}"""


def get_critique_prompt(draft: dict, topic: str, ctx: dict) -> str:
    return f"""You are the QUALITY CONTROL module for {ctx['channel_name']}.
Evaluate this {ctx['niche']} script for a {ctx['language_name']} audience.

SCRIPT: {json.dumps(draft, ensure_ascii=False)}
ORIGINAL TOPIC: {topic}

Score each dimension (1-10):

Return JSON:
{{
    "scores": {{
        "hook_power": 8,
        "information_density": 7,
        "emotional_resonance": 9,
        "clarity": 8,
        "call_to_action": 7,
        "monetization_safe": 10
    }},
    "overall_score": 8.2,
    "critical_issues": ["Issue 1 if any"],
    "improvement_suggestions": ["Specific actionable improvement"],
    "verdict": "APPROVED" or "NEEDS_REVISION",
    "revision_priority": "Which issue to fix first if revising"
}}"""


def get_refine_prompt(draft: dict, critique: str, priority: str, ctx: dict) -> str:
    language_rules = get_script_language_rules(ctx['language'])
    
    return f"""You are the REFINEMENT module for {ctx['channel_name']}.
Improve the script based on critique feedback.

CURRENT SCRIPT: {json.dumps(draft, ensure_ascii=False)}
CRITIQUE: {critique}
PRIORITY FIX: {priority}

{language_rules}

Make targeted improvements while preserving what works.
Return the improved script in the same JSON format.

RULES:
- Fix only the identified issues
- Keep the script in {ctx['language_name']}
- Maintain or improve hook power
- Keep it 50-70 words"""


# ============================================================================
# COGNITIVE NODES
# ============================================================================

def perceive_node(state: CognitiveState) -> dict:
    ctx = get_channel_context()
    prompt = get_perceive_prompt(state["topic"], ctx)
    response = llm_fast.invoke([HumanMessage(content=prompt)])
    
    try:
        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        perception = json.loads(content)
    except:
        perception = {"core_concept": state["topic"], "emotional_hook": "curiosity"}
    
    print(f"[Brain] Perceived: {perception.get('core_concept', 'Unknown')[:50]}...")
    return {"perception": perception}


def research_node(state: CognitiveState) -> dict:
    ctx = get_channel_context()
    prompt = get_research_prompt(state["perception"], ctx)
    response = llm_fast.invoke([HumanMessage(content=prompt)])
    
    try:
        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        research = json.loads(content)
    except:
        research = {"key_facts": [], "surprising_angle": ""}
    
    print(f"[Brain] Researched: {len(research.get('key_facts', []))} facts")
    return {"research": research}


def ideate_node(state: CognitiveState) -> dict:
    ctx = get_channel_context()
    prompt = get_ideate_prompt(state["perception"], state["research"], ctx)
    response = llm_creative.invoke([HumanMessage(content=prompt)])
    
    try:
        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        ideas = json.loads(content)
    except:
        ideas = {"angles": [{"hook_style": "Question"}], "recommended_angle": 0}
    
    print(f"[Brain] Ideated: {len(ideas.get('angles', []))} angles")
    return {"ideas": ideas.get("angles", [ideas])}


def draft_node(state: CognitiveState) -> dict:
    ctx = get_channel_context()
    angles = state.get("ideas", [{}])
    chosen_angle = angles[0] if angles else {}
    
    prompt = get_draft_prompt(state["perception"], state["research"], chosen_angle, ctx)
    response = llm_creative.invoke([HumanMessage(content=prompt)])
    
    try:
        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        draft = json.loads(content)
    except Exception as e:
        draft = {"script": response.content, "visual_cues": [], "error": str(e)}
    
    print(f"[Brain] Drafted: '{draft.get('title', 'Untitled')[:40]}...'")
    return {"draft": draft, "iteration_count": state.get("iteration_count", 0) + 1}


def critique_node(state: CognitiveState) -> dict:
    ctx = get_channel_context()
    prompt = get_critique_prompt(state["draft"], state["topic"], ctx)
    response = llm_precise.invoke([HumanMessage(content=prompt)])
    
    try:
        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        critique_data = json.loads(content)
        score = critique_data.get("overall_score", 7.0)
        verdict = critique_data.get("verdict", "APPROVED")
    except:
        score = 7.0
        verdict = "APPROVED"
        critique_data = {"verdict": verdict}
    
    print(f"[Brain] Critiqued: Score {score}/10 - {verdict}")
    return {
        "critique": json.dumps(critique_data),
        "confidence_score": score / 10.0,
        "quality_flags": critique_data.get("critical_issues", [])
    }


def refine_node(state: CognitiveState) -> dict:
    ctx = get_channel_context()
    try:
        critique_data = json.loads(state["critique"])
        priority = critique_data.get("revision_priority", "general improvement")
    except:
        priority = "general improvement"
    
    prompt = get_refine_prompt(state["draft"], state["critique"], priority, ctx)
    response = llm_creative.invoke([HumanMessage(content=prompt)])
    
    try:
        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        draft = json.loads(content)
    except:
        draft = state["draft"]
    
    print(f"[Brain] Refined: Iteration {state['iteration_count'] + 1}")
    return {"draft": draft, "iteration_count": state["iteration_count"] + 1}


# ============================================================================
# DECISION LOGIC
# ============================================================================

def should_continue(state: CognitiveState) -> str:
    try:
        critique_data = json.loads(state["critique"])
        verdict = critique_data.get("verdict", "APPROVED")
        score = critique_data.get("overall_score", 8.0)
    except:
        verdict = "APPROVED"
        score = 8.0
    
    if verdict == "APPROVED" or score >= 8.5:
        return "end"
    if state["iteration_count"] >= 3:
        return "end"
    return "refine"


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

workflow = StateGraph(CognitiveState)

workflow.add_node("perceive", perceive_node)
workflow.add_node("research", research_node)
workflow.add_node("ideate", ideate_node)
workflow.add_node("draft", draft_node)
workflow.add_node("critique", critique_node)
workflow.add_node("refine", refine_node)

workflow.set_entry_point("perceive")
workflow.add_edge("perceive", "research")
workflow.add_edge("research", "ideate")
workflow.add_edge("ideate", "draft")
workflow.add_edge("draft", "critique")

workflow.add_conditional_edges(
    "critique",
    should_continue,
    {"refine": "refine", "end": END}
)
workflow.add_edge("refine", "critique")

app = workflow.compile()


# ============================================================================
# PUBLIC API
# ============================================================================

def generate_script_with_agent(topic: str) -> dict:
    """Generate a YouTube Short script based on channel configuration."""
    ctx = get_channel_context()
    # Assuming get_feedback_adjustments is imported and modifies ctx or is called here
    # For now, we'll simulate injecting it into ctx if it exists.
    # In a real scenario, get_channel_context() would likely handle this.
    # Or, if get_feedback_adjustments() is a standalone call, it would be:
    # feedback_tuning = get_feedback_adjustments()
    # if feedback_tuning:
    #     ctx["feedback_tuning"] = feedback_tuning
    print(f"\n[Brain] Channel: {ctx['channel_name']} | Language: {ctx['language_name']} | Niche: {ctx['niche']}")
    if ctx.get("feedback_tuning"):
        print(f"[Brain] Applying Feedback Tuning: {ctx['feedback_tuning']}")
    print(f"[Brain] Processing: '{topic}'")
    print("[Brain] " + "="*50)
    
    initial_state = {
        "topic": topic,
        "iteration_count": 0,
        "confidence_score": 0.0,
        "quality_flags": []
    }
    
    final_state = app.invoke(initial_state)
    
    print(f"[Brain] Complete! Confidence: {final_state.get('confidence_score', 0)*100:.0f}%")
    print("[Brain] " + "="*50 + "\n")
    
    return final_state["draft"]


if __name__ == "__main__":
    ctx = get_channel_context()
    print(f"Testing Script Agent for: {ctx['channel_name']}")
    print(f"Language: {ctx['language_name']}, Niche: {ctx['niche']}")
    
    topic = "Why Your Brain Lies to You About Time"
    result = generate_script_with_agent(topic)
    print(json.dumps(result, indent=2, ensure_ascii=False))
