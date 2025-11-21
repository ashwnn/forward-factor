"""User settings API routes."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Optional

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.user_service import UserService

router = APIRouter(prefix="/api/settings", tags=["settings"])


class DTEPair(BaseModel):
    """DTE pair configuration."""
    front: int
    back: int
    front_tol: int
    back_tol: int


class QuietHours(BaseModel):
    """Quiet hours configuration."""
    enabled: bool
    start: str
    end: str


class SettingsResponse(BaseModel):
    """User settings response."""
    ff_threshold: float
    dte_pairs: List[DTEPair]
    vol_point: str
    min_open_interest: int
    min_volume: int
    max_bid_ask_pct: float
    sigma_fwd_floor: float
    stability_scans: int
    cooldown_minutes: int
    quiet_hours: QuietHours
    preferred_structure: str
    timezone: str
    scan_priority: str


class UpdateSettingsRequest(BaseModel):
    """Request to update user settings."""
    ff_threshold: Optional[float] = None
    dte_pairs: Optional[List[Dict]] = None
    vol_point: Optional[str] = None
    min_open_interest: Optional[int] = None
    min_volume: Optional[int] = None
    max_bid_ask_pct: Optional[float] = None
    sigma_fwd_floor: Optional[float] = None
    stability_scans: Optional[int] = None
    cooldown_minutes: Optional[int] = None
    quiet_hours: Optional[Dict] = None
    preferred_structure: Optional[str] = None
    timezone: Optional[str] = None
    scan_priority: Optional[str] = None


@router.get("", response_model=SettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current user's settings.
    
    Requires authentication.
    """
    settings = await UserService.get_user_settings(str(current_user.id), db)
    
    return {
        "ff_threshold": settings.ff_threshold,
        "dte_pairs": settings.dte_pairs,
        "vol_point": settings.vol_point,
        "min_open_interest": settings.min_open_interest,
        "min_volume": settings.min_volume,
        "max_bid_ask_pct": settings.max_bid_ask_pct,
        "sigma_fwd_floor": settings.sigma_fwd_floor,
        "stability_scans": settings.stability_scans,
        "cooldown_minutes": settings.cooldown_minutes,
        "quiet_hours": settings.quiet_hours,
        "preferred_structure": settings.preferred_structure,
        "timezone": settings.timezone,
        "scan_priority": settings.scan_priority
    }


@router.put("", response_model=SettingsResponse)
async def update_settings(
    request: UpdateSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the current user's settings.
    
    Only provided fields will be updated.
    Requires authentication.
    """
    settings = await UserService.get_user_settings(str(current_user.id), db)
    
    # Update only provided fields
    if request.ff_threshold is not None:
        settings.ff_threshold = request.ff_threshold
    if request.dte_pairs is not None:
        settings.dte_pairs = request.dte_pairs
    if request.vol_point is not None:
        settings.vol_point = request.vol_point
    if request.min_open_interest is not None:
        settings.min_open_interest = request.min_open_interest
    if request.min_volume is not None:
        settings.min_volume = request.min_volume
    if request.max_bid_ask_pct is not None:
        settings.max_bid_ask_pct = request.max_bid_ask_pct
    if request.sigma_fwd_floor is not None:
        settings.sigma_fwd_floor = request.sigma_fwd_floor
    if request.stability_scans is not None:
        settings.stability_scans = request.stability_scans
    if request.cooldown_minutes is not None:
        settings.cooldown_minutes = request.cooldown_minutes
    if request.quiet_hours is not None:
        settings.quiet_hours = request.quiet_hours
    if request.preferred_structure is not None:
        settings.preferred_structure = request.preferred_structure
    if request.timezone is not None:
        settings.timezone = request.timezone
    if request.scan_priority is not None:
        settings.scan_priority = request.scan_priority
    
    await db.commit()
    await db.refresh(settings)
    
    return {
        "ff_threshold": settings.ff_threshold,
        "dte_pairs": settings.dte_pairs,
        "vol_point": settings.vol_point,
        "min_open_interest": settings.min_open_interest,
        "min_volume": settings.min_volume,
        "max_bid_ask_pct": settings.max_bid_ask_pct,
        "sigma_fwd_floor": settings.sigma_fwd_floor,
        "stability_scans": settings.stability_scans,
        "cooldown_minutes": settings.cooldown_minutes,
        "quiet_hours": settings.quiet_hours,
        "preferred_structure": settings.preferred_structure,
        "timezone": settings.timezone,
        "scan_priority": settings.scan_priority
    }
