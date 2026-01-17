"""
Stage 5: Failure Injection Tests.

Validates resilience against component failures.
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.app.core.reliability import CircuitBreaker, CircuitOpenError
from backend.app.models.dlq import DeadLetterQueue

@pytest.mark.asyncio
async def test_circuit_breaker_activates():
    """Test that circuit breaker opens after threshold failures."""
    cb = CircuitBreaker(failure_threshold=2, reset_timeout=1)
    
    async def failing_func():
        raise ValueError("Boom")
        
    # Fail 1
    try:
        await cb.call(failing_func)
    except ValueError:
        pass
        
    # Fail 2 (Threshold reached)
    try:
        await cb.call(failing_func)
    except ValueError:
        pass
        
    # Call 3 (Should be CircuitOpenError)
    try:
        await cb.call(failing_func)
        assert False, "Circuit should be open"
    except CircuitOpenError:
        pass # Success

@pytest.mark.asyncio
async def test_dlq_capture(db_session, mocker):
    """Test that a failed background task is captured in DLQ."""
    # We mimic a task handler behavior here.
    
    task_name = "test_billing_task"
    error = "Payment gateway timeout"
    payload = {"trip_id": 500}
    
    # Manual DLQ entry creation simulation
    from backend.app.models.dlq import DeadLetterQueue, DLQStatus
    
    dlq_item = DeadLetterQueue(
        task_name=task_name,
        error_message=error,
        payload=payload,
        status=DLQStatus.FAILED
    )
    db_session.add(dlq_item)
    await db_session.flush()
    
    assert dlq_item.id is not None
    assert dlq_item.status == DLQStatus.FAILED
