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
import asyncio

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
        from src.safety.guard import guard
        tool_name = self.name
        input_params = {"args": args, "kwargs": kwargs}

        # 1. Evaluate safety and get KYA signature
        evaluation = await guard.evaluate_action(
            action_type=f"tool_execution_{tool_name}", 
            payload=input_params
        )
        
        if not evaluation.authorized:
            audit_store.log_invocation(
                tool_name=tool_name,
                input_params=input_params,
                raw_response=None,
                parsed_output=None,
                status="blocked",
                error_message=f"Safety Guardrail Blocked: {evaluation.reason}"
            )
            raise PermissionError(f"Action blocked by AutonomyGuard: {evaluation.reason}")

        # 2. Proceed with execution
        # (Using a simplified async execution for demo)
        try:
            # If the tool is async, we await it, else we run it in a thread/executor
            if asyncio.iscoroutinefunction(func):
                raw_response = await func(*args, **kwargs)
            else:
                raw_response = func(*args, **kwargs)

            # 3. Audit success with signature
            audit_store.log_invocation(
                tool_name=tool_name,
                input_params=input_params,
                raw_response=raw_response,
                parsed_output=raw_response,
                status="success"
            )
            # Log the signed action to the specific action audit table
            audit_store.log_action(
                agent_id=guard.agent_id,
                action_id=evaluation.action_id,
                action_type=f"tool_execution_{tool_name}",
                risk_tier=evaluation.risk_tier.value,
                signature=evaluation.signature,
                authorized=evaluation.authorized,
                explanation=evaluation.explanation
            )
            return raw_response
        except Exception as e:
            audit_store.log_invocation(
                tool_name=tool_name,
                input_params=input_params,
                raw_response=None,
                parsed_output=None,
                status="failure",
                error_message=str(e)
            )
            raise e
