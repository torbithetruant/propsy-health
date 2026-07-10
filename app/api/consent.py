"""Routes for the informed consent flow."""
import logging
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.session import get_current_user, SessionUser, clear_user_session
from app.core.templates import templates
from app.database import get_database
from app.services.consent_storage import ConsentStorageService
from app.core.security import get_client_ip
from app.services.health_data_storage import HealthDataStorage
from app.auth.token_storage import TokenStorageService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["consent"])



@router.get("/consent", response_class=HTMLResponse)
async def show_consent_form(
    request: Request,
    current_user: SessionUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    storage = ConsentStorageService(db)
    
    if await storage.has_active_consent(current_user.legacy_id):
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    
    return templates.TemplateResponse(
        request,
        "consent.html",
        {
            "current_user": current_user,
            "legacy_id": current_user.legacy_id,
            "health_id": current_user.health_id,
            "consent_version": ConsentStorageService.CURRENT_CONSENT_VERSION,
        }
    )


@router.post("/consent")
async def submit_consent(
    request: Request,
    current_user: SessionUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Process the signed consent form.
    """

    if hasattr(request.state, "form_data"):
        form = request.state.form_data
    else:
        form = await request.form()
    
    # DEBUG: Log exactly what keys are arriving from the browser
    logger.info(f" Consent form keys received: {list(form.keys())}")
    
    # FIX: Check for the presence of the key, not its string value.
    # In HTML forms, unchecked checkboxes are completely omitted from the payload.
    # Therefore, if the key exists in the form, the box was checked.
    consent_read = "consent_read" in form
    consent_voluntary = "consent_voluntary" in form
    consent_data = "consent_data" in form
    
    # Validate all required checkboxes were checked
    if not all([consent_read, consent_voluntary, consent_data]):
        logger.warning(f" Consent validation failed. Read: {consent_read}, Voluntary: {consent_voluntary}, Data: {consent_data}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="All consent checkboxes must be checked"
        )
    
    # Record consent with boolean flags
    storage = ConsentStorageService(db)
    consent_id = await storage.record_consent(
        legacy_id=current_user.legacy_id,
        health_id=current_user.health_id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
        consent_read=consent_read,
        consent_voluntary=consent_voluntary,
        consent_data=consent_data,
    )
    
    # Store consent metadata in session for quick access
    request.session["consent_given"] = True
    request.session["consent_id"] = consent_id
    request.session["consent_version"] = ConsentStorageService.CURRENT_CONSENT_VERSION
    
    logger.info(f" Consent submitted by {current_user.legacy_id} (consent_id: {consent_id})")
    
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


# @router.post("/consent/withdraw")
# WILL BE AVAILABLE FOR ADMIN
async def withdraw_consent(
    request: Request,
    current_user: SessionUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Withdraw consent and optionally delete all data.
    
    This is the GDPR Article 17 "Right to Erasure" implementation.
    """
    if hasattr(request.state, "form_data"):
        form = request.state.form_data
    else:
        form = await request.form()
        
    reason = form.get("reason", "User-initiated withdrawal")
    delete_data = form.get("delete_data") == "true"
    
    storage = ConsentStorageService(db)
    success = await storage.withdraw_consent(
        legacy_id=current_user.legacy_id,
        reason=reason,
        delete_data=delete_data
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active consent found to withdraw"
        )
    
    # If requested, also delete health data and token
    health_storage = HealthDataStorage(db)
    token_storage = TokenStorageService(db)
    
    if delete_data:
        await health_storage.delete_all_records(current_user.legacy_id)
        await token_storage.hard_delete_token(current_user.legacy_id)
        logger.info(f"All data deleted for {current_user.legacy_id} upon withdrawal")
    else:
        # Revoke the token but keep data if user opted not to delete
        await token_storage.delete_token(current_user.legacy_id)
        logger.info(f"Consent withdrawn for {current_user.legacy_id} without data deletion")
    
    # Clear session
    clear_user_session(request)
    
    logger.info(f"Consent withdrawn for {current_user.legacy_id}")
    return RedirectResponse(url="/?withdrawn=true", status_code=status.HTTP_303_SEE_OTHER)