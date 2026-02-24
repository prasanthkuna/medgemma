"""
Pramana AI - FastAPI Main Application
Offline Claim Readiness Copilot
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging

from config import settings
from db.database import init_db
from routers import cases, analysis, policies, pack, health, query

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Ensure directories exist
    settings.cases_dir.mkdir(parents=True, exist_ok=True)
    settings.policies_dir.mkdir(parents=True, exist_ok=True)
    
    # Warm up Pramana AI model (preload into GPU/RAM)
    try:
        import ollama
        logger.info(f"🧠 Warming up Pramana AI ({settings.default_model})...")
        ollama.chat(
            model=settings.default_model,
            messages=[{"role": "user", "content": "Initializing clinical logic pipeline..."}],
            options={"num_predict": 1}
        )
        logger.info("✅ Pramana AI Edge Engine - Warm and Ready")
    except Exception as e:
        logger.warning(f"⚠️ Pramana AI Engine check failed: {e}")
    
    yield
    
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Offline Claim Readiness Copilot for Healthcare",
    lifespan=lifespan
)

# CORS for Tauri/SvelteKit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:1420", "tauri://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(cases.router, prefix="/api/cases", tags=["Cases"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(policies.router, prefix="/api/policies", tags=["Policies"])
app.include_router(pack.router, prefix="/api/pack", tags=["Pack Builder"])
app.include_router(query.router, prefix="/api/cases", tags=["Query Reply"])

# Mount data directory for static file serving
app.mount("/docs", StaticFiles(directory=settings.data_root), name="docs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
