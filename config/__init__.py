# Configuration module for YouTube Automation
# Contains platform-specific settings

from .platform import (
    get_os,
    get_ffmpeg_path,
    get_imagemagick_binary,
    get_malayalam_font,
    configure_environment
)
