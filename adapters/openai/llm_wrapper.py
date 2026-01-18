"""
OpenAI LLM Wrapper - Standardized LLM calls with error handling

Wraps LangChain ChatOpenAI with:
- Timeout
- Retry logic
- Circuit breaker
- Context compression
- Trace IDs
"""

import logging
from typing import Optional, List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, BaseMessage

from utils.errors.retry_decorator import retry_openai
from utils.errors.circuit_breaker import circuit_breaker, get_circuit_breaker
from utils.errors.error_handler import error_handler
from utils.logging.tracer import tracer
from utils.prompts.compressor import compressor


class WrappedChatOpenAI:
    """ChatOpenAI wrapper with production-ready error handling"""
    
    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.7,
        timeout: float = 60.0,
        max_retries: int = 3
    ):
        """
        Initialize wrapped LLM
        
        Args:
            model: Model name (gpt-4o, gpt-4o-mini, etc.)
            temperature: Sampling temperature
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize underlying LLM with timeout
        self.llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            timeout=timeout,
            max_retries=0  # We handle retries ourselves
        )
        
        # Get circuit breaker for this model
        self.circuit_breaker = get_circuit_breaker(
            f"openai_{model}",
            failure_threshold=5,
            recovery_timeout=60.0
        )
    
    @retry_openai
    def invoke(
        self,
        messages: List[BaseMessage],
        compress_context: bool = True,
        trace_id: Optional[str] = None
    ) -> Any:
        """
        Invoke LLM with error handling
        
        Args:
            messages: List of messages
            compress_context: Whether to compress context in messages
            trace_id: Optional trace ID for logging
        
        Returns:
            LLM response
        """
        if trace_id is None:
            trace_id = tracer.get_trace_id()
        
        try:
            # Compress context if requested
            if compress_context:
                messages = self._compress_messages(messages)
            
            # Log request
            if trace_id:
                logging.debug(f"[LLM:{self.model}] Invoking with trace {trace_id}")
            
            # Use circuit breaker
            response = self.circuit_breaker.call(
                self._invoke_internal,
                messages
            )
            
            return response
        
        except Exception as e:
            error_handler.handle_error(
                e,
                context={"model": self.model, "message_count": len(messages)},
                operation=f"llm_invoke_{self.model}",
                trace_id=trace_id
            )
            raise
    
    def _invoke_internal(self, messages: List[BaseMessage]) -> Any:
        """Internal invoke without circuit breaker (called by circuit breaker)"""
        return self.llm.invoke(messages)
    
    def _compress_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Compress context in messages to reduce token usage"""
        compressed = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                content = msg.content
                # If content is very long, try to compress it
                if len(content) > 1000:
                    # Try to extract and compress JSON if present
                    if "{" in content and "}" in content:
                        # This is a simplified compression - in production,
                        # you'd want more sophisticated compression
                        # For now, we'll just truncate very long content
                        if len(content) > 2000:
                            content = content[:2000] + "...[truncated]"
                    compressed.append(HumanMessage(content=content))
                else:
                    compressed.append(msg)
            else:
                compressed.append(msg)
        return compressed


# Pre-configured LLM instances with error handling
def get_llm_fast() -> WrappedChatOpenAI:
    """Get fast LLM (gpt-4o-mini) with error handling"""
    return WrappedChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.5,
        timeout=30.0
    )


def get_llm_creative() -> WrappedChatOpenAI:
    """Get creative LLM (gpt-4o) with error handling"""
    return WrappedChatOpenAI(
        model="gpt-4o",
        temperature=0.8,
        timeout=60.0
    )


def get_llm_precise() -> WrappedChatOpenAI:
    """Get precise LLM (gpt-4o) with error handling"""
    return WrappedChatOpenAI(
        model="gpt-4o",
        temperature=0.3,
        timeout=60.0
    )


def get_llm_analyst() -> WrappedChatOpenAI:
    """Get analyst LLM (gpt-4o-mini) with error handling"""
    return WrappedChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.4,
        timeout=30.0
    )


def get_llm_storyteller() -> WrappedChatOpenAI:
    """Get storyteller LLM (gpt-4o) with error handling"""
    return WrappedChatOpenAI(
        model="gpt-4o",
        temperature=0.85,
        timeout=60.0
    )


def get_llm_editor() -> WrappedChatOpenAI:
    """Get editor LLM (gpt-4o) with error handling"""
    return WrappedChatOpenAI(
        model="gpt-4o",
        temperature=0.3,
        timeout=60.0
    )
