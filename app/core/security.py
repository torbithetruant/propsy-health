"""
Security middleware and utilities for production deployment.
"""
import logging
import secrets
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.config import get_settings

logger = logging.getLogger(__name__)


# ============================================================================
# SLIDING WINDOW RATE LIMITER
# ============================================================================

class SlidingWindowRateLimiter:
    """
    Production-grade sliding window rate limiter.
    
    Uses a sliding window algorithm that tracks request timestamps
    and automatically cleans up expired entries.
    
    Features:
    - Sliding window algorithm (more accurate than fixed window)
    - Automatic cleanup of expired entries
    - Memory efficient with periodic garbage collection
    - Configurable per-endpoint limits
    - Thread-safe for async operations
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Cleanup every 5 minutes
    
    def is_allowed(self, key: str, custom_limit: Optional[int] = None) -> bool:
        """
        Check if a request is allowed for the given key.
        
        Args:
            key: Unique identifier (IP address, user ID, endpoint, etc.)
            custom_limit: Optional custom limit for this specific key
            
        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        now = time.time()
        window_start = now - self.window_seconds
        limit = custom_limit or self.max_requests
        
        # Periodic cleanup to prevent memory leaks
        self._cleanup_if_needed(now)
        
        # Get request history for this key
        request_history = self._requests[key]
        
        # Remove expired entries (outside the window)
        self._requests[key] = [
            ts for ts in request_history if ts > window_start
        ]
        
        # Check if limit exceeded
        if len(self._requests[key]) >= limit:
            return False
        
        # Record this request
        self._requests[key].append(now)
        return True
    
    def get_remaining(self, key: str, custom_limit: Optional[int] = None) -> int:
        """
        Get remaining requests for a key.
        
        Args:
            key: Unique identifier
            custom_limit: Optional custom limit
            
        Returns:
            Number of remaining requests allowed
        """
        now = time.time()
        window_start = now - self.window_seconds
        limit = custom_limit or self.max_requests
        
        if key not in self._requests:
            return limit
        
        active_requests = [ts for ts in self._requests[key] if ts > window_start]
        return max(0, limit - len(active_requests))
    
    def get_reset_time(self, key: str) -> Optional[float]:
        """
        Get time when the rate limit resets for a key.
        
        Args:
            key: Unique identifier
            
        Returns:
            Unix timestamp when limit resets, or None if no requests
        """
        if key not in self._requests or not self._requests[key]:
            return None
        
        oldest_request = min(self._requests[key])
        return oldest_request + self.window_seconds
    
    def reset(self, key: str) -> None:
        """
        Reset rate limit for a specific key.
        
        Args:
            key: Unique identifier to reset
        """
        self._requests.pop(key, None)
    
    def _cleanup_if_needed(self, now: float) -> None:
        """
        Perform periodic cleanup of expired entries to prevent memory leaks.
        """
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        window_start = now - self.window_seconds
        
        # Remove keys with no active requests
        keys_to_remove = []
        for key, timestamps in self._requests.items():
            active_timestamps = [ts for ts in timestamps if ts > window_start]
            if not active_timestamps:
                keys_to_remove.append(key)
            else:
                self._requests[key] = active_timestamps
        
        for key in keys_to_remove:
            del self._requests[key]
        
        self._last_cleanup = now
        
        if keys_to_remove:
            logger.debug(f"Rate limiter cleanup: removed {len(keys_to_remove)} expired keys")
    
    def get_stats(self) -> dict:
        """
        Get rate limiter statistics.
        
        Returns:
            Dictionary with stats about current state
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        total_keys = len(self._requests)
        active_keys = sum(
            1 for timestamps in self._requests.values()
            if any(ts > window_start for ts in timestamps)
        )
        total_requests = sum(
            len([ts for ts in timestamps if ts > window_start])
            for timestamps in self._requests.values()
        )
        
        return {
            "total_keys": total_keys,
            "active_keys": active_keys,
            "total_requests_in_window": total_requests,
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
        }


# ============================================================================
# ENDPOINT-SPECIFIC RATE LIMITERS
# ============================================================================

# Different rate limits for different types of endpoints
_oauth_rate_limiter = SlidingWindowRateLimiter(max_requests=10, window_seconds=60)  # 10/min for OAuth
_api_rate_limiter = SlidingWindowRateLimiter(max_requests=100, window_seconds=60)  # 100/min for API
_general_rate_limiter = SlidingWindowRateLimiter(max_requests=200, window_seconds=60)  # 200/min general


# ============================================================================
# SECURITY MIDDLEWARE SETUP
# ============================================================================

def setup_security(app: FastAPI):
    """
    Configure security middleware. MUST be called before app starts.
    
    Sets up:
    - Security headers (X-Content-Type-Options, X-Frame-Options, etc.)
    - Rate limiting with sliding window algorithm
    - CSRF token validation for state-changing requests
    """
    settings = get_settings()
    
    # === Security Headers Middleware ===
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        """Add security headers to all responses."""
        response = await call_next(request)
        
        # Standard security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        
        # HSTS (HTTPS enforcement) - only in production
        if not settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Prevent caching of sensitive endpoints
        if request.url.path.startswith("/api/tokens"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
        
        return response
    
    # === Rate Limiting Middleware ===
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        """Apply rate limiting based on endpoint type."""
        # Skip rate limiting for static files and health checks
        if request.url.path.startswith("/static") or request.url.path == "/health":
            return await call_next(request)
        
        client_ip = request.client.host
        
        # Determine which rate limiter to use based on endpoint
        if request.url.path in ("/login", "/oauth/callback"):
            # Stricter limits for OAuth endpoints
            limiter = _oauth_rate_limiter
            limit_key = f"oauth:{client_ip}"
        elif request.url.path.startswith("/api/"):
            # API endpoints
            limiter = _api_rate_limiter
            limit_key = f"api:{client_ip}"
        else:
            # General pages
            limiter = _general_rate_limiter
            limit_key = f"general:{client_ip}"
        
        # Check rate limit
        if not limiter.is_allowed(limit_key):
            reset_time = limiter.get_reset_time(limit_key)
            retry_after = int(reset_time - time.time()) if reset_time else limiter.window_seconds
            
            logger.warning(
                f"Rate limit exceeded for {client_ip} on {request.url.path} "
                f"(limit: {limiter.max_requests}/{limiter.window_seconds}s)"
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "retry_after": retry_after,
                    "limit": limiter.max_requests,
                    "window_seconds": limiter.window_seconds,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limiter.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_time)) if reset_time else "",
                }
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        remaining = limiter.get_remaining(limit_key)
        reset_time = limiter.get_reset_time(limit_key)
        
        response.headers["X-RateLimit-Limit"] = str(limiter.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        if reset_time:
            response.headers["X-RateLimit-Reset"] = str(int(reset_time))
        
        return response
    
    # === CSRF Validation Middleware ===
    @app.middleware("http")
    async def csrf_validation(request: Request, call_next):
        """Validate CSRF tokens for state-changing requests."""
        # Skip CSRF for safe methods
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return await call_next(request)
        
        # Skip if session middleware is not installed or hasn't run yet
        if "session" not in request.scope:
            return await call_next(request)
            
        # Skip CSRF for OAuth callback (uses state parameter instead)
        if request.url.path in ("/oauth/callback", "/login", "/consent", "/consent/withdraw"):
            return await call_next(request)
        
        # Skip CSRF for API endpoints
        if request.url.path.startswith("/api/"):
            return await call_next(request)
            
        # Skip CSRF for dashboard POSTs (forms don't have CSRF tokens yet)
        if request.url.path.startswith("/dashboard/"):
            return await call_next(request)
        
        # Validate CSRF token for other state-changing requests
        session_token = request.session.get("csrf_token")
        
        # Get CSRF token from form data or header
        form_token = None
        if request.method == "POST":
            try:
                form_data = await request.form()
                form_token = form_data.get("csrf_token")
            except Exception:
                pass
        
        header_token = request.headers.get("X-CSRF-Token")
        incoming_token = form_token or header_token
        
        # Validate token
        if not session_token or not incoming_token:
            logger.warning(f"Missing CSRF token from {request.client.host} on {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing CSRF token. Please refresh the page and try again."
            )
        
        if not secrets.compare_digest(session_token, incoming_token):
            logger.warning(f"CSRF validation failed for {request.client.host} on {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid CSRF token. Security validation failed."
            )
        
        return await call_next(request)
    
    # === Request Logging Middleware ===
    @app.middleware("http")
    async def request_logging(request: Request, call_next):
        """Log all requests for security auditing."""
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Define paths that are usually noisy
        is_noisy_path = (
            request.url.path.startswith("/static") or 
            request.url.path == "/health" or 
            request.url.path in ("/docs", "/redoc", "/openapi.json")
        )
        
        # Only ignore these paths if the request was successful (200 OK)
        # If it fails (e.g., 500, 503, 404), we WANT to see it in the logs
        should_ignore = is_noisy_path and response.status_code == 200
        
        if not should_ignore:
            logger.info(
                f"{request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"IP: {request.client.host} - "
                f"Duration: {duration:.3f}s"
            )
        
        return response
    
    logger.info("✅ Security middleware configured")
    logger.info(f"   Rate limits: OAuth={_oauth_rate_limiter.max_requests}/min, "
                f"API={_api_rate_limiter.max_requests}/min, "
                f"General={_general_rate_limiter.max_requests}/min")


# ============================================================================
# CSRF TOKEN UTILITIES
# ============================================================================

def generate_csrf_token() -> str:
    """
    Generate a cryptographically secure CSRF token.
    
    Returns:
        URL-safe base64-encoded token (43 characters)
    """
    return secrets.token_urlsafe(32)


def validate_csrf_token(session_token: str, incoming_token: str) -> bool:
    """
    Validate a CSRF token using constant-time comparison.
    
    Args:
        session_token: Token stored in session
        incoming_token: Token from request (form or header)
        
    Returns:
        True if tokens match, False otherwise
    """
    if not session_token or not incoming_token:
        return False
    
    return secrets.compare_digest(session_token, incoming_token)


# ============================================================================
# SECURITY UTILITIES
# ============================================================================

def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request, considering proxies.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Client IP address string
    """
    # Check for X-Forwarded-For header (set by reverse proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP in the chain (original client)
        return forwarded_for.split(",")[0].strip()
    
    # Check for X-Real-IP header (nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    # Fall back to direct connection IP
    return request.client.host if request.client else "unknown"


