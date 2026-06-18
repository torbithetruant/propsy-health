"""FastAPI application entry point."""
import signal
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.database import connect_to_mongodb, close_mongodb
from app.api import auth, dashboard
from app.core.logging import setup_logging, get_logger
from app.core.security import setup_security

# Initialize logging
setup_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    logger.info("🚀 Starting Sanpsy Health OAuth Connector")
    await connect_to_mongodb()
    
    # Graceful shutdown handler for Cloud Run
    def handle_sigterm(*args):
        logger.info("🛑 Received SIGTERM, shutting down gracefully...")
        raise KeyboardInterrupt
    
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    yield

    # Shutdown
    logger.info("🛑 Shutting down Sanpsy Health OAuth Connector")
    await close_mongodb()


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="Sanpsy Health OAuth Connector",
        description="Secure Google Health authentication service",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    setup_security(app)
    
    # Security Middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        https_only=settings.is_production,
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
    app.include_router(dashboard.router)
    
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