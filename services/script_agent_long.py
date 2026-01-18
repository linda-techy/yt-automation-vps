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
import logging
from typing import TypedDict, List, Optional
from langgraph.graph import StateGraph, END
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
# LLM SETUP - Using wrapped LLM with error handling
# ============================================================================
from adapters.openai.llm_wrapper import get_llm_analyst, get_llm_storyteller, get_llm_editor

# Lazy initialization - only create when needed (avoids API key requirement at import time)
_llm_analyst = None
_llm_storyteller = None
_llm_editor = None

def _get_llm_analyst():
    """Lazy getter for analyst LLM"""
    global _llm_analyst
    if _llm_analyst is None:
        _llm_analyst = get_llm_analyst()  # Imported function from llm_wrapper
    return _llm_analyst

def _get_llm_storyteller():
    """Lazy getter for storyteller LLM"""
    global _llm_storyteller
    if _llm_storyteller is None:
        _llm_storyteller = get_llm_storyteller()  # Imported function from llm_wrapper
    return _llm_storyteller

def _get_llm_editor():
    """Lazy getter for editor LLM"""
    global _llm_editor
    if _llm_editor is None:
        _llm_editor = get_llm_editor()  # Imported function from llm_wrapper
    return _llm_editor

# Import prompt registry and compressor for token optimization
from utils.prompts.registry import registry
from utils.prompts.compressor import compressor

# ============================================================================
# DYNAMIC PROMPT GENERATORS
# ============================================================================

def get_perceive_prompt(topic: str, ctx: dict) -> str:
    """Get perception prompt using registry"""
    return registry.get_long_perceive_prompt(topic)


def get_research_prompt(perception: dict, topic: str, ctx: dict) -> str:
    """Get research prompt with compressed context"""
    perception_summary = compressor.compress_dict(perception, max_length=150)
    return registry.get_long_research_prompt(perception_summary, topic)


def get_structure_prompt(perception: dict, research: dict, ctx: dict) -> str:
    """Get structure prompt with compressed context"""
    perception_summary = compressor.compress_dict(perception, max_length=150)
    research_summary = compressor.compress_dict(research, max_length=200)
    return registry.get_long_structure_prompt(perception_summary, research_summary)


def get_section_prompt(section_info: dict, research: dict, perception: dict, 
                       target_words: int, ctx: dict) -> str:
    """Get section prompt using registry with compressed context"""
    # Compress context before sending (reduce tokens by 60-80%)
    section_info_summary = compressor.compress_dict(section_info, max_length=100)
    research_summary = compressor.compress_dict(research, max_length=200)
    perception_summary = compressor.compress_dict(perception, max_length=150)
    
    # Use registry method which already uses compact templates
    return registry.get_long_section_prompt(
        section_info_summary,
        research_summary,
        perception_summary,
        target_words
    )


def get_assemble_prompt(sections: list, perception: dict, ctx: dict) -> str:
    """Get assemble prompt with compressed context"""
    sections_summary = compressor.compress_structure({"sections": sections})
    perception_summary = compressor.compress_dict(perception, max_length=100)
    return registry.get_long_assemble_prompt(sections_summary, perception_summary)


def get_critique_prompt(script: dict, ctx: dict) -> str:
    """Get critique prompt with compressed context"""
    script_summary = compressor.compress_dict(script, max_length=200)
    return registry.get_long_critique_prompt(script_summary)


# ============================================================================
# COGNITIVE NODES
# ============================================================================

def perceive_long_node(state: DocumentaryState) -> dict:
    ctx = get_channel_context()
    prompt = get_perceive_prompt(state["topic"], ctx)
    response = _get_llm_analyst().invoke([HumanMessage(content=prompt)])
    
    try:
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        perception = json.loads(content)
    except Exception as e:
        logging.warning(f"[ScriptAgentLong] Failed to parse perception JSON: {e}, using fallback")
        perception = {"core_thesis": state["topic"]}
    
    safe_thesis = perception.get('core_thesis', '').encode('ascii', 'replace').decode('ascii')
    print(f"[DocBrain] Perceived: {safe_thesis[:60]}...")
    return {"perception": perception}


def research_long_node(state: DocumentaryState) -> dict:
    """Research node with compressed context"""
    from utils.logging.tracer import tracer
    
    ctx = get_channel_context()
    prompt = get_research_prompt(state["perception"], state["topic"], ctx)
    
    try:
        response = _get_llm_analyst().invoke(
            [HumanMessage(content=prompt)],
            trace_id=tracer.get_trace_id(),
            compress_context=True
        )
        
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        research = json.loads(content)
    except Exception as e:
        logging.warning(f"[DocBrain] Research parsing failed: {e}, using fallback")
        research = {"key_statistics": [], "case_studies": []}
    
    print(f"[DocBrain] Researched: {len(research.get('key_statistics', []))} stats")
    return {"research": research}


