"""
Prompt Registry - Centralized reusable prompt templates

Reduces token usage by:
- Reusing common prompt blocks
- Using compact templates instead of f-strings
- Eliminating repeated system instructions
"""

import json
from typing import Dict, Any, Optional
from config.channel import channel_config


class PromptRegistry:
    """Centralized prompt template registry"""
    
    # Cached channel context (loaded once)
    _channel_context: Optional[Dict[str, Any]] = None
    
    @classmethod
    def get_channel_context(cls) -> Dict[str, Any]:
        """Get channel context (cached after first call)"""
        if cls._channel_context is None:
            try:
                from config.channel import channel_config
                cls._channel_context = {
                    "channel_name": channel_config.get("channel.name", "My Channel"),
                    "language": channel_config.get("channel.language", "en"),
                    "language_name": cls._get_language_name(channel_config.get("channel.language", "en")),
                    "niche": channel_config.get("niche.primary", "Technology"),
                    "persona": channel_config.get("content.persona", "The Storyteller"),
                    "country": channel_config.get("channel.country", "US"),
                    "topic_keywords": channel_config.get("niche.topic_keywords", []),
                }
            except Exception:
                cls._channel_context = {
                    "channel_name": "My Channel",
                    "language": "en",
                    "language_name": "English",
                    "niche": "Technology",
                    "persona": "The Storyteller",
                    "country": "US",
                    "topic_keywords": [],
                }
        return cls._channel_context
    
    @staticmethod
    def _get_language_name(code: str) -> str:
        """Convert language code to full name"""
        languages = {
            "ml": "Malayalam", "hi": "Hindi", "ta": "Tamil", "te": "Telugu",
            "kn": "Kannada", "bn": "Bengali", "en": "English", "es": "Spanish",
            "fr": "French", "de": "German", "ar": "Arabic"
        }
        return languages.get(code, "English")
    
    @staticmethod
    def get_language_rules(language: str) -> str:
        """Get compact language rules (reusable block)"""
        lang_name = PromptRegistry._get_language_name(language)
        if language in ["ml", "hi", "ta", "te", "kn", "bn"]:
            return f"LANG:{lang_name}|UNICODE_ONLY|TECH_TERMS_EN|ACRONYMS_DOTTED"
        return f"LANG:{lang_name}|NATURAL_TONE"
    
    # Compact prompt blocks (reusable)
    BLOCKS = {
        "channel_header": "CH:{channel_name}|N:{niche}|L:{language_name}|P:{persona}|C:{country}",
        "json_schema_compact": "JSON:{{key1,key2,key3}}",
        "perception_schema": "JSON:{core_concept,emotional_hook,target_audience,current_relevance,controversy_angle,transformation_promise}",
        "research_schema": "JSON:{key_facts,expert_quotes,common_misconceptions,surprising_angle,story_elements,data_points}",
        "script_schema": "JSON:{title,script,visual_cues,on_screen_text,comment_question,thumbnail_text}",
    }
    
    @classmethod
    def get_perceive_prompt(cls, topic: str) -> str:
        """Compact perception prompt"""
        ctx = cls.get_channel_context()
        header = cls.BLOCKS["channel_header"].format(**ctx)
        return f"{header}\nPERCEPTION_MODULE|TOPIC:{topic}\n{cls.BLOCKS['perception_schema']}"
    
    @classmethod
    def get_research_prompt(cls, perception_summary: str) -> str:
        """Compact research prompt (uses summarized perception)"""
        return f"RESEARCH_MODULE|PERCEPTION:{perception_summary}\n{cls.BLOCKS['research_schema']}"
    
    @classmethod
    def get_ideate_prompt(cls, perception_summary: str, research_summary: str) -> str:
        """Compact ideation prompt"""
        ctx = cls.get_channel_context()
        header = cls.BLOCKS["channel_header"].format(**ctx)
        return f"{header}\nIDEATION_MODULE|P:{perception_summary}|R:{research_summary}\nJSON:{{angles:[{{hook_style,opening_line,emotional_arc,unique_value}}],recommended_angle,reasoning}}"
    
    @classmethod
    def get_draft_prompt(cls, perception_summary: str, research_summary: str, angle_summary: str) -> str:
        """Compact draft prompt"""
        ctx = cls.get_channel_context()
        lang_rules = cls.get_language_rules(ctx['language'])
        header = cls.BLOCKS["channel_header"].format(**ctx)
        return f"{header}\nSCRIPT_MODULE|LANG_RULES:{lang_rules}|P:{perception_summary}|R:{research_summary}|A:{angle_summary}\nSTRUCTURE:HOOK(2s)|CONTEXT(2s)|VALUE(2s)|PROOF(2s)|CTA(2s)\n{cls.BLOCKS['script_schema']}"
    
    @classmethod
    def get_critique_prompt(cls, draft_summary: str, topic: str) -> str:
        """Compact critique prompt"""
        return f"CRITIQUE_MODULE|TOPIC:{topic}|DRAFT:{draft_summary}\nJSON:{{score,issues,improvements}}"
    
    # Long-form prompts (documentary style)
    @classmethod
    def get_long_perceive_prompt(cls, topic: str) -> str:
        """Long-form perception prompt"""
        ctx = cls.get_channel_context()
        header = cls.BLOCKS["channel_header"].format(**ctx)
        return f"{header}\nDOC_PERCEPTION|TOPIC:{topic}\nJSON:{{core_thesis,why_now,target_viewer,emotional_journey:{{start,middle,end}},controversy,transformation}}"
    
    @classmethod
    def get_long_research_prompt(cls, perception_summary: str, topic: str) -> str:
        """Long-form research prompt"""
        return f"DOC_RESEARCH|TOPIC:{topic}|P:{perception_summary}\nJSON:{{timeline:[{{year,event}}],key_statistics,expert_insights,case_studies,data_sources}}"
    
    @classmethod
    def get_long_structure_prompt(cls, perception_summary: str, research_summary: str) -> str:
        """Long-form structure prompt"""
        return f"DOC_STRUCTURE|P:{perception_summary}|R:{research_summary}\nJSON:{{sections:[{{title,duration_sec,content_outline,visual_style}}],total_duration,tone}}"
    
    @classmethod
    def get_long_draft_prompt(cls, structure_summary: str) -> str:
        """Long-form draft prompt"""
        ctx = cls.get_channel_context()
        lang_rules = cls.get_language_rules(ctx['language'])
        return f"DOC_DRAFT|LANG:{lang_rules}|STRUCT:{structure_summary}\nJSON:{{title,sections:[{{title,content,visual_cues,on_screen_text}}],thumbnail_text}}"
    
    # SEO prompts
    @classmethod
    def get_seo_prompt(cls, topic: str) -> str:
        """Compact SEO prompt"""
        ctx = cls.get_channel_context()
        lang_name = ctx['language_name']
        return f"SEO_MODULE|TOPIC:{topic}|LANG:{lang_name}\nJSON:{{title,description,tags:[str]}}"
    
    # Repurposer prompt
    @classmethod
    def get_repurpose_prompt(cls) -> str:
        """Compact repurpose prompt"""
        ctx = cls.get_channel_context()
        lang_name = ctx['language_name']
        return f"REPURPOSE_MODULE|LANG:{lang_name}\nEXTRACT:5_SHORTS|STRUCTURE:HOOK(5s)|VALUE(40s)|CTA(5s)|CURIOSITY_LOOP\nJSON:[{{title,script,visual_cues,thumbnail_text}}]"


# Global registry instance
registry = PromptRegistry()
