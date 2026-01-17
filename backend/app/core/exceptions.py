"""
Custom exceptions and error handlers for consistent error responses.

Provides standardized error codes and global exception handlers.
"""

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Any, Dict


class AppException(Exception):
    """Base application exception."""
    
    def __init__(self, message: str, error_code: str, status_code: int = 500, details: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class InsufficientPermissionsError(AppException):
    """Raised when user doesn't have permission to perform an action."""
    
    def __init__(self, message: str = "Insufficient permissions", details: Dict[str, Any] = None):
        super().__init__(
            message=message,
            error_code="ERR_PERM_001",
            status_code=status.HTTP_403_FORBIDDEN,
            details=details
        )


class ResourceNotFoundError(AppException):
    """Raised when requested resource is not found."""
    
    def __init__(self, resource: str, resource_id: Any = None):
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with ID {resource_id} not found"
        super().__init__(
            message=message,
            error_code="ERR_NOT_FOUND_001",
            status_code=status.HTTP_404_NOT_FOUND,
            details={"resource": resource, "id": resource_id}
        )


class AuthenticationError(AppException):
    """Raised for authentication failures."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="ERR_AUTH_001",
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class TokenRevokedError(AppException):
    """Raised when token has been revoked."""
    
    def __init__(self):
        super().__init__(
            message="Token has been revoked",
            error_code="ERR_AUTH_002",
            status_code=status.HTTP_401_UNAUTHORIZED
        )


# Global Exception Handlers

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handler for custom application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handler for FastAPI HTTPException with standardized format."""
    # Map status code to error code
    error_code_map = {
        400: "ERR_BAD_REQUEST",
        401: "ERR_UNAUTHORIZED",
        403: "ERR_FORBIDDEN",
        404: "ERR_NOT_FOUND",
        500: "ERR_INTERNAL_SERVER"
    }
    
    error_code = error_code_map.get(exc.status_code, "ERR_UNKNOWN")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": error_code,
            "message": exc.detail,
            "details": {}
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handler for Pydantic validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_code": "ERR_VALIDATION",
            "message": "Validation error",
            "details": {
                "errors": exc.errors()
            }
        }
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler for unhandled exceptions."""
    # Log the exception (in production, use proper logging)
    print(f"Unhandled exception: {type(exc).__name__}: {str(exc)}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "ERR_INTERNAL_SERVER",
            "message": "An internal server error occurred",
            "details": {}
        }
    )
