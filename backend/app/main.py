"""
FastAPI Application Entry Point.

This is the main application file for the Logistics Manager Backend.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from backend.app.core.config import settings
from backend.app.api.v1.router import router as api_v1_router
from backend.app.core.dependencies import get_current_user
from backend.app.core.jwt import create_access_token
from backend.app.db.session import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for application startup/shutdown.
    
    1. Creates database tables on startup.
    2. Handles graceful shutdown (if needed).
    """
    # Create tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Cleanup (optional)

# Initialize FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.api_version,
    debug=settings.debug,
    description="A scalable FastAPI backend for logistics management",
    lifespan=lifespan,
)


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        dict: Status and application information
    """
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.api_version,
    }


# Include API v1 router
app.include_router(api_v1_router, prefix=f"/{settings.api_version}")


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.
    
    Returns:
        dict: Welcome message and API documentation links
    """
    return {
        "message": "Welcome to Logistics Manager Backend API",
        "docs": "/docs",
        "health": "/health",
    }


# Authentication test endpoints (for Phase-2 validation)
@app.post("/auth/test-token", tags=["Authentication"])
async def generate_test_token(user_id: int = 1, username: str = "test_user"):
    """
    Generate a test JWT token.
    
    This endpoint is for Phase-2 validation purposes only.
    """
    token = create_access_token(data={"sub": username, "user_id": user_id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id,
        "username": username,
    }


@app.get("/auth/protected", tags=["Authentication"])
async def protected_route(current_user: dict = Depends(get_current_user)):
    """
    Protected route that requires valid JWT authentication.
    
    Returns 401 if token is missing or invalid.
    Returns 200 with user info if authentication succeeds.
    """
    return {
        "message": "Access granted to protected resource",
        "authenticated_user": current_user,
    }
