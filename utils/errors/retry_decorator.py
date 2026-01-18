"""
Unified Retry Decorator with Exponential Backoff

Standardizes retry logic across all API calls
"""

import time
import logging
from functools import wraps
from typing import Callable, Type, Tuple, Optional
from enum import Enum


class RetryableError(Exception):
    """Base class for retryable errors"""
    pass


class NonRetryableError(Exception):
    """Base class for non-retryable errors"""
    pass


def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    timeout: Optional[float] = None
):
    """
    Decorator for retry logic with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for wait time
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        retryable_exceptions: Tuple of exception types to retry on
        timeout: Optional timeout in seconds (not implemented in decorator, use in function)
    
    Usage:
        @retry_with_backoff(max_retries=3, timeout=30)
        def my_api_call():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            delay = initial_delay
            
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                
                except retryable_exceptions as e:
                    retries += 1
                    
                    if retries > max_retries:
                        logging.error(
                            f"[Retry] {func.__name__} failed after {max_retries} attempts: {e}"
                        )
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(initial_delay * (backoff_factor ** (retries - 1)), max_delay)
                    
                    logging.warning(
                        f"[Retry] {func.__name__} attempt {retries}/{max_retries} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)
                
                except NonRetryableError as e:
                    # Don't retry on non-retryable errors
                    logging.error(f"[Retry] {func.__name__} non-retryable error: {e}")
                    raise
                
                except Exception as e:
                    # Check if it's a retryable HTTP error
                    error_str = str(e).lower()
                    if any(code in error_str for code in ['429', '500', '502', '503', '504']):
                        retries += 1
                        if retries > max_retries:
                            logging.error(
                                f"[Retry] {func.__name__} HTTP error after {max_retries} attempts: {e}"
                            )
                            raise
                        
                        delay = min(initial_delay * (backoff_factor ** (retries - 1)), max_delay)
                        logging.warning(
                            f"[Retry] {func.__name__} HTTP error (attempt {retries}/{max_retries}): {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                    else:
                        # Not retryable, raise immediately
                        raise
            
            # Should never reach here, but just in case
            raise Exception(f"{func.__name__} failed after {max_retries} retries")
        
        return wrapper
    return decorator


# Common retry configurations
retry_openai = retry_with_backoff(
    max_retries=3,
    backoff_factor=2.0,
    initial_delay=1.0,
    retryable_exceptions=(ConnectionError, TimeoutError, Exception)
)

retry_youtube = retry_with_backoff(
    max_retries=5,
    backoff_factor=2.0,
    initial_delay=2.0,
    max_delay=120.0,
    retryable_exceptions=(ConnectionError, TimeoutError, Exception)
)

retry_http = retry_with_backoff(
    max_retries=3,
    backoff_factor=2.0,
    initial_delay=1.0,
    retryable_exceptions=(ConnectionError, TimeoutError)
)
