"""FastAPI application entry point."""
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from app.config import get_settings
from app.database import connect_to_mongodb, close_mongodb
from app.api import auth

# Configure logging
logging.basicConfig(
    level=getattr(logging, get_settings().log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    logger.info("🚀 Starting Propsy Health OAuth Connector")
    await connect_to_mongodb()
    yield
    # Shutdown
    logger.info("🛑 Shutting down Propsy Health OAuth Connector")
    await close_mongodb()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="Propsy Health OAuth Connector",
        description="Secure Google Health authentication service",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )
    
    # Security Middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        https_only=False,
        same_site="lax"
    )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.base_url] if settings.is_production else ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )
    
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Static files and templates
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    
    # Register routers
    app.include_router(auth.public_router)  # Public OAuth endpoints
    app.include_router(auth.router)  # API endpoints
    
    # Root redirect to homepage
    @app.get("/health")
    async def root_health():
        """Root health check."""
        from app.database import health_check
        return await health_check()
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return {
            "detail": "Internal server error",
            "error_type": type(exc).__name__
        }, status.HTTP_500_INTERNAL_SERVER_ERROR
    
    logger.info("✅ FastAPI application configured")
    return app


# Create app instance for uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=not settings.is_production,
        log_level=settings.log_level.lower()
    )