def structure_node(state: DocumentaryState) -> dict:
    """Structure node with compressed context"""
    from utils.logging.tracer import tracer
    
    ctx = get_channel_context()
    prompt = get_structure_prompt(state["perception"], state["research"], ctx)
    
    try:
        response = _get_llm_analyst().invoke(
            [HumanMessage(content=prompt)],
            trace_id=tracer.get_trace_id(),
            compress_context=True
        )
        
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        structure = json.loads(content)
    except Exception as e:
        logging.warning(f"[DocBrain] Structure parsing failed: {e}, using fallback")
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
        
        from utils.logging.tracer import tracer
        from utils.prompts.compressor import compressor
        
        # Compress research and perception before sending
        research_summary = compressor.compress_dict(state["research"], max_length=200)
        perception_summary = compressor.compress_dict(state["perception"], max_length=150)
        
        prompt = get_section_prompt(section_plan, state["research"], 
                                    state["perception"], target_words, ctx)
        
        try:
            response = _get_llm_storyteller().invoke(
                [HumanMessage(content=prompt)],
                trace_id=tracer.get_trace_id(),
                compress_context=True
            )
            
            content = response.content.strip()
            
            # Extract JSON if wrapped in code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                # Try to extract from generic code block
                parts = content.split("```")
                if len(parts) >= 2:
                    content = parts[1].strip()
                    if content.startswith("json"):
                        content = content[4:].strip()
            
            # Validate content is not empty
            if not content or content == "":
                raise ValueError("Empty response from LLM")
            
            # Try to parse JSON with better error handling
            try:
                section = json.loads(content)
            except json.JSONDecodeError as json_error:
                # Log the actual content for debugging
                logging.error(f"[DocBrain] JSON decode error. Response preview: {content[:200]}...")
                # Try to extract JSON object manually with improved regex for nested structures
                import re
                # Better regex that handles nested braces more reliably
                # Try balanced brace matching
                brace_count = 0
                start_idx = -1
                for i, char in enumerate(content):
                    if char == '{':
                        if brace_count == 0:
                            start_idx = i
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0 and start_idx >= 0:
                            # Found a complete JSON object
                            json_str = content[start_idx:i+1]
                            try:
                                section = json.loads(json_str)
                                logging.info(f"[DocBrain] Recovered JSON from balanced braces")
                                break
                            except:
                                pass
                else:
                    # Fallback to simple regex if balanced matching failed
                    json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content)
                    if json_match:
                        try:
                            section = json.loads(json_match.group(0))
                            logging.info(f"[DocBrain] Recovered JSON from partial response")
                        except:
                            raise json_error
                    else:
                        raise json_error
        except Exception as e:
            # Retry once with more explicit prompt
            try:
                logging.warning(f"[DocBrain] Section parsing failed: {e}, retrying with explicit JSON request...")
                retry_prompt = f"""{prompt}

CRITICAL: Respond ONLY with valid JSON. No explanations, no markdown, no text before or after.
Required JSON format:
{{
    "header": "Section Title Here",
    "content": "Section content text here...",
    "visual_cues": ["cue1", "cue2", "cue3"],
    "on_screen_text": "Text to display",
    "word_count": 200
}}

Respond with ONLY the JSON object, nothing else."""
                response = _get_llm_storyteller().invoke(
                    [HumanMessage(content=retry_prompt)],
                    compress_context=False  # Don't compress on retry
                )
                content = response.content.strip()
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    parts = content.split("```")
                    if len(parts) >= 2:
                        content = parts[1].strip()
                        if content.startswith("json"):
                            content = content[4:].strip()
                
                if content and content != "":
                    section = json.loads(content)
                    logging.info(f"[DocBrain] Retry successful - parsed JSON")
                else:
                    raise ValueError("Empty response on retry")
            except Exception as retry_error:
                logging.error(f"[DocBrain] Retry also failed: {retry_error}. Response: {response.content[:200] if 'response' in locals() else 'N/A'}...")
                # Last resort fallback - create minimal valid section
                # Ensure header is always a string, never a dict
                fallback_header = section_plan.get("name", "Section")
                if isinstance(fallback_header, dict):
                    fallback_header = fallback_header.get('title', fallback_header.get('name', 'Section'))
                elif not isinstance(fallback_header, str):
                    fallback_header = str(fallback_header) if fallback_header else 'Section'
                
                section = {
                    "header": fallback_header,
                    "content": f"[Content generation failed. Topic: {state['topic']}]", 
                    "visual_cues": []
                }
        
        # Normalize section structure - ensure all fields have correct types
        if not isinstance(section, dict):
            logging.warning(f"[DocBrain] Section is not a dict, creating fallback")
            section = {
                "header": "Section",
                "content": f"[Invalid section format: {type(section).__name__}]",
                "visual_cues": []
            }
        
        # Validate and normalize header (must be string)
        header_value = section.get('header', 'Section')
        if isinstance(header_value, dict):
            header_value = header_value.get('title', header_value.get('name', 'Section'))
        elif not isinstance(header_value, str):
            header_value = str(header_value) if header_value else 'Section'
        section['header'] = header_value
        
        # Validate and normalize content (must be string)
        content_value = section.get('content', '')
        if isinstance(content_value, list):
            content_value = ' '.join(str(item) for item in content_value)
        elif not isinstance(content_value, str):
            content_value = str(content_value) if content_value else ''
        section['content'] = content_value
        
        # Validate and normalize visual_cues (must be list)
        visual_cues_value = section.get('visual_cues', [])
        if not isinstance(visual_cues_value, list):
            visual_cues_value = [str(visual_cues_value)] if visual_cues_value else []
        section['visual_cues'] = visual_cues_value
        
        sections.append(section)
        safe_header = header_value.encode('ascii', 'replace').decode('ascii')
        print(f"[DocBrain] Drafted: {safe_header}")
    
    return {"sections": sections}


