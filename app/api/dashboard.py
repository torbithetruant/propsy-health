"""
User dashboard routes for managing Google Health connection.
"""
import logging
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.session import SessionUser, clear_user_session, get_current_user_with_consent
from app.core.templates import templates
from app.database import get_database
from app.auth.token_storage import TokenStorageService
from app.config import get_settings
from app.services.health_data_storage import HealthDataStorage

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/", response_class=HTMLResponse)
async def dashboard_home(
    request: Request,
    current_user: SessionUser = Depends(get_current_user_with_consent)
):
    """Main dashboard page with menu."""
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "legacy_id": current_user.legacy_id,
            "health_id": current_user.health_id,
        }
    )


@router.get("/data", response_class=HTMLResponse)
async def view_my_data(
    request: Request,
    current_user: SessionUser = Depends(get_current_user_with_consent),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """View Google Health data."""
    # Get token from database
    
    return templates.TemplateResponse(
        request,
        "data.html",
        {
            "legacy_id": current_user.legacy_id,
            "health_id": current_user.health_id,
            "health_data": None,
        }
    )


@router.post("/disconnect")
async def disconnect_account(
    request: Request,
    current_user: SessionUser = Depends(get_current_user_with_consent),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Disconnect Google Health account.
    """
    
    # Clear session
    clear_user_session(request)
    
    return RedirectResponse(url="/?disconnected=true", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/revoke")
async def revoke_token(
    request: Request,
    current_user: SessionUser = Depends(get_current_user_with_consent),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Revoke token (soft delete).
    Marks token as revoked but keeps it in database.
    """
    storage = TokenStorageService(db)
    success = await storage.delete_token(current_user.legacy_id)
    
    if success:
        logger.info(f"✅ Token revoked for {current_user.legacy_id}")
        # Clear session
        clear_user_session(request)
        return RedirectResponse(url="/?revoked=true", status_code=status.HTTP_303_SEE_OTHER)
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token not found"
        )


@router.post("/withdraw")
async def withdraw_from_study(
    request: Request,
    current_user: SessionUser = Depends(get_current_user_with_consent),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Redirect to withdrawal confirmation page. If confirmed, deletes all data and revokes token.
    This is the GDPR Article 17 "Right to Erasure" implementation.
    """
    
    logger.info(f"Initiating withdrawal process for {current_user.legacy_id}")
    return templates.TemplateResponse(
        request,
        "withdraw.html",
        {
            "legacy_id": current_user.legacy_id,
            "health_id": current_user.health_id,
        }
    )