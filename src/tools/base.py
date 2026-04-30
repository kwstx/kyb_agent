import functools
import logging
import time
from typing import Any, Callable, Dict, Optional, Type
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import pybreaker
from langchain.tools import BaseTool
from .audit import audit_store
from .secrets import secrets_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Circuit breaker configuration
# We can have different breakers for different tools if needed, 
# but for now, we'll use a shared one or a factory.
db_breaker = pybreaker.CircuitBreaker(fail_max=5, reset_timeout=60)

class BaseResilientTool(BaseTool):
    """
    A base class for tools with built-in resilience and auditing.
    """
    
    def _run_with_resilience(self, func: Callable, *args, **kwargs) -> Any:
        tool_name = self.name
        input_params = {"args": args, "kwargs": kwargs}
        
        @retry(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((Exception,)), # Customize per tool if needed
            reraise=True
        )
        @db_breaker
        def executed_with_retry_and_breaker():
            start_time = time.time()
            raw_response = None
            try:
                raw_response = func(*args, **kwargs)
                # Audit success
                audit_store.log_invocation(
                    tool_name=tool_name,
                    input_params=input_params,
                    raw_response=raw_response,
                    parsed_output=raw_response, # Default, tools can override
                    status="success"
                )
                return raw_response
            except Exception as e:
                # Audit failure
                audit_store.log_invocation(
                    tool_name=tool_name,
                    input_params=input_params,
                    raw_response=raw_response,
                    parsed_output=None,
                    status="failure",
                    error_message=str(e)
                )
                raise e

        return executed_with_retry_and_breaker()

    async def _arun_with_resilience(self, func: Callable, *args, **kwargs) -> Any:
        # Async implementation of the same pattern
        # (Simplified for now, similar to _run_with_resilience)
        return self._run_with_resilience(func, *args, **kwargs)