def assemble_node(state: DocumentaryState) -> dict:
    """Assemble node with compressed context"""
    from utils.logging.tracer import tracer
    from utils.prompts.compressor import compressor
    
    ctx = get_channel_context()
    # Compress sections before sending
    structure_summary = compressor.compress_structure({"sections": state["sections"]})
    prompt = get_assemble_prompt(state["sections"], state["perception"], ctx)
    
    try:
        response = _get_llm_editor().invoke(
            [HumanMessage(content=prompt)],
            trace_id=tracer.get_trace_id(),
            compress_context=True
        )
        
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        draft = json.loads(content)
    except Exception as e:
        logging.warning(f"[DocBrain] Assemble parsing failed: {e}, using fallback")
        draft = {"title": state["topic"], "sections": state["sections"]}
    
    # Safely get word count - content might be string or list
    def get_word_count(section):
        word_count = section.get("word_count")
        if word_count is not None:
            return word_count
        
        content = section.get("content", "")
        # Handle both string and list content
        if isinstance(content, list):
            # If content is a list, join it or count items
            content_str = " ".join(str(item) for item in content) if content else ""
            return len(content_str.split()) if content_str else 0
        elif isinstance(content, str):
            return len(content.split()) if content else 0
        else:
            return 0
    
    total_words = sum(get_word_count(s) for s in state["sections"])
    
    safe_title = draft.get('title', '').encode('ascii', 'replace').decode('ascii')
    print(f"[DocBrain] Assembled: '{safe_title[:50]}' (~{total_words} words)")
    return {"draft": draft, "total_word_count": total_words, 
            "iteration_count": state.get("iteration_count", 0) + 1}


def critique_long_node(state: DocumentaryState) -> dict:
    """Critique node with compressed context"""
    from utils.logging.tracer import tracer
    from utils.prompts.compressor import compressor
    
    ctx = get_channel_context()
    # Compress draft before sending
    draft_summary = compressor.compress_dict(state["draft"], max_length=200)
    prompt = get_critique_prompt(state["draft"], ctx)
    
    try:
        response = _get_llm_editor().invoke(
            [HumanMessage(content=prompt)],
            trace_id=tracer.get_trace_id(),
            compress_context=True
        )
        
        content = response.content.strip()
        
        # Extract JSON if wrapped in code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            parts = content.split("```")
            if len(parts) >= 2:
                content = parts[1].strip()
                if content.startswith("json"):
                    content = content[4:].strip()
        
        # Validate content is not empty
        if not content or content == "":
            raise ValueError("Empty response from LLM")
        
        # Try to parse JSON with better error handling
        try:
            critique = json.loads(content)
        except json.JSONDecodeError as json_error:
            logging.error(f"[DocBrain] JSON decode error. Response preview: {content[:200]}...")
            # Try to extract JSON object manually
            import re
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content)
            if json_match:
                try:
                    critique = json.loads(json_match.group(0))
                    logging.info(f"[DocBrain] Recovered JSON from partial response")
                except:
                    raise json_error
            else:
                raise json_error
    except Exception as e:
        # Retry once with more explicit prompt
        try:
            logging.warning(f"[DocBrain] Critique parsing failed: {e}, retrying with explicit JSON request...")
            retry_prompt = f"{prompt}\n\nCRITICAL: Respond ONLY with valid JSON. No explanations, no markdown, just JSON."
            response = _get_llm_editor().invoke(
                [HumanMessage(content=retry_prompt)],
                compress_context=False  # Don't compress on retry
            )
            content = response.content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                parts = content.split("```")
                if len(parts) >= 2:
                    content = parts[1].strip()
                    if content.startswith("json"):
                        content = content[4:].strip()
            
            if content and content != "":
                critique = json.loads(content)
                logging.info(f"[DocBrain] Retry successful - parsed JSON")
            else:
                raise ValueError("Empty response on retry")
        except Exception as retry_error:
            logging.error(f"[DocBrain] Retry also failed: {retry_error}. Response: {response.content[:200] if 'response' in locals() else 'N/A'}...")
            # Fallback with warning
            critique = {"overall_score": 8.0, "verdict": "APPROVED", "warning": "Fallback used due to parsing failure"}
    
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
