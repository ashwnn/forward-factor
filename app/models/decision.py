"""Signal user decision model."""
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base


class SignalUserDecision(Base):
    """User decision on a signal (placed, ignored, etc.)."""
    
    __tablename__ = "signal_user_decisions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signal_id = Column(UUID(as_uuid=True), ForeignKey("signals.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    decision = Column(String, nullable=False)  # placed, ignored, expired, error
    decision_ts = Column(DateTime, default=datetime.utcnow, nullable=False)
    decision_metadata = Column(JSON, default=dict)
    
    # Relationships
    user = relationship("User", back_populates="decisions")