"""Signal service for persistence and retrieval."""
from typing import List, Optional, Dict, Any
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from app.models import Signal, SignalUserDecision
from datetime import datetime
import hashlib


class SignalService:
    """Service for signal management."""
    
    @staticmethod
    def generate_dedupe_key(signal: Dict[str, Any]) -> str:
        """
        Generate unique dedupe key for a signal.
        
        Based on ticker, front/back expiry, and date.
        Uses SHA256 for better collision resistance.
        """
        ticker = signal["ticker"]
        front_expiry = str(signal["front_expiry"])
        back_expiry = str(signal["back_expiry"])
        date_str = signal["as_of_ts"].strftime("%Y-%m-%d")
        
        key_str = f"{ticker}:{front_expiry}:{back_expiry}:{date_str}"
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    @staticmethod
    async def create_signal(
        db: AsyncSession,
        signal_data: Dict[str, Any]
    ) -> Optional[Signal]:
        """
        Create a new signal record using INSERT OR IGNORE for atomic upsert.
        
        Args:
            db: Database session
            signal_data: Signal dictionary from compute_signals()
            
        Returns:
            Signal object, or None if duplicate
        """
        dedupe_key = SignalService.generate_dedupe_key(signal_data)
        
        # Use INSERT OR IGNORE for atomic duplicate check
        # This prevents race conditions between check and insert
        signal_values = {
            "ticker": signal_data["ticker"],
            "as_of_ts": signal_data["as_of_ts"],
            "front_expiry": signal_data["front_expiry"],
            "back_expiry": signal_data["back_expiry"],
            "front_dte": signal_data["front_dte"],
            "back_dte": signal_data["back_dte"],
            "front_iv": signal_data["front_iv"],
            "back_iv": signal_data["back_iv"],
            "sigma_fwd": signal_data["sigma_fwd"],
            "ff_value": signal_data["ff_value"],
            "vol_point": signal_data["vol_point"],
            "quality_score": signal_data.get("quality_score"),
            "reason_codes": signal_data.get("reason_codes", []),
            "dedupe_key": dedupe_key,
            "underlying_price": signal_data.get("underlying_price"),
            "provider": signal_data.get("provider")
        }
        
        # Use SQLite's INSERT OR IGNORE via on_conflict_do_nothing
        stmt = sqlite_insert(Signal).values(**signal_values).on_conflict_do_nothing(
            index_elements=['dedupe_key']
        )
        result = await db.execute(stmt)
        await db.commit()
        
        # Check if a row was inserted
        if result.rowcount == 0:
            return None  # Already exists
        
        # Fetch the newly created signal
        fetch_result = await db.execute(
            select(Signal).where(Signal.dedupe_key == dedupe_key)
        )
        return fetch_result.scalar_one_or_none()
    
    @staticmethod
    async def get_recent_signals(
        db: AsyncSession,
        ticker: Optional[str] = None,
        limit: int = 50
    ) -> List[Signal]:
        """Get recent signals, optionally filtered by ticker."""
        query = select(Signal).order_by(desc(Signal.as_of_ts)).limit(limit)
        
        if ticker:
            query = query.where(Signal.ticker == ticker.upper())
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def record_decision(
        db: AsyncSession,
        signal_id: str,
        user_id: str,
        decision: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SignalUserDecision:
        """
        Record a user's decision on a signal.
        
        Args:
            db: Database session
            signal_id: Signal ID
            user_id: User ID
            decision: "placed", "ignored", "expired", "error"
            metadata: Optional metadata dict
            
        Returns:
            SignalUserDecision object
        """
        decision_record = SignalUserDecision(
            signal_id=signal_id,
            user_id=user_id,
            decision=decision,
            metadata=metadata or {}
        )
        
        db.add(decision_record)
        await db.commit()
        await db.refresh(decision_record)
        
        return decision_record
    
    @staticmethod
    async def get_user_decisions(
        db: AsyncSession,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get user's recent decisions with signal details.
        
        Args:
            db: Database session
            user_id: User ID
            limit: Number of decisions to return
            
        Returns:
            List of decision dictionaries with signal info
        """
        result = await db.execute(
            select(SignalUserDecision, Signal)
            .join(Signal, SignalUserDecision.signal_id == Signal.id)
            .where(SignalUserDecision.user_id == user_id)
            .order_by(desc(SignalUserDecision.decision_ts))
            .limit(limit)
        )
        
        decisions = []
        for decision, signal in result.all():
            decisions.append({
                "ticker": signal.ticker,
                "ff_value": signal.ff_value,
                "front_dte": signal.front_dte,
                "back_dte": signal.back_dte,
                "decision": decision.decision,
                "decision_ts": decision.decision_ts.strftime("%Y-%m-%d %H:%M")
            })
        
        return decisions
