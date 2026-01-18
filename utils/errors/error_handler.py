"""
Centralized Error Handler - Unified error handling and logging
"""

import logging
import traceback
from typing import Optional, Dict, Any
from datetime import datetime


class ErrorHandler:
    """Centralized error handling"""
    
    @staticmethod
    def handle_error(
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        operation: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle error with structured logging
        
        Args:
            error: Exception that occurred
            context: Additional context about the error
            operation: Name of operation that failed
            trace_id: Trace ID for request tracking
        
        Returns:
            Error information dictionary
        """
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "operation": operation,
            "trace_id": trace_id,
            "context": context or {},
            "traceback": traceback.format_exc()
        }
        
        # Log error
        log_msg = f"[Error] {operation or 'Unknown'}"
        if trace_id:
            log_msg += f" [Trace:{trace_id}]"
        log_msg += f": {error_info['error_type']} - {error_info['error_message']}"
        
        logging.error(log_msg)
        logging.debug(f"Error context: {error_info}")
        
        return error_info
    
    @staticmethod
    def is_retryable(error: Exception) -> bool:
        """Check if error is retryable"""
        error_str = str(error).lower()
        retryable_patterns = [
            'timeout', 'connection', '429', '500', '502', '503', '504',
            'rate limit', 'temporary', 'unavailable'
        ]
        return any(pattern in error_str for pattern in retryable_patterns)
    
    @staticmethod
    def is_quota_error(error: Exception) -> bool:
        """Check if error is quota-related"""
        error_str = str(error).lower()
        quota_patterns = ['quota', '403', 'exceeded', 'limit reached']
        return any(pattern in error_str for pattern in quota_patterns)


# Global error handler instance
error_handler = ErrorHandler()
