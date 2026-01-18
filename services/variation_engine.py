"""
Variation Engine - Intro/Outro rotation to prevent repetitive patterns

Generates and rotates intro/outro variations to maintain content freshness
and YPP compliance.
"""

import random
import logging
from typing import List, Dict, Optional
from datetime import datetime


class VariationEngine:
    """Manages content variations to prevent repetition"""
    
    # Intro variations (Malayalam)
    INTRO_VARIATIONS = [
        "ഇത് അറിയാമോ?",
        "കണ്ടോ ഇത്?",
        "നോക്ക്, ഇത് പ്രധാനമാണ്!",
        "ഇന്ന് നമ്മൾ പഠിക്കാൻ പോകുന്നത്...",
        "ശ്രദ്ധിക്കൂ, ഇത് നിങ്ങളുടെ ജീവിതം മാറ്റാം!",
        "ഒരു ചോദ്യം: ഇത് നിങ്ങൾക്ക് അറിയാമോ?",
        "ഇന്ന് ഒരു വലിയ സത്യം പറയാൻ പോകുന്നു...",
        "ഇത് കേട്ടാൽ നിങ്ങൾ ഞെട്ടും!",
        "നോക്ക്, ഇത് നിങ്ങൾക്ക് വേണ്ടതാണ്!",
        "ഇന്ന് നമ്മൾ ഒരു പ്രധാന വിഷയം ചർച്ച ചെയ്യാൻ പോകുന്നു...",
        "ശ്രദ്ധിക്കൂ, ഇത് നിങ്ങൾക്ക് ഉപയോഗപ്രദമാകും!",
        "ഇത് അറിയാത്തവർക്ക് വലിയ നഷ്ടമാണ്!",
    ]
    
    # Outro variations (Malayalam)
    OUTRO_VARIATIONS = [
        "കൂടുതൽ അറിയാൻ ചാനൽ സബ്സ്ക്രൈബ് ചെയ്യൂ!",
        "ഇഷ്ടമായാൽ ലൈക്ക് ചെയ്യൂ, കമന്റ് ചെയ്യൂ!",
        "അടുത്ത വീഡിയോയിൽ കാണാം!",
        "ഇത് പങ്കിടൂ, മറ്റുള്ളവർക്കും അറിയട്ടെ!",
        "നന്ദി, അടുത്ത തവണ കാണാം!",
        "ഇഷ്ടമായാൽ ബെൽ ഐക്കൺ ക്ലിക്ക് ചെയ്യൂ!",
        "കൂടുതൽ വീഡിയോകൾക്ക് ചാനൽ സബ്സ്ക്രൈബ് ചെയ്യൂ!",
        "ഇത് ഉപയോഗപ്രദമായാൽ ഷെയർ ചെയ്യൂ!",
        "അടുത്ത വീഡിയോയിൽ കൂടുതൽ പഠിക്കാം!",
        "നന്ദി, ഇഷ്ടമായാൽ ലൈക്ക് ചെയ്യൂ!",
        "കമന്റിൽ നിങ്ങളുടെ അഭിപ്രായം പറയൂ!",
        "ചാനൽ സബ്സ്ക്രൈബ് ചെയ്ത് അപ്ഡേറ്റുകൾ നഷ്ടപ്പെടുത്തരുത്!",
    ]
    
    # Hook variations for script starts
    HOOK_VARIATIONS = [
        "അറിയാമോ?",
        "കണ്ടോ?",
        "നോക്ക്!",
        "ഇത് പ്രധാനമാണ്!",
        "ശ്രദ്ധിക്കൂ!",
        "ഒരു ചോദ്യം:",
        "ഇന്ന് നമ്മൾ പഠിക്കാൻ പോകുന്നത്...",
        "ഇത് കേട്ടാൽ ഞെട്ടും!",
    ]
    
    def __init__(self):
        self.usage_history: List[Dict[str, str]] = []
        self.last_intro_index = -1
        self.last_outro_index = -1
    
    def get_intro(self, avoid_recent: bool = True) -> str:
        """
        Get random intro variation
        
        Args:
            avoid_recent: If True, avoids recently used intros
        
        Returns:
            Intro text
        """
        if avoid_recent and len(self.usage_history) > 0:
            # Get recently used intros
            recent_intros = [
                entry["intro"] for entry in self.usage_history[-5:]
                if "intro" in entry
            ]
            
            # Filter out recent ones
            available = [intro for intro in self.INTRO_VARIATIONS 
                        if intro not in recent_intros]
            
            if available:
                selected = random.choice(available)
            else:
                # All were recent, just pick random
                selected = random.choice(self.INTRO_VARIATIONS)
        else:
            selected = random.choice(self.INTRO_VARIATIONS)
        
        # Track usage
        self.usage_history.append({
            "intro": selected,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 20 entries
        self.usage_history = self.usage_history[-20:]
        
        logging.debug(f"[Variation] Selected intro: {selected[:30]}...")
        return selected
    
    def get_outro(self, avoid_recent: bool = True) -> str:
        """
        Get random outro variation
        
        Args:
            avoid_recent: If True, avoids recently used outros
        
        Returns:
            Outro text
        """
        if avoid_recent and len(self.usage_history) > 0:
            # Get recently used outros
            recent_outros = [
                entry["outro"] for entry in self.usage_history[-5:]
                if "outro" in entry
            ]
            
            # Filter out recent ones
            available = [outro for outro in self.OUTRO_VARIATIONS 
                        if outro not in recent_outros]
            
            if available:
                selected = random.choice(available)
            else:
                selected = random.choice(self.OUTRO_VARIATIONS)
        else:
            selected = random.choice(self.OUTRO_VARIATIONS)
        
        # Track usage
        self.usage_history.append({
            "outro": selected,
            "timestamp": datetime.now().isoformat()
        })
        
        # Keep only last 20 entries
        self.usage_history = self.usage_history[-20:]
        
        logging.debug(f"[Variation] Selected outro: {selected[:30]}...")
        return selected
    
    def get_hook(self) -> str:
        """Get random hook variation"""
        return random.choice(self.HOOK_VARIATIONS)
    
    def add_script_variation(self, script: str, add_intro: bool = True, 
                            add_outro: bool = True) -> str:
        """
        Add intro/outro variations to script
        
        Args:
            script: Original script text
            add_intro: Whether to add intro
            add_outro: Whether to add outro
        
        Returns:
            Script with variations added
        """
        result = script
        
        if add_intro:
            intro = self.get_intro()
            result = f"{intro} {result}"
        
        if add_outro:
            outro = self.get_outro()
            result = f"{result} {outro}"
        
        return result
    
    def get_variation_stats(self) -> Dict[str, any]:
        """Get statistics on variation usage"""
        intro_counts = {}
        outro_counts = {}
        
        for entry in self.usage_history:
            if "intro" in entry:
                intro = entry["intro"]
                intro_counts[intro] = intro_counts.get(intro, 0) + 1
            if "outro" in entry:
                outro = entry["outro"]
                outro_counts[outro] = outro_counts.get(outro, 0) + 1
        
        return {
            "total_uses": len(self.usage_history),
            "intro_distribution": intro_counts,
            "outro_distribution": outro_counts,
            "unique_intros_used": len(intro_counts),
            "unique_outros_used": len(outro_counts)
        }


# Global variation engine instance
variation_engine = VariationEngine()
