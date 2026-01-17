"""
Reliability Utilities for Phase 3.

Includes Circuit Breaker pattern.
"""

import time
import asyncio
from functools import wraps
from typing import Callable, Any

class CircuitOpenError(Exception):
    pass

class CircuitBreaker:
    """
    Simple Circuit Breaker implementation.
    If 'failure_threshold' failures occur within 'reset_timeout', 
    the circuit opens and rejects calls for 'reset_timeout' seconds.
    """
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED" # CLOSED, OPEN, HALF_OPEN

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitOpenError("Circuit is OPEN")

        try:
            result = await func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.reset_state()
            return result
        except Exception as e:
            self.record_failure()
            raise e

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"

    def reset_state(self):
        self.failures = 0
        self.state = "CLOSED"

# Global instance for heavy ML calls
ml_circuit_breaker = CircuitBreaker(failure_threshold=3, reset_timeout=30)
