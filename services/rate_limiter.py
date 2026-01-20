"""
YouTube API Rate Limiter & Retry Logic

Prevents quota exhaustion and handles transient failures gracefully.

YouTube API Quota Costs:
- Video upload: 1600 units
- Comment post: 50 units
- Daily quota: 10,000 units
- Max uploads/day: ~6 videos (if only uploading)
"""

import time
import logging
from functools import wraps
from datetime import datetime, timedelta


# Use persistent quota manager instead of in-memory tracking
try:
    from services.quota_manager import get_quota_manager, QuotaExceededError as PersistentQuotaError
    persistent_quota = get_quota_manager()
    USE_PERSISTENT_QUOTA = True
    logging.info("[RateLimiter] Using persistent quota tracking (SQLite)")
except ImportError:
    persistent_quota = None
    USE_PERSISTENT_QUOTA = False
    logging.warning("[RateLimiter] Persistent quota manager not available, using fallback")


class YouTubeRateLimiter:
    def __init__(self, daily_quota=None):
        from config.channel import channel_config
        quota_config = channel_config.get("quota", {})
        
        if daily_quota is None:
            self.daily_quota = quota_config.get("daily_limit", 10000)
        else:
            self.daily_quota = daily_quota
            
        if not USE_PERSISTENT_QUOTA:
            # Fallback to in-memory (not recommended for production)
            self.used_quota = 0
            self.reset_time = datetime.now() + timedelta(days=1)
        
        costs_config = quota_config.get("costs", {})
        self.quota_costs = {
            'upload': costs_config.get("upload", 1600),
            'comment': costs_config.get("comment", 50),
            'update': costs_config.get("update", 50),
            'list': costs_config.get("list", 1)
        }
    
    def check_quota(self, operation='upload'):
        """Check if operation would exceed quota"""
        if USE_PERSISTENT_QUOTA:
            try:
                return persistent_quota.check_available(operation, self.daily_quota)
            except PersistentQuotaError as e:
                raise QuotaExceededError(str(e))
        
        # Fallback logic (in-memory)
        cost = self.quota_costs.get(operation, 1)
        
        # Reset if new day
        if datetime.now() >= self.reset_time:
            self.used_quota = 0
            self.reset_time = datetime.now() + timedelta(days=1)
            logging.info("[Rate Limiter] Quota reset for new day")
        
        if self.used_quota + cost > self.daily_quota:
            remaining_hours = (self.reset_time - datetime.now()).total_seconds() / 3600
            raise QuotaExceededError(
                f"YouTube API quota would be exceeded. "
                f"Used: {self.used_quota}/{self.daily_quota}. "
                f"Resets in {remaining_hours:.1f} hours"
            )
        
        return True
    
    def consume(self, operation='upload'):
        """Consume quota for an operation"""
        cost = self.quota_costs.get(operation, 1)
        
        if USE_PERSISTENT_QUOTA:
            persistent_quota.record_usage(operation, cost)
        else:
            # Fallback
            self.used_quota += cost
            logging.info(f"[Rate Limiter] Used {cost} quota ({self.used_quota}/{self.daily_quota})")


class QuotaExceededError(Exception):
    """Raised when YouTube API quota is exhausted"""
    pass


# Global rate limiter instance
rate_limiter = YouTubeRateLimiter()


# Import retry logic from centralized utilities (no longer duplicate)
from utils.errors.retry_decorator import retry_with_backoff


if __name__ == "__main__":
    # Test
    limiter = YouTubeRateLimiter()
    
    print("Testing quota system:")
    print(f"Daily quota: {limiter.daily_quota}")
    
    # Simulate uploads
    for i in range(3):
        try:
            limiter.check_quota('upload')
            limiter.consume('upload')
            print(f"Upload {i+1}: OK ({limiter.used_quota} used)")
        except QuotaExceededError as e:
            print(f"Upload {i+1}: BLOCKED - {e}")