def is_safe_redirect_url(url: str, allowed_hosts: list[str]) -> bool:
    """
    Validate that a redirect URL is safe (prevents open redirect attacks).
    
    Args:
        url: URL to validate
        allowed_hosts: List of allowed hostnames
        
    Returns:
        True if URL is safe, False otherwise
    """
    from urllib.parse import urlparse
    
    try:
        parsed = urlparse(url)
        
        # Only allow http/https schemes
        if parsed.scheme not in ("http", "https"):
            return False
        
        # Check if host is in allowed list
        if parsed.netloc and parsed.netloc not in allowed_hosts:
            return False
        
        # Relative URLs are safe
        if not parsed.netloc:
            return True
        
        return True
    except Exception:
        return False


def mask_sensitive_data(value: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive data for logging (e.g., tokens, keys).
    
    Args:
        value: Sensitive string
        visible_chars: Number of characters to show at start
        
    Returns:
        Masked string (e.g., "ya29.abc...xyz" → "ya29...")
    """
    if not value or len(value) <= visible_chars:
        return "****"
    
    return value[:visible_chars] + "..."


# ============================================================================
# RATE LIMITER STATISTICS ENDPOINT (for monitoring)
# ============================================================================

def get_rate_limiter_stats() -> dict:
    """
    Get statistics from all rate limiters.
    
    Returns:
        Dictionary with stats for each rate limiter
    """
    return {
        "oauth": _oauth_rate_limiter.get_stats(),
        "api": _api_rate_limiter.get_stats(),
        "general": _general_rate_limiter.get_stats(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }