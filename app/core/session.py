"""
Session management for authenticated users.
"""
from fastapi import Request, HTTPException, status
from typing import Optional


class SessionUser:
    """Represents an authenticated user from session."""
    
    def __init__(self, legacy_id: str, health_id: str):
        self.legacy_id = legacy_id
        self.health_id = health_id
    
    def __repr__(self):
        return f"SessionUser(legacy_id={self.legacy_id}, health_id={self.health_id})"


async def get_current_user(request: Request) -> SessionUser:
    """
    Dependency to get current authenticated user from session.
    
    Raises HTTPException if user is not authenticated.
    """
    legacy_id = request.session.get("legacy_id")
    health_id = request.session.get("health_id")
    
    if not legacy_id or not health_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please connect your Google Health account.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return SessionUser(legacy_id=legacy_id, health_id=health_id)


async def get_optional_user(request: Request) -> Optional[SessionUser]:
    """
    Dependency to get current user if authenticated, None otherwise.
    """
    legacy_id = request.session.get("legacy_id")
    health_id = request.session.get("health_id")
    
    if not legacy_id or not health_id:
        return None
    
    return SessionUser(legacy_id=legacy_id, health_id=health_id)


def set_user_session(request: Request, legacy_id: str, health_id: str):
    """Store user info in session after successful OAuth."""
    request.session["legacy_id"] = legacy_id
    request.session["health_id"] = health_id
    request.session["authenticated"] = True


def clear_user_session(request: Request):
    """Clear user session on logout/disconnect."""
    request.session.pop("legacy_id", None)
    request.session.pop("health_id", None)
    request.session.pop("authenticated", None)