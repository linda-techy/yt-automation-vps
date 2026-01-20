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
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        self._config = yaml.safe_load(f)
                    print(f"[Config] Loaded: {path}")
                    
                    # Validate configuration
                    try:
                        from config.validator import ConfigValidator
                        ConfigValidator.validate_and_raise()
                    except ImportError:
                        # Validator not available, skip validation
                        pass
                    except ValueError as e:
                        # Validation failed - log but continue with defaults
                        import logging
                        logging.error(f"[Config] Validation failed: {e}")
                        logging.warning("[Config] Using default configuration due to validation errors")
                        self._config = self._get_defaults()
                    
                    return
                except yaml.YAMLError as e:
                    import logging
                    logging.error(f"[Config] Failed to parse YAML file {path}: {e}")
                    print(f"[Config] ERROR: Invalid YAML in {path}, using defaults")
                    self._config = self._get_defaults()
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
                "background_music": {"enabled": True, "volume": 0.05},
                "voice_boost": 1.5,
                "sample_rate": 44100
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
            },
            "thumbnails": {
                "long": {
                    "dall_e_size": "1792x1024",
                    "target_dimensions": [1920, 1080],
                    "font_size": 180,
                    "stroke_width": 8,
                    "top_padding_percent": 8,
                    "min_top_padding_px": 100
                },
                "short": {
                    "dall_e_size": "1024x1792",
                    "target_dimensions": [1080, 1920],
                    "font_size": 400,
                    "stroke_width": 12,
                    "top_padding_percent": 5,
                    "min_top_padding_px": 80
                },
                "common": {
                    "horizontal_padding_percent": 5,
                    "min_horizontal_padding_px": 40,
                    "font_resize_reduction": 0.95,
                    "max_font_resize_attempts": 10,
                    "download_max_retries": 5,
                    "download_timeout_seconds": 120,
                    "image_quality": 95,
                    "contrast_threshold": 3.0,
                    "stroke_padding_extra": 2
                }
            },
            "video_building": {
                "long": {
                    "chunk_size_seconds": 60,
                    "fps": 24,
                    "codec": "libx264",
                    "audio_codec": "aac",
                    "chunk_threads": 2,
                    "final_threads": 4,
                    "resolution": [1920, 1080]
                },
                "short": {
                    "fps": 24,
                    "codec": "libx264",
                    "audio_codec": "aac",
                    "threads": 4,
                    "resolution": [1080, 1920]
                }
            },
            "upload": {
                "window_minutes": 5,
                "buffer_hours": 1,
                "max_attempts": 3,
                "daemon_check_interval_seconds": 60
            },
            "quality_control": {
                "thresholds": {
                    "min_script_score": 7.0,
                    "min_video_score": 6.5,
                    "min_metadata_score": 7.0,
                    "min_overall_score": 7.0
                },
                "weights": {
                    "script_length": 2.0,
                    "title_quality": 1.5,
                    "visual_cues": 1.5,
                    "seo_completeness": 1.0,
                    "ypp_safety": 2.0,
                    "originality": 2.0
                }
            },
            "assets": {
                "max_scene_duration_seconds": 4.5,
                "safety_buffer": 1.15,
                "default_count": 40,
                "fallback_count": 50
            },
            "scheduler": {
                "jitter_minutes": [-10, 10],
                "buffer_hours": 2,
                "weekday_times": {
                    "monday": [20, 30],
                    "tuesday": [21, 0],
                    "wednesday": [21, 0],
                    "thursday": [21, 0],
                    "friday": [20, 0],
                    "saturday": [19, 0],
                    "sunday": [18, 30]
                }
            },
            "lifecycle": {
                "max_age_hours": 48,
                "cleanup_interval_hours": 6
            },
            "health": {
                "check_interval_hours": 1,
                "max_retries": 3,
                "stale_file_age_hours": 24,
                "cleanup_stale_files_age_hours": 48
            },
            "quota": {
                "daily_limit": 10000,
                "costs": {
                    "upload": 1600,
                    "comment": 50,
                    "update": 50,
                    "list": 1
                }
            },
            "validation": {
                "fps": {
                    "min": 23,
                    "max": 61
                },
                "min_duration_seconds": 0.2
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
    
    @property
    def topic_keywords(self) -> list:
        """Get topic keywords for content discovery."""
        # First try niche.topic_keywords (if exists in config)
        keywords = self.get("niche.topic_keywords", None)
        if keywords:
            return keywords
        
        # Fallback: derive from niche and common keywords
        niche = self.niche
        content_types = self.get("niche.content_types", [])
        example_topics = self.get("niche.example_topics", [])
        
        # Combine niche + content types as keywords
        derived_keywords = [niche] + content_types[:3]  # Max 4 keywords
        return derived_keywords if derived_keywords else ["General Topics"]
    
    # Thumbnail settings convenience properties
    @property
    def thumbnail_settings(self) -> dict:
        return self.get("thumbnails", {})
    
    # Video building settings convenience properties
    @property
    def video_building_settings(self) -> dict:
        return self.get("video_building", {})
    
    # Upload settings convenience properties
    @property
    def upload_settings(self) -> dict:
        return self.get("upload", {})
    
    # Quality control settings convenience properties
    @property
    def quality_control_settings(self) -> dict:
        return self.get("quality_control", {})
    
    # Asset settings convenience properties
    @property
    def asset_settings(self) -> dict:
        return self.get("assets", {})
    
    # Scheduler settings convenience properties
    @property
    def scheduler_settings(self) -> dict:
        return self.get("scheduler", {})
    
    # Lifecycle settings convenience properties
    @property
    def lifecycle_settings(self) -> dict:
        return self.get("lifecycle", {})
    
    # Health settings convenience properties
    @property
    def health_settings(self) -> dict:
        return self.get("health", {})
    
    # Quota settings convenience properties
    @property
    def quota_settings(self) -> dict:
        return self.get("quota", {})
    
    # Validation settings convenience properties
    @property
    def validation_settings(self) -> dict:
        return self.get("validation", {})



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
