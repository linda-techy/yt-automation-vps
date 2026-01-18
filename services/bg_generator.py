"""
Hybrid Background Generator - AI + Stock Video
DALL-E 3 for key scenes, Pixabay for B-roll

KEY SCENES (AI Generated - Perfect Script Match):
- Hook (first impression)
- Turning Point (key moment)  
- Outro (memorable ending)

B-ROLL (Stock Video):
- All other scenes use high-quality Pixabay footage
"""

import os
import requests
import random
import concurrent.futures
import time
import logging
from openai import OpenAI

# API Keys
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def generate_ai_image(prompt, output_path, size="1792x1024"):
    """
    Generate a single image using DALL-E 3.
    Used for key scenes that need perfect script alignment.
    
    Args:
        prompt: Descriptive prompt for the image
        output_path: Where to save the generated image
        size: Image size (1792x1024 for landscape, 1024x1792 for portrait)
    
    Returns:
        Path to saved image or None if failed
    """
    if not openai_client:
        raise Exception("OPENAI_API_KEY not found - required for AI image generation")
    
    try:
        logging.info(f"[AI] Generating: '{prompt[:50]}...'")
        
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=f"Cinematic 4K film still, highly detailed, professional lighting: {prompt}",
            size=size,
            quality="hd",
            n=1
        )
        
        image_url = response.data[0].url
        
        # Download and save
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        img_response = requests.get(image_url, timeout=30)
        img_response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(img_response.content)
        
        logging.info(f"[AI] Generated: {os.path.basename(output_path)}")
        return output_path
        
    except Exception as e:
        logging.error(f"[AI] Error: {e}")
        raise


