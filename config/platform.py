"""
Cross-Platform Configuration for YouTube Automation

Auto-detects OS and provides correct paths for:
- FFmpeg
- ImageMagick
- Fonts (Malayalam-compatible)
"""

import os
import platform
import shutil


def get_os():
    """Detect operating system"""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "linux":
        return "linux"
    elif system == "darwin":
        return "macos"
    return "unknown"


def get_ffmpeg_path():
    """
    Get FFmpeg binary path based on OS.
    Returns directory containing ffmpeg executable.
    """
    os_type = get_os()
    
    if os_type == "windows":
        # Check common Windows locations
        windows_paths = [
            r"C:\Users\linda\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin",
            r"C:\ffmpeg\bin",
            r"C:\Program Files\ffmpeg\bin",
        ]
        for path in windows_paths:
            if os.path.exists(path):
                return path
    
    elif os_type == "linux":
        # On Linux, ffmpeg is usually in PATH
        if shutil.which("ffmpeg"):
            return os.path.dirname(shutil.which("ffmpeg"))
        # Common Linux locations
        linux_paths = [
            "/usr/bin",
            "/usr/local/bin",
        ]
        for path in linux_paths:
            if os.path.exists(os.path.join(path, "ffmpeg")):
                return path
    
    # Final fallback - let system find it
    return None


def get_imagemagick_binary():
    """
    Get ImageMagick binary path based on OS.
    Returns full path to convert/magick executable.
    """
    os_type = get_os()
    
    if os_type == "windows":
        windows_paths = [
            r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-7.1.0-Q16-HDRI\magick.exe",
        ]
        for path in windows_paths:
            if os.path.exists(path):
                return path
    
    elif os_type == "linux":
        # On Linux, ImageMagick uses 'convert' command
        if shutil.which("convert"):
            return shutil.which("convert")
        linux_paths = [
            "/usr/bin/convert",
            "/usr/local/bin/convert",
        ]
        for path in linux_paths:
            if os.path.exists(path):
                return path
    
    return None


def get_malayalam_font():
    """
    Get a font path that supports Malayalam script.
    Prioritizes Malayalam-specific fonts, falls back to Unicode fonts.
    """
    os_type = get_os()
    
    if os_type == "windows":
        font_paths = [
            r"C:\Windows\Fonts\NirmalaUI.ttf",
            r"C:\Windows\Fonts\NirmalaUI-Bold.ttf",
            r"C:\Windows\Fonts\Nirmala.ttf",
            r"C:\Windows\Fonts\Arial.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
        ]
    elif os_type == "linux":
        font_paths = [
            # Noto fonts - best for Malayalam
            "/usr/share/fonts/truetype/noto/NotoSansMalayalam-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansMalayalam-Bold.ttf",
            "/usr/share/fonts/noto/NotoSansMalayalam-Regular.ttf",
            # Fallback Unicode fonts
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            # Lohit Malayalam
            "/usr/share/fonts/truetype/lohit-malayalam/Lohit-Malayalam.ttf",
        ]
    else:
        font_paths = []
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            print(f"[Platform] Font: {os.path.basename(font_path)}")
            return font_path
    
    # Last resort - use font name and let ImageMagick find it
    print("[Platform] WARNING: No specific font found, using 'DejaVu-Sans'")
    return "DejaVu-Sans"


def configure_environment():
    """
    Configure environment variables for cross-platform compatibility.
    Call this at the start of pipeline.py
    """
    os_type = get_os()
    print(f"[Platform] Detected OS: {os_type}")
    
    # Configure FFmpeg
    ffmpeg_path = get_ffmpeg_path()
    if ffmpeg_path:
        os.environ["PATH"] = ffmpeg_path + os.pathsep + os.environ.get("PATH", "")
        print(f"[Platform] FFmpeg: {ffmpeg_path}")
    else:
        print("[Platform] WARNING: FFmpeg not found in expected locations")
    
    # Configure ImageMagick for MoviePy
    imagemagick_binary = get_imagemagick_binary()
    if imagemagick_binary:
        try:
            import moviepy.config as mp_config
            mp_config.change_settings({"IMAGEMAGICK_BINARY": imagemagick_binary})
            print(f"[Platform] ImageMagick: {imagemagick_binary}")
        except Exception as e:
            print(f"[Platform] ImageMagick config failed: {e}")
    else:
        print("[Platform] WARNING: ImageMagick not found")
    
    return {
        "os": os_type,
        "ffmpeg_path": ffmpeg_path,
        "imagemagick_binary": imagemagick_binary,
        "malayalam_font": get_malayalam_font()
    }


if __name__ == "__main__":
    print("Platform Configuration Test")
    print("=" * 40)
    config = configure_environment()
    print(f"\nConfiguration: {config}")
