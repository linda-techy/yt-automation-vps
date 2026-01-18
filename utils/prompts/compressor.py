"""
Context Compression - Summarize long contexts before LLM calls

Reduces token usage by 40-60% by:
- Summarizing perception/research data
- Compressing JSON structures
- Extracting key points only
"""

import json
from typing import Dict, Any, List, Optional


class ContextCompressor:
    """Compress long contexts into compact summaries"""
    
    @staticmethod
    def compress_dict(data: Dict[str, Any], max_length: int = 100) -> str:
        """
        Compress dictionary to compact string representation
        
        Args:
            data: Dictionary to compress
            max_length: Max characters per value
        
        Returns:
            Compact string representation
        """
        if not data:
            return ""
        
        parts = []
        for key, value in data.items():
            if isinstance(value, str):
                # Truncate long strings
                val_str = value[:max_length] + "..." if len(value) > max_length else value
                parts.append(f"{key}:{val_str}")
            elif isinstance(value, (list, dict)):
                # Summarize collections
                if isinstance(value, list):
                    if len(value) > 3:
                        parts.append(f"{key}:[{len(value)}items]")
                    else:
                        parts.append(f"{key}:{','.join(str(v)[:30] for v in value[:3])}")
                else:
                    parts.append(f"{key}:{{dict}}")
            else:
                parts.append(f"{key}:{value}")
        
        return "|".join(parts)
    
    @staticmethod
    def compress_perception(perception: Dict[str, Any]) -> str:
        """Compress perception data to key points"""
        if not perception:
            return ""
        
        # Extract only essential fields
        core = perception.get("core_concept", "")[:80]
        hook = perception.get("emotional_hook", "")[:30]
        relevance = perception.get("current_relevance", "")[:60]
        
        return f"C:{core}|H:{hook}|R:{relevance}"
    
    @staticmethod
    def compress_research(research: Dict[str, Any]) -> str:
        """Compress research data to key points"""
        if not research:
            return ""
        
        # Extract top facts only
        facts = research.get("key_facts", [])[:3]
        facts_str = "|".join(f[:50] for f in facts)
        angle = research.get("surprising_angle", "")[:60]
        
        return f"F:{facts_str}|A:{angle}"
    
    @staticmethod
    def compress_angle(angle: Dict[str, Any]) -> str:
        """Compress creative angle to key points"""
        if not angle:
            return ""
        
        hook = angle.get("hook_style", "")[:20]
        opening = angle.get("opening_line", "")[:40]
        
        return f"H:{hook}|O:{opening}"
    
    @staticmethod
    def compress_structure(structure: Dict[str, Any]) -> str:
        """Compress long-form structure to summary"""
        if not structure:
            return ""
        
        sections = structure.get("sections", [])
        section_count = len(sections)
        total_duration = structure.get("total_duration", 0)
        
        # Summarize section titles only
        titles = [s.get("title", "")[:30] for s in sections[:5]]
        titles_str = "|".join(titles)
        
        return f"SECTIONS:{section_count}|DUR:{total_duration}|T:{titles_str}"
    
    @staticmethod
    def compress_json_safely(data: Any, max_chars: int = 200) -> str:
        """
        Safely compress JSON data to string
        
        Args:
            data: JSON-serializable data
            max_chars: Maximum characters in output
        
        Returns:
            Compact string representation
        """
        try:
            json_str = json.dumps(data, ensure_ascii=False)
            if len(json_str) <= max_chars:
                return json_str
            # Truncate and add indicator
            return json_str[:max_chars-10] + "...[trunc]"
        except Exception:
            # Fallback to string representation
            str_repr = str(data)
            return str_repr[:max_chars] if len(str_repr) > max_chars else str_repr


# Global compressor instance
compressor = ContextCompressor()
