"""
Centralized Configuration Loader
Loads channel_config.yaml and provides typed access to all settings
"""

import yaml
import os
import logging
from typing import Dict, Any, List


class ChannelConfig:
    """
    Centralized configuration manager.
    
    Eliminates ALL hardcoded values - everything comes from channel_config.yaml.
    """
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._load_config()
        return cls._instance
    
    @classmethod
    def _load_config(cls):
        """Load configuration from YAML file."""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "channel_config.yaml")
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            cls._config = yaml.safe_load(f)
        
        logging.info(f"✅ Loaded config for channel: {cls._config['channel']['name']}")
    
    @classmethod
    def get(cls, key_path: str, default=None):
        """
        Get config value by dot notation path.
        
        Example:
            config.get("channel.name") → "FinMindMalayalam"
            config.get("niche.primary") → "Personal Finance & Money Management"
        """
        if cls._config is None:
            cls._load_config()
        
        keys = key_path.split('.')
        value = cls._config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    @classmethod
    def reload(cls):
        """Reload configuration (useful for testing)."""
        cls._load_config()
    
    # Convenience property accessors
    
    @property
    def channel_name(self) -> str:
        return self.get("channel.name", "FinMindMalayalam")
    
    @property
    def channel_handle(self) -> str:
        return self.get("channel.handle", "@FinMindMalayalam")
    
    @property
    def niche_primary(self) -> str:
        return self.get("niche.primary", "Personal Finance")
    
    @property
    def niche_description(self) -> str:
        return self.get("niche.description", "")
    
    @property
    def content_types(self) -> List[str]:
        return self.get("niche.content_types", [])
    
    @property
    def example_topics(self) -> List[str]:
        return self.get("niche.example_topics", [])
    
    @property
    def malayalam_keywords(self) -> Dict[str, List[str]]:
        return self.get("niche.malayalam_keywords", {})
    
    @property
    def excluded_topics(self) -> List[str]:
        return self.get("niche.excluded_topics", [])
    
    @property
    def persona(self) -> str:
        return self.get("content.persona", "The Practical Guide")
    
    @property
    def content_tone(self) -> List[str]:
        return self.get("content.tone", [])
    
    @property
    def hook_types(self) -> List[str]:
        return self.get("content.hook_types", [])
    
    @property
    def visual_themes(self) -> Dict[str, str]:
        return self.get("visuals.themes", {})
    
    @property
    def thumbnail_hooks(self) -> List[str]:
        return self.get("visuals.thumbnail.hooks", [])
    
    @property
    def default_tags(self) -> List[str]:
        return self.get("seo.default_tags", [])
    
    @property
    def voice_id(self) -> str:
        return self.get("audio.voice_id", "ml-IN-MidhunNeural")
    
    @property
    def language(self) -> str:
        return self.get("channel.language", "ml")


# Global config instance
config = ChannelConfig()


if __name__ == "__main__":
    # Test configuration loading
    print("\n" + "="*60)
    print("CHANNEL CONFIGURATION")
    print("="*60)
    print(f"Channel Name: {config.channel_name}")
    print(f"Niche: {config.niche_primary}")
    print(f"Content Types: {config.content_types}")
    print(f"Example Topics: {config.example_topics[:3]}")
    print(f"Persona: {config.persona}")
    print(f"Tags: {config.default_tags}")
