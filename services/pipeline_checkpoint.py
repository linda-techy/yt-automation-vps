"""
Pipeline Checkpoint System

Saves pipeline state after each major step to enable resume on crash.
"""

import os
import json
import logging
import datetime
from typing import Dict, Any, Optional

CHECKPOINT_FILE = "channel/pipeline_checkpoint.json"
from utils.file_locking import load_json_safe, save_json_safe


class PipelineCheckpoint:
    """Manages pipeline checkpoint state"""
    
    @staticmethod
    def save_checkpoint(step: str, data: Dict[str, Any]) -> bool:
        """
        Save checkpoint after completing a step.
        
        Args:
            step: Step name (e.g., "topic_generated", "script_generated", "long_video_built")
            data: Data to save for this step
        
        Returns:
            True if successful
        """
        checkpoint = {
            "step": step,
            "timestamp": datetime.datetime.now().isoformat(),
            "data": data
        }
        
        success = save_json_safe(CHECKPOINT_FILE, checkpoint)
        if success:
            logging.info(f"[Checkpoint] Saved checkpoint: {step}")
        else:
            logging.error(f"[Checkpoint] Failed to save checkpoint: {step}")
        
        return success
    
    @staticmethod
    def load_checkpoint() -> Optional[Dict[str, Any]]:
        """
        Load last checkpoint.
        
        Returns:
            Checkpoint data or None if no checkpoint exists
        """
        checkpoint = load_json_safe(CHECKPOINT_FILE, default=None)
        if checkpoint:
            logging.info(f"[Checkpoint] Loaded checkpoint: {checkpoint.get('step')}")
        return checkpoint
    
    @staticmethod
    def clear_checkpoint() -> bool:
        """Clear checkpoint (call after successful pipeline completion)"""
        try:
            if os.path.exists(CHECKPOINT_FILE):
                os.remove(CHECKPOINT_FILE)
                logging.info("[Checkpoint] Cleared checkpoint")
            return True
        except Exception as e:
            logging.error(f"[Checkpoint] Failed to clear checkpoint: {e}")
            return False
    
    @staticmethod
    def should_resume() -> bool:
        """
        Check if pipeline should resume from checkpoint.
        
        Returns:
            True if checkpoint exists and is recent (< 24 hours old)
        """
        checkpoint = PipelineCheckpoint.load_checkpoint()
        if not checkpoint:
            return False
        
        try:
            timestamp_str = checkpoint.get("timestamp")
            if not timestamp_str:
                return False
            
            checkpoint_time = datetime.datetime.fromisoformat(timestamp_str)
            age_hours = (datetime.datetime.now() - checkpoint_time).total_seconds() / 3600
            
            # Only resume if checkpoint is less than 24 hours old
            if age_hours < 24:
                logging.info(f"[Checkpoint] Found recent checkpoint ({age_hours:.1f}h old), can resume")
                return True
            else:
                logging.warning(f"[Checkpoint] Checkpoint too old ({age_hours:.1f}h), clearing")
                PipelineCheckpoint.clear_checkpoint()
                return False
        except Exception as e:
            logging.error(f"[Checkpoint] Error checking checkpoint age: {e}")
            return False
