"""Signal user decision model."""
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Float, ForeignKeyConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.core.database import Base


class SignalUserDecision(Base):
    """User decision on a signal (placed, ignored, etc.)."""
    
    __tablename__ = "signal_user_decisions"
    
    # Define table args first for composite foreign key
    __table_args__ = (
        ForeignKeyConstraint(
            ['signal_id', 'signal_as_of_ts'],
            ['signals.id', 'signals.as_of_ts'],
            ondelete='CASCADE',
            name='signal_user_decisions_signal_composite_fkey'
        ),
    )
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Composite foreign key to signals table (id, as_of_ts)
    # Required because signals has composite primary key for TimescaleDB hypertable
    signal_id = Column(String, nullable=False, index=True)
    signal_as_of_ts = Column(DateTime(timezone=True), nullable=False)
    
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    decision = Column(String, nullable=False)  # placed, ignored, expired, error
    decision_ts = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    decision_metadata = Column(JSON, default=dict)
    entry_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    notes = Column(String, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="decisions")