"""
API Key Validator
Ensures all required API keys are present before pipeline starts
Prevents gradient-only videos due to missing credentials
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def validate_api_keys():
    """
    Validates all required API keys before pipeline execution.
    
    Prevents issues:
    - Gradient-only videos (missing Pixabay/DALL-E keys)
    - Runtime failures mid-pipeline
    - Wasted processing time
    
    Raises:
        Exception: If any required API key is missing
    """
    
    required_keys = {
        "OPENAI_API_KEY": {
            "service": "OpenAI (DALL-E 3 images + GPT-4)",
            "purpose": "Generate AI images and classify intent",
            "critical": True
        },
        "PIXABAY_API_KEY": {
            "service": "Pixabay (stock videos)",
            "purpose": "Fetch B-roll video footage",
            "critical": True
        }
    }
    
    optional_keys = {
        "YOUTUBE_CLIENT_SECRET_FILE": {
            "service": "YouTube Data API",
            "purpose": "Upload videos to YouTube",
            "critical": False
        }
    }
    
    missing_critical = []
    missing_optional = []
    
    # Check required keys
    for key, info in required_keys.items():
        value = os.getenv(key)
        if not value or value.strip() == "":
            missing_critical.append(f"  • {key}: {info['service']} - {info['purpose']}")
            logging.error(f"❌ Missing: {key}")
        else:
            logging.info(f"✅ Found: {key}")
    
    # Check optional keys
    for key, info in optional_keys.items():
        value = os.getenv(key)
        if not value:
            missing_optional.append(f"  • {key}: {info['service']} - {info['purpose']}")
            logging.warning(f"⚠️ Optional missing: {key}")
        else:
            logging.info(f"✅ Found: {key}")
    
    # Report results
    if missing_critical:
        error_msg = "\n❌ MISSING CRITICAL API KEYS:\n" + "\n".join(missing_critical)
        error_msg += "\n\n💡 Add these to your .env file to prevent:"
        error_msg += "\n  - Gradient-only videos"
        error_msg += "\n  - Pipeline failures"
        error_msg += "\n  - Low-quality output"
        raise Exception(error_msg)
    
    if missing_optional:
        warning_msg = "\n⚠️ MISSING OPTIONAL API KEYS:\n" + "\n".join(missing_optional)
        logging.warning(warning_msg)
    
    logging.info("✅ All critical API keys validated")
    return True


def validate_file_paths():
    """
    Validates critical file paths exist.
    """
    
    required_dirs = [
        "videos/temp",
        "channel",
        "assets/music"
    ]
    
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            logging.info(f"Created directory: {dir_path}")
    
    return True


if __name__ == "__main__":
    # Test validation
    logging.basicConfig(level=logging.INFO)
    
    try:
        validate_api_keys()
        validate_file_paths()
        print("\n✅ All validations passed!")
    except Exception as e:
        print(f"\n❌ Validation failed:\n{e}")
