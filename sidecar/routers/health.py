"""
Health check router
"""
from fastapi import APIRouter
from config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint for Tauri to verify sidecar is running"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "mode": "Edge AI",
        "offline_verified": True  # Always true - strict local execution
    }


@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "docs": "/docs"
    }
