"""
Channel Configuration Loader

Loads channel_config.yaml and provides settings to all modules.
This is the SINGLE SOURCE OF TRUTH for channel configuration.

Usage:
    from config.channel import channel_config
    
    channel_name = channel_config.get("channel.name")
    niche = channel_config.get("niche.primary")
    topic_keywords = channel_config.get("niche.topic_keywords")
"""

import os
import yaml
from typing import Any, Optional


class ChannelConfig:
    """
    Centralized channel configuration manager.
    Reads from channel_config.yaml and provides easy access to settings.
    """
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self):
        """Load configuration from YAML file."""
        config_paths = [
            "channel_config.yaml",
            "channel_config.yml",
            os.path.join(os.path.dirname(__file__), "..", "channel_config.yaml"),
        ]
        
        for path in config_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f)
                print(f"[Config] Loaded: {path}")
                return
        
        # Fallback to default config
        print("[Config] WARNING: channel_config.yaml not found, using defaults")
        self._config = self._get_defaults()
    
    def _get_defaults(self) -> dict:
        """Default configuration if YAML not found."""
        return {
            "channel": {
                "name": "My Channel",
                "handle": "@MyChannel",
                "language": "en",
                "country": "US",
                "copyright_year": 2025
            },
            "niche": {
                "primary": "Technology",
                "topic_keywords": ["Technology", "AI", "Innovation"],
                "excluded_topics": ["Politics", "Religion"]
            },
            "content": {
                "persona": "The Storyteller"
            },
            "audio": {
                "engine": "edge-tts",
                "voice_id": "en-US-GuyNeural",
                "language_code": "en-US",
                "background_music": {"enabled": True, "volume": 0.05}
            },
            "visuals": {
                "watermark": {"text": "@MyChannel", "opacity": 0.3}
            },
            "formats": {
                "long_form": {"enabled": True, "duration_minutes": 10},
                "shorts": {"enabled": True, "count_per_long": 5}
            },
            "schedule": {
                "timezone": "UTC",
                "upload_time": "12:00"
            },
            "seo": {
                "default_tags": []
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key: Dot-separated path (e.g., "channel.name", "niche.topic_keywords")
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split(".")
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_all(self) -> dict:
        """Get entire configuration dictionary."""
        return self._config.copy()
    
    def reload(self):
        """Reload configuration from file."""
        self._load_config()
    
    # =========================================================================
    # CONVENIENCE PROPERTIES
    # =========================================================================
    
    @property
    def channel_name(self) -> str:
        return self.get("channel.name", "My Channel")
    
    @property
    def channel_handle(self) -> str:
        return self.get("channel.handle", "@MyChannel")
    
    @property
    def language(self) -> str:
        return self.get("channel.language", "en")
    
    @property
    def niche(self) -> str:
        return self.get("niche.primary", "General")
    
    @property
    def excluded_topics(self) -> list:
        return self.get("niche.excluded_topics", [])
    
    @property
    def persona(self) -> str:
        return self.get("content.persona", "The Storyteller")
    
    @property
    def voice_id(self) -> str:
        return self.get("audio.voice_id", "en-US-GuyNeural")
    
    @property
    def language_code(self) -> str:
        return self.get("audio.language_code", "en-US")
    
    @property
    def bgm_volume(self) -> float:
        return self.get("audio.background_music.volume", 0.05)
    
    @property
    def watermark_text(self) -> str:
        return self.get("visuals.watermark.text", "")
    
    @property
    def default_tags(self) -> list:
        return self.get("seo.default_tags", [])
    
    @property
    def timezone(self) -> str:
        return self.get("schedule.timezone", "UTC")
    
    @property
    def upload_time(self) -> str:
        return self.get("schedule.upload_time", "12:00")


# Global instance for easy import
channel_config = ChannelConfig()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_search_topics() -> list:
    """Get list of topic keywords for news search."""
    return channel_config.topic_keywords


def is_topic_allowed(topic: str) -> bool:
    """Check if a topic is allowed (not in excluded list)."""
    excluded = channel_config.excluded_topics
    topic_lower = topic.lower()
    return not any(ex.lower() in topic_lower for ex in excluded)


def get_description_footer() -> str:
    """Get formatted description footer with channel info."""
    footer = channel_config.get("seo.description_footer", "")
    return footer.format(
        channel_handle=channel_config.channel_handle,
        channel_name=channel_config.channel_name,
        copyright_year=channel_config.get("channel.copyright_year", 2025)
    )


if __name__ == "__main__":
    print("Channel Configuration Test")
    print("=" * 50)
    print(f"Channel: {channel_config.channel_name}")
    print(f"Handle: {channel_config.channel_handle}")
    print(f"Language: {channel_config.language}")
    print(f"Niche: {channel_config.niche}")
    print(f"Topics: {channel_config.topic_keywords[:3]}...")
    print(f"Voice: {channel_config.voice_id}")
    print(f"Persona: {channel_config.persona}")
