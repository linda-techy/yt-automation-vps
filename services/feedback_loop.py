"""
Feedback Loop - Analytics & Learning Engine

Closes the loop between "Upload" and "Planning".
1. Fetches recent video performance (CTR, Retention).
2. Updates 'config/brain_weights.json' to adjust future script generation.
3. Identifies winning formats/hooks.
"""

import os
import json
import logging

ANALYTICS_CACHE = "channel/analytics_cache.json"
WEIGHTS_FILE = "config/brain_weights.json"

def fetch_recent_performance(max_results=10):
    """
    Fetches performance stats for recent videos.
    Returns list of dicts: {video_id, title, ctr, avd_percent, views}
    """
    # TODO: Implement real YouTube Analytics API call.
    # For now, we check `channel/upload_history.json` and simulate/placeholder.
    
    history_file = "channel/upload_history.json"
    if not os.path.exists(history_file):
        logging.debug("[FeedbackLoop] No upload history file found")
        return []
    
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
        
        # In a real scenario, we would query the API for these IDs.
        # Here we just return the history metadata.
        return history[-max_results:] if isinstance(history, list) else []
    except Exception as e:
        logging.error(f"[FeedbackLoop] Failed to read upload history: {e}")
        return []

def analyze_performance_trends():
    """
    Analyzes recent videos to find what's working.
    Updates brain_weights.json
    """
    videos = fetch_recent_performance()
    if not videos:
        logging.info("[FeedbackLoop] No video history to analyze.")
        return

    # Simulation logic for "Learning"
    # If we had real CTR data:
    # high_ctr_videos = [v for v in videos if v.get('ctr', 0) > 0.08]
    # common_keywords = extract_keywords(high_ctr_videos)
    
    # For now, we will just log that we ran.
    logging.info(f"[FeedbackLoop] Analyzed {len(videos)} recent videos.")
    
    # Example: Update weights (mock)
    current_weights = {
        "humor_level": 0.5,
        "pacing_speed": 1.0, 
        "hook_aggression": 0.7
    }
    
    # Logic: If recent views are low, increase 'hook_aggression'
    # This is a placeholder for the real logic.
    
    # Ensure directory exists before writing
    os.makedirs(os.path.dirname(WEIGHTS_FILE), exist_ok=True)
    
    try:
        with open(WEIGHTS_FILE, "w", encoding="utf-8") as f:
            json.dump(current_weights, f, indent=2)
        logging.info(f"[FeedbackLoop] Updated brain weights: {current_weights}")
    except Exception as e:
        logging.error(f"[FeedbackLoop] Failed to write weights file: {e}")

def get_feedback_adjustments():
    """Run by Script Agent to get current tuning parameters."""
    try:
        if os.path.exists(WEIGHTS_FILE):
            with open(WEIGHTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logging.warning(f"[FeedbackLoop] Failed to load weights: {e}")
    
    return {}  # Return empty dict if file doesn't exist or fails to load
    
if __name__ == "__main__":
    analyze_performance_trends()
