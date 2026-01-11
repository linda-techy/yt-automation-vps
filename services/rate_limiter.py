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

class YouTubeRateLimiter:
    def __init__(self, daily_quota=10000):
        self.daily_quota = daily_quota
        self.used_quota = 0
        self.reset_time = datetime.now() + timedelta(days=1)
        self.quota_costs = {
            'upload': 1600,
            'comment': 50,
            'update': 50,
            'list': 1
        }
    
    def check_quota(self, operation='upload'):
        """Check if operation would exceed quota"""
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
        self.used_quota += cost
        logging.info(f"[Rate Limiter] Used {cost} quota ({self.used_quota}/{self.daily_quota})")


class QuotaExceededError(Exception):
    """Raised when YouTube API quota is exhausted"""
    pass


# Global rate limiter instance
rate_limiter = YouTubeRateLimiter()


def retry_with_backoff(max_retries=3, backoff_factor=2):
    """
    Decorator for retry logic with exponential backoff.
    
    Handles:
    - Network timeouts (ConnectionError, TimeoutError)
    - Rate limits (429)
    - Server errors (500, 503)
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for wait time (2 = exponential)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                
                except (ConnectionError, TimeoutError) as e:
                    retries += 1
                    if retries >= max_retries:
                        logging.error(f"[Retry] {func.__name__} failed after {max_retries} attempts: {e}")
                        raise
                    
                    wait_time = backoff_factor ** retries
                    logging.warning(
                        f"[Retry] {func.__name__} attempt {retries}/{max_retries} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                
                except QuotaExceededError:
                    # Don't retry on quota errors
                    logging.error(f"[Retry] {func.__name__} quota exceeded - no retry")
                    raise
                
                except Exception as e:
                    # Check if it's a retryable HTTP error
                    error_str = str(e).lower()
                    if any(code in error_str for code in ['429', '500', '503']):
                        retries += 1
                        if retries >= max_retries:
                            logging.error(f"[Retry] {func.__name__} failed after {max_retries} attempts: {e}")
                            raise
                        
                        wait_time = backoff_factor ** retries
                        logging.warning(
                            f"[Retry] {func.__name__} HTTP error (attempt {retries}/{max_retries}): {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)
                    else:
                        # Not retryable, raise immediately
                        raise
            
            return None
        return wrapper
    return decorator


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
