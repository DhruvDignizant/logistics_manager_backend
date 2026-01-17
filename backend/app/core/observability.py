"""
Observability Middleware for Phase 3.

Adds correlation IDs and structured logging context to requests.
"""

import time
import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Configure structured logger
logger = logging.getLogger("losgistics")

class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Generate or extract Correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        
        # 2. Start Timer
        start_time = time.time()
        
        # 3. Process Request
        response = await call_next(request)
        
        # 4. Calculate Duration
        process_time = (time.time() - start_time) * 1000  # ms
        
        # 5. Add Header to Response
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Process-Time"] = str(process_time)
        
        # 6. Structured Log
        log_data = {
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(process_time, 2),
            "ip": request.client.host if request.client else "unknown"
        }
        
        # Log level based on status
        if response.status_code >= 500:
            logger.error("Request Failed", extra=log_data)
        elif response.status_code >= 400:
            logger.warning("Request Error", extra=log_data)
        else:
            logger.info("Request API", extra=log_data)
            
        return response
