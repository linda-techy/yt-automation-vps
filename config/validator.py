"""
Configuration Validator

Validates channel_config.yaml structure and values to prevent runtime errors.
"""

import os
import logging
from typing import Dict, Any, List
from config.channel import channel_config


class ConfigValidator:
    """Validates channel configuration"""
    
    REQUIRED_FIELDS = [
        "channel.name",
        "channel.language",
        "niche.primary",
        "audio.voice_id",
        "schedule.timezone",
        "schedule.upload_time"
    ]
    
    OPTIONAL_FIELDS = [
        "channel.handle",
        "channel.country",
        "niche.excluded_topics",
        "audio.background_music.enabled",
        "formats.long_form.enabled",
        "formats.shorts.enabled"
    ]
    
    @staticmethod
    def validate() -> Dict[str, Any]:
        """
        Validate channel configuration.
        
        Returns:
            dict with validation results:
            {
                "valid": bool,
                "errors": List[str],
                "warnings": List[str]
            }
        """
        errors = []
        warnings = []
        
        # Check required fields
        for field in ConfigValidator.REQUIRED_FIELDS:
            value = channel_config.get(field)
            if value is None:
                errors.append(f"Missing required field: {field}")
            elif isinstance(value, str) and not value.strip():
                errors.append(f"Empty required field: {field}")
        
        # Validate field types and ranges
        try:
            # Validate timezone
            timezone = channel_config.get("schedule.timezone")
            if timezone:
                import pytz
                try:
                    pytz.timezone(timezone)
                except pytz.exceptions.UnknownTimeZoneError:
                    errors.append(f"Invalid timezone: {timezone}")
            
            # Validate upload_time format (HH:MM)
            upload_time = channel_config.get("schedule.upload_time")
            if upload_time:
                try:
                    parts = upload_time.split(":")
                    if len(parts) != 2:
                        raise ValueError("Invalid format")
                    hour, minute = int(parts[0]), int(parts[1])
                    if not (0 <= hour < 24 and 0 <= minute < 60):
                        raise ValueError("Out of range")
                except (ValueError, IndexError):
                    errors.append(f"Invalid upload_time format: {upload_time} (expected HH:MM)")
            
            # Validate BGM volume (0.0-1.0)
            bgm_volume = channel_config.get("audio.background_music.volume")
            if bgm_volume is not None:
                try:
                    volume = float(bgm_volume)
                    if not (0.0 <= volume <= 1.0):
                        warnings.append(f"BGM volume out of recommended range: {volume} (should be 0.0-1.0)")
                except (ValueError, TypeError):
                    errors.append(f"Invalid BGM volume: {bgm_volume} (must be number)")
            
            # Validate language code format
            language_code = channel_config.get("audio.language_code")
            if language_code:
                # Basic format check: should be like "en-US" or "ml-IN"
                if "-" not in language_code or len(language_code.split("-")) != 2:
                    warnings.append(f"Language code format unusual: {language_code} (expected format: ll-CC)")
            
            # Validate video formats
            long_enabled = channel_config.get("formats.long_form.enabled", True)
            shorts_enabled = channel_config.get("formats.shorts.enabled", True)
            if not long_enabled and not shorts_enabled:
                errors.append("Both long_form and shorts are disabled. At least one must be enabled.")
            
            # Validate duration ranges
            long_duration = channel_config.get("formats.long_form.duration_minutes")
            if long_duration:
                try:
                    duration = float(long_duration)
                    if duration < 1 or duration > 60:
                        warnings.append(f"Long form duration unusual: {duration} minutes (typical: 5-15 minutes)")
                except (ValueError, TypeError):
                    errors.append(f"Invalid long_form duration: {long_duration}")
            
            shorts_duration = channel_config.get("formats.shorts.duration_seconds")
            if shorts_duration:
                try:
                    duration = float(shorts_duration)
                    if duration < 15 or duration > 60:
                        warnings.append(f"Shorts duration unusual: {duration} seconds (typical: 30-60 seconds)")
                except (ValueError, TypeError):
                    errors.append(f"Invalid shorts duration: {shorts_duration}")
            
            # Validate thumbnail settings
            thumbnails = channel_config.get("thumbnails", {})
            if thumbnails:
                long_font = thumbnails.get("long", {}).get("font_size")
                if long_font and (long_font < 50 or long_font > 300):
                    warnings.append(f"Long thumbnail font size unusual: {long_font}px")
                
                short_font = thumbnails.get("short", {}).get("font_size")
                if short_font and (short_font < 100 or short_font > 600):
                    warnings.append(f"Short thumbnail font size unusual: {short_font}px")
            
            # Validate video building settings
            video_building = channel_config.get("video_building", {})
            if video_building:
                long_fps = video_building.get("long", {}).get("fps")
                if long_fps and (long_fps < 15 or long_fps > 60):
                    warnings.append(f"Long video FPS unusual: {long_fps} (typical: 24-30)")
            
            # Validate quality control thresholds
            qc = channel_config.get("quality_control", {})
            if qc:
                thresholds = qc.get("thresholds", {})
                for key, value in thresholds.items():
                    if isinstance(value, (int, float)) and (value < 0 or value > 10):
                        warnings.append(f"Quality control threshold {key} out of range: {value} (expected 0-10)")
            
            # Validate quota settings
            quota = channel_config.get("quota", {})
            if quota:
                daily_limit = quota.get("daily_limit")
                if daily_limit and daily_limit != 10000:
                    warnings.append(f"Daily quota limit changed from default: {daily_limit} (default: 10000)")
        
        except Exception as e:
            errors.append(f"Validation error: {e}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    @staticmethod
    def validate_and_raise():
        """
        Validate configuration and raise exception if invalid.
        
        Raises:
            ValueError: If configuration is invalid
        """
        result = ConfigValidator.validate()
        
        if result["warnings"]:
            for warning in result["warnings"]:
                logging.warning(f"[Config Validation] {warning}")
        
        if not result["valid"]:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in result["errors"])
            logging.error(f"[Config Validation] {error_msg}")
            raise ValueError(error_msg)
        
        logging.info("[Config Validation] Configuration valid")


if __name__ == "__main__":
    # Test validation
    result = ConfigValidator.validate()
    print("Configuration Validation Results:")
    print(f"Valid: {result['valid']}")
    if result["errors"]:
        print("Errors:")
        for error in result["errors"]:
            print(f"  - {error}")
    if result["warnings"]:
        print("Warnings:")
        for warning in result["warnings"]:
            print(f"  - {warning}")
