"""
Security middleware and utilities for production deployment.
"""
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from app.config import settings
import secrets, time, logging
from datetime import datetime

logger = logging.getLogger(__name__)
_rate_limits = {}  # Simple in-memory rate limiting for dev

def setup_security(app: FastAPI):
    """Configure security middleware. MUST be called before app starts."""
    
    # === Security Headers Middleware ===
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
    
    # === Rate Limiting Middleware (simple in-memory) ===
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        # Skip for static files and health checks
        if request.url.path.startswith("/static") or request.url.path == "/health":
            return await call_next(request)
        
        client_ip = request.client.host
        now = time.time()
        window = settings.RATE_LIMIT_WINDOW
        
        # Initialize or clean old entries
        _rate_limits.setdefault(client_ip, [])
        _rate_limits[client_ip] = [ts for ts in _rate_limits[client_ip] if now - ts < window]
        
        # Check limit
        if len(_rate_limits[client_ip]) >= settings.RATE_LIMIT_REQUESTS:
            logger.warning(f"Rate limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please try again later."}
            )
        
        # Record this request
        _rate_limits[client_ip].append(now)
        return await call_next(request)
    
    # === CSRF Validation Middleware ===
    @app.middleware("http")
    async def csrf_validation(request: Request, call_next):
        # Skip CSRF for GET requests and API auth endpoints
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)
        if request.url.path.startswith("/api/auth"):
            return await call_next(request)
            
        # Validate CSRF token for state-changing requests
        session_token = request.session.get("csrf_token")
        form_token = (await request.form()).get("csrf_token") if request.method == "POST" else None
        header_token = request.headers.get("X-CSRF-Token")
        
        incoming_token = form_token or header_token
        
        if not session_token or not incoming_token:
            raise HTTPException(status_code=403, detail="Missing CSRF token")
        
        if not secrets.compare_digest(session_token, incoming_token):
            logger.warning(f"CSRF validation failed for {request.client.host}")
            raise HTTPException(status_code=403, detail="Invalid CSRF token")
        
        return await call_next(request)
    
    logger.info("✓ Security middleware configured")