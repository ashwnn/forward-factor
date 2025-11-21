"""Signals and history API routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.signal import Signal
from app.models.decision import SignalUserDecision
from app.models.subscription import Subscription
from app.services.signal_service import SignalService

router = APIRouter(prefix="/api/signals", tags=["signals"])


class SignalResponse(BaseModel):
    """Signal information response."""
    id: str
    ticker: str
    ff_value: float
    front_iv: float
    back_iv: float
    sigma_fwd: float
    front_expiry: str
    back_expiry: str
    front_dte: int
    back_dte: int
    as_of_ts: str
    quality_score: float
    vol_point: str


class DecisionRequest(BaseModel):
    """Request to record a signal decision."""
    decision: str  # "placed" or "ignored"


class DecisionResponse(BaseModel):
    """Decision information response."""
    id: str
    signal_id: str
    decision: str
    decision_ts: str


class HistoryResponse(BaseModel):
    """History entry with signal and decision."""
    signal: SignalResponse
    decision: Optional[DecisionResponse]


@router.get("", response_model=List[SignalResponse])
async def get_signals(
    ticker: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent signals for the user's watchlist.
    
    Optionally filter by ticker.
    Requires authentication.
    """
    # Get user's subscribed tickers
    result = await db.execute(
        select(Subscription.ticker).where(
            and_(
                Subscription.user_id == current_user.id,
                Subscription.active == True
            )
        )
    )
    subscribed_tickers = [row[0] for row in result.all()]
    
    if not subscribed_tickers:
        return []
    
    # Build query for signals
    query = select(Signal).where(Signal.ticker.in_(subscribed_tickers))
    
    if ticker:
        query = query.where(Signal.ticker == ticker.upper())
    
    query = query.order_by(Signal.as_of_ts.desc()).limit(limit)
    
    result = await db.execute(query)
    signals = result.scalars().all()
    
    return [
        {
            "id": str(signal.id),
            "ticker": signal.ticker,
            "ff_value": signal.ff_value,
            "front_iv": signal.front_iv,
            "back_iv": signal.back_iv,
            "sigma_fwd": signal.sigma_fwd,
            "front_expiry": signal.front_expiry.isoformat(),
            "back_expiry": signal.back_expiry.isoformat(),
            "front_dte": signal.front_dte,
            "back_dte": signal.back_dte,
            "as_of_ts": signal.as_of_ts.isoformat(),
            "quality_score": signal.quality_score,
            "vol_point": signal.vol_point
        }
        for signal in signals
    ]


@router.get("/history", response_model=List[HistoryResponse])
async def get_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the user's signal history with decisions.
    
    Requires authentication.
    """
    # Get user's decisions with signals
    result = await db.execute(
        select(SignalUserDecision, Signal)
        .join(Signal, SignalUserDecision.signal_id == Signal.id)
        .where(SignalUserDecision.user_id == current_user.id)
        .order_by(SignalUserDecision.decision_ts.desc())
        .limit(limit)
    )
    
    history = []
    for decision, signal in result.all():
        history.append({
            "signal": {
                "id": str(signal.id),
                "ticker": signal.ticker,
                "ff_value": signal.ff_value,
                "front_iv": signal.front_iv,
                "back_iv": signal.back_iv,
                "sigma_fwd": signal.sigma_fwd,
                "front_expiry": signal.front_expiry.isoformat(),
                "back_expiry": signal.back_expiry.isoformat(),
                "front_dte": signal.front_dte,
                "back_dte": signal.back_dte,
                "as_of_ts": signal.as_of_ts.isoformat(),
                "quality_score": signal.quality_score,
                "vol_point": signal.vol_point
            },
            "decision": {
                "id": str(decision.id),
                "signal_id": str(decision.signal_id),
                "decision": decision.decision,
                "decision_ts": decision.decision_ts.isoformat()
            }
        })
    
    return history


@router.post("/{signal_id}/decision", response_model=DecisionResponse, status_code=status.HTTP_201_CREATED)
async def record_decision(
    signal_id: str,
    request: DecisionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Record a decision (place/ignore) for a signal.
    
    Requires authentication.
    """
    # Validate decision type
    if request.decision not in ["placed", "ignored"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be 'placed' or 'ignored'"
        )
    
    # Verify signal exists
    result = await db.execute(select(Signal).where(Signal.id == signal_id))
    signal = result.scalar_one_or_none()
    
    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signal not found"
        )
    
    # Check if decision already exists
    result = await db.execute(
        select(SignalUserDecision).where(
            and_(
                SignalUserDecision.signal_id == signal_id,
                SignalUserDecision.user_id == current_user.id
            )
        )
    )
    existing_decision = result.scalar_one_or_none()
    
    if existing_decision:
        # Update existing decision
        existing_decision.decision = request.decision
        existing_decision.decision_ts = datetime.utcnow()
        await db.commit()
        await db.refresh(existing_decision)
        
        return {
            "id": str(existing_decision.id),
            "signal_id": str(existing_decision.signal_id),
            "decision": existing_decision.decision,
            "decision_ts": existing_decision.decision_ts.isoformat()
        }
    
    # Create new decision
    decision = SignalUserDecision(
        signal_id=signal_id,
        user_id=current_user.id,
        decision=request.decision,
        decision_ts=datetime.utcnow()
    )
    
    db.add(decision)
    await db.commit()
    await db.refresh(decision)
    
    return {
        "id": str(decision.id),
        "signal_id": str(decision.signal_id),
        "decision": decision.decision,
        "decision_ts": decision.decision_ts.isoformat()
    }
