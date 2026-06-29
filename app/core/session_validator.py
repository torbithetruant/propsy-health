"""
Middleware to validate that session users still exist in the database.

This solves the "stale session" problem where an admin deletes a user
but their browser session cookie remains valid.
"""
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse

from app.database import get_database

logger = logging.getLogger(__name__)


class SessionValidationMiddleware(BaseHTTPMiddleware):
    PUBLIC_PATHS = {
        "/", "/login", "/oauth/callback", "/privacy", "/health",
        "/admin/login", "/admin/logout"
    }
    
    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.PUBLIC_PATHS or request.url.path.startswith("/static"):
            return await call_next(request)
        
        if "session" not in request.scope:
            return await call_next(request)
        
        legacy_id = request.session.get("legacy_id")
        
        if legacy_id:
            try:
                db = get_database()
                
                # Check 1: Does user have an OAuth token?
                token_col = db["oauth_tokens"]
                has_token = await token_col.find_one({"legacy_id": legacy_id}) is not None
                
                # Check 2: Does user have a consent record?
                consent_col = db["user_consents"]
                consent_record = await consent_col.find_one({"legacy_id": legacy_id})
                
                # Decision logic:
                # - Has token + has consent → Valid user, let through
                # - Has token + NO consent → User in onboarding flow (just did OAuth), let through
                # - NO token + NO consent → Stale/deleted session, invalidate
                # - NO token + has consent → Edge case (token revoked but consent exists), let through
                
                if not has_token and not consent_record:
                    logger.warning(f"🚨 Stale session for {legacy_id}: no token, no consent. Clearing.")
                    request.session.clear()
                    
                    if not request.url.path.startswith("/admin"):
                        return RedirectResponse(url="/?session_expired=true", status_code=303)
                
            except Exception as e:
                logger.error(f"Session validation error: {e}")
        
        return await call_next(request)