def generate_fallback_asset(query, index, orientation="portrait"):
    """
    Generate a fallback solid color asset when DALL-E/Pixabay fails.
    
    Args:
        query: Visual cue query (for color selection)
        index: Asset index
        orientation: 'portrait' or 'landscape'
    
    Returns:
        Path to generated fallback image, or None if generation fails
    """
    try:
        # Use PIL to create solid color image
        try:
            from PIL import Image
        except ImportError:
            logging.warning("[Hybrid] PIL not available, cannot generate fallback asset")
            return None
        
        # Determine dimensions based on orientation
        if orientation == "portrait":
            width, height = 1080, 1920
        else:
            width, height = 1920, 1080
        
        # Generate a gradient-like color based on query hash
        import hashlib
        hash_val = int(hashlib.md5(query.encode()).hexdigest()[:8], 16)
        
        # Create color palette (avoid pure black/white)
        r = (hash_val % 156) + 50  # 50-205
        g = ((hash_val // 256) % 156) + 50
        b = ((hash_val // 65536) % 156) + 50
        
        # Create solid color image
        img = Image.new('RGB', (width, height), color=(r, g, b))
        
        # Save to temp directory
        os.makedirs("videos/temp", exist_ok=True)
        fallback_path = f"videos/temp/fallback_{index}_{random.randint(1000,9999)}.png"
        img.save(fallback_path)
        
        logging.info(f"[Hybrid] Generated fallback asset: {fallback_path} (color: RGB({r},{g},{b}))")
        return fallback_path
        
    except Exception as e:
        logging.error(f"[Hybrid] Fallback asset generation failed: {e}")
        return None


def fetch_pixabay_video(query, index, orientation="portrait"):
    """
    Fetch a single video from Pixabay.
    
    Args:
        query: Search term
        index: Asset index
        orientation: 'portrait' or 'landscape'
    
    Returns:
        Tuple of (index, path) or (index, None)
    """
    if not PIXABAY_API_KEY:
        raise Exception("PIXABAY_API_KEY not found")
    
    try:
        # Clean search query
        stop_words = ["a", "an", "the", "in", "on", "at", "with", "of", "and", "cinematic", "abstract", "4k"]
        keywords = [word for word in query.split() if word.lower() not in stop_words and len(word) > 2]
        clean_query = " ".join(keywords[:4]) if keywords else "technology"
        
        logging.info(f"[Pixabay] Fetching: '{clean_query[:40]}' ({orientation})")
        
        url = "https://pixabay.com/api/videos/"
        params = {
            "key": PIXABAY_API_KEY,
            "q": clean_query,
            "video_type": "film",
            "per_page": 10,
            "safesearch": "true",
            "min_width": 1080
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Try generic search if no results
        if not data.get('hits'):
            params["q"] = "technology motion"
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
        
        if data.get('hits'):
            video = random.choice(data['hits'][:5])
            videos = video.get('videos', {})
            
            video_url = None
            if 'large' in videos and videos['large'].get('url'):
                video_url = videos['large']['url']
            elif 'medium' in videos and videos['medium'].get('url'):
                video_url = videos['medium']['url']
            
            if video_url:
                path = f"videos/temp/pixabay_{index}_{random.randint(1000,9999)}.mp4"
                os.makedirs(os.path.dirname(path), exist_ok=True)
                
                for attempt in range(3):
                    try:
                        r = requests.get(video_url, stream=True, timeout=60)
                        r.raise_for_status()
                        with open(path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=1024*1024):
                                if chunk:
                                    f.write(chunk)
                        return (index, path)
                    except Exception as e:
                        if attempt < 2:
                            time.sleep(2 ** attempt)
                        else:
                            raise
        
        return (index, None)
        
    except Exception as e:
        logging.warning(f"[Pixabay] Error for query '{query[:30]}': {type(e).__name__}")
        return (index, None)


def fetch_background_videos(visual_cues, orientation="portrait", key_scene_indices=None):
    """
    HYBRID: Fetches visuals using AI for key scenes, Pixabay for B-roll.
    
    Args:
        visual_cues: List of search queries/prompts
        orientation: 'portrait' (Shorts) or 'landscape' (Long-Form)
        key_scene_indices: Indices that should use AI generation (default: first, middle, last)
    
    Returns:
        List of local file paths (videos and images)
    """
    if not PIXABAY_API_KEY:
        raise Exception("PIXABAY_API_KEY not found. Get free key at https://pixabay.com/api/docs/")
    
    # Determine key scene indices if not provided
    # Key scenes: Hook (first 3), Turning Point (middle 3), Outro (last 3)
    if key_scene_indices is None:
        n = len(visual_cues)
        middle = n // 2
        key_scene_indices = set(
            list(range(0, min(3, n))) +  # First 3 (Hook)
            list(range(max(0, middle-1), min(n, middle+2))) +  # Middle 3 (Turning Point)
            list(range(max(0, n-3), n))  # Last 3 (Outro)
        )
    
    # Determine AI image size based on orientation
    ai_size = "1024x1792" if orientation == "portrait" else "1792x1024"
    
    final_paths = [None] * len(visual_cues)
    
    # Step 1: Generate AI images for key scenes (sequential to manage API rate)
    logging.info(f"[Hybrid] Generating AI images for {len(key_scene_indices)} key scenes...")
    for idx in sorted(key_scene_indices):
        if idx < len(visual_cues):
            try:
                cue = visual_cues[idx]
                output_path = f"videos/temp/ai_scene_{idx}_{random.randint(1000,9999)}.png"
                path = generate_ai_image(cue, output_path, size=ai_size)
                final_paths[idx] = path
            except Exception as e:
                logging.warning(f"[Hybrid] AI fallback to Pixabay for index {idx}: {e}")
                # Will be filled by Pixabay below
    
    # Step 2: Fetch Pixabay videos for remaining scenes (parallel)
    pixabay_indices = [i for i in range(len(visual_cues)) if final_paths[i] is None]
    logging.info(f"[Hybrid] Fetching {len(pixabay_indices)} Pixabay videos for B-roll...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(fetch_pixabay_video, visual_cues[i], i, orientation) 
            for i in pixabay_indices
        ]
        for future in concurrent.futures.as_completed(futures):
            idx, path = future.result()
            if path:
                final_paths[idx] = path
    
    # Check for missing assets and apply fallbacks
    missing = [i for i, p in enumerate(final_paths) if p is None]
    if missing:
        logging.warning(f"[Hybrid] Missing assets at indices: {missing}, generating fallbacks")
        for idx in missing:
            try:
                # Try to generate fallback asset (solid color placeholder)
                fallback_path = generate_fallback_asset(
                    visual_cues[idx] if idx < len(visual_cues) else "abstract motion",
                    idx,
                    orientation
                )
                if fallback_path and os.path.exists(fallback_path):
                    final_paths[idx] = fallback_path
                    logging.info(f"[Hybrid] Generated fallback asset for index {idx}: {fallback_path}")
                else:
                    logging.error(f"[Hybrid] Fallback generation failed for index {idx}")
            except Exception as e:
                logging.error(f"[Hybrid] Fallback failed for index {idx}: {e}")
        
        # Final check - if still missing, raise error (should be rare with fallbacks)
        still_missing = [i for i, p in enumerate(final_paths) if p is None]
        if still_missing:
            raise Exception(f"[Hybrid] Critical: Failed to generate assets at indices: {still_missing} even after fallbacks")
    
    ai_count = len([p for p in final_paths if p and 'ai_scene_' in p])
    video_count = len([p for p in final_paths if p and 'pixabay_' in p])
    fallback_count = len([p for p in final_paths if p and 'fallback_' in p])
    logging.info(f"[Hybrid] Complete: {ai_count} AI images + {video_count} Pixabay videos" + 
                 (f" + {fallback_count} fallbacks" if fallback_count > 0 else ""))
    
    return final_paths


# Alias for backward compatibility
generate_background_images = fetch_background_videos


# ========== AUDIO-DRIVEN VISUAL INTELLIGENCE HELPERS ==========

def search_pixabay_videos(query, min_duration=10, max_duration=40):
    """
    Semantic Pixabay video search for audio-driven visuals.
    
    Args:
        query: Semantic search query (e.g., "Indian man confused thinking")
        min_duration: Minimum video duration in seconds
        max_duration: Maximum video duration in seconds
    
    Returns:
        List of video URLs matching criteria
    """
    
    if not PIXABAY_API_KEY:
        logging.warning("No Pixabay API key, cannot search videos")
        return []
    
    url = "https://pixabay.com/api/videos/"
    params = {
        "key": PIXABAY_API_KEY,
        "q": query,
        "per_page": 10,
        "video_type": "film",  # Prefer authentic footage
        "min_width": 1920,
        "min_height": 1080
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        videos = []
        for hit in data.get("hits", []):
            for video_data in hit.get("videos", {}).values():
                duration = video_data.get("duration", 0)
                if min_duration <= duration <= max_duration:
                    videos.append({
                        "url": video_data.get("url"),
                        "duration": duration,
                        "width": video_data.get("width"),
                        "height": video_data.get("height")
                    })
        
        return videos
        
    except Exception as e:
        logging.error(f"Pixabay video search failed: {e}")
        return []


def generate_dalle_image(prompt, size="1024x1024", quality="standard"):
    """
    Controlled DALL-E image generation for educational visuals.
    
    Args:
        prompt: Educational prompt (minimal, clear, no artistic elements)
        size: Image size (1024x1024, 1792x1024, 1024x1792)
        quality: "standard" or "hd"
    
    Returns:
        URL of generated image
    """
    
    if not openai_client:
        raise Exception("OpenAI client not initialized")
    
    try:
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality=quality,
            n=1
        )
        
        return response.data[0].url
        
    except Exception as e:
        logging.error(f"DALL-E generation failed: {e}")
        raise


if __name__ == "__main__":
    # Test
    test_cues = ["robot hand", "AI technology", "futuristic city"]
    try:
        paths = fetch_background_videos(test_cues, orientation="landscape", key_scene_indices={0, 2})
        print(f"Downloaded: {paths}")
    except Exception as e:
        print(f"Test failed: {e}")
