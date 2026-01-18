"""
Execution Tracer - Trace IDs for request tracking

Provides trace IDs for each pipeline run to track execution across services
"""

import uuid
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
from datetime import datetime


class ExecutionTracer:
    """Manages trace IDs for execution tracking"""
    
    _current_trace_id: Optional[str] = None
    
    @classmethod
    def generate_trace_id(cls) -> str:
        """Generate new trace ID"""
        return f"trace_{uuid.uuid4().hex[:12]}_{int(datetime.now().timestamp())}"
    
    @classmethod
    def set_trace_id(cls, trace_id: Optional[str] = None) -> str:
        """Set current trace ID (generates if None)"""
        if trace_id is None:
            trace_id = cls.generate_trace_id()
        cls._current_trace_id = trace_id
        return trace_id
    
    @classmethod
    def get_trace_id(cls) -> Optional[str]:
        """Get current trace ID"""
        return cls._current_trace_id
    
    @classmethod
    def clear_trace_id(cls):
        """Clear current trace ID"""
        cls._current_trace_id = None
    
    @classmethod
    @contextmanager
    def trace_context(cls, trace_id: Optional[str] = None):
        """Context manager for trace ID"""
        old_trace_id = cls._current_trace_id
        new_trace_id = cls.set_trace_id(trace_id)
        try:
            logging.info(f"[Trace] Started execution: {new_trace_id}")
            yield new_trace_id
        finally:
            cls._current_trace_id = old_trace_id
            if old_trace_id:
                logging.debug(f"[Trace] Restored trace ID: {old_trace_id}")
    
    @classmethod
    def log_with_trace(cls, level: str, message: str, **kwargs):
        """Log message with trace ID"""
        trace_id = cls.get_trace_id()
        if trace_id:
            message = f"[Trace:{trace_id}] {message}"
        
        log_func = getattr(logging, level.lower(), logging.info)
        log_func(message, **kwargs)


# Global tracer instance
tracer = ExecutionTracer()
