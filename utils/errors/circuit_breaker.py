"""
Circuit Breaker Pattern - Prevents API cascade failures

Opens circuit after threshold failures, prevents further calls until recovery
"""

import time
import logging
from enum import Enum
from typing import Callable, Optional, Dict
from functools import wraps


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Circuit breaker implementation"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to track
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED
        self.success_count = 0  # For half-open state
    
    def call(self, func: Callable, *args, **kwargs):
        """
        Execute function with circuit breaker protection
        
        Args:
            func: Function to execute
            *args, **kwargs: Function arguments
        
        Returns:
            Function result
        
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time and \
               (time.time() - self.last_failure_time) >= self.recovery_timeout:
                logging.info(f"[CircuitBreaker] Attempting recovery for {func.__name__}")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise Exception(
                    f"Circuit breaker is OPEN for {func.__name__}. "
                    f"Too many failures. Retry after {self.recovery_timeout}s"
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            # Need 2 successes to close circuit
            if self.success_count >= 2:
                logging.info("[CircuitBreaker] Circuit CLOSED - service recovered")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
        else:
            # Reset failure count on success
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            # Failed during recovery, open again
            logging.warning("[CircuitBreaker] Recovery failed, opening circuit")
            self.state = CircuitState.OPEN
        elif self.failure_count >= self.failure_threshold:
            logging.error(
                f"[CircuitBreaker] Circuit OPENED after {self.failure_count} failures"
            )
            self.state = CircuitState.OPEN


# Global circuit breakers for different services
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(service_name: str, **kwargs) -> CircuitBreaker:
    """Get or create circuit breaker for a service"""
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = CircuitBreaker(**kwargs)
    return _circuit_breakers[service_name]


def circuit_breaker(service_name: str, **breaker_kwargs):
    """
    Decorator to add circuit breaker to a function
    
    Usage:
        @circuit_breaker("openai", failure_threshold=5)
        def my_api_call():
            ...
    """
    def decorator(func: Callable) -> Callable:
        breaker = get_circuit_breaker(service_name, **breaker_kwargs)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator
