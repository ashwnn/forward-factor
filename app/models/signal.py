"""Signal model for storing computed Forward Factor signals."""
from sqlalchemy import Column, String, DateTime, Integer, Float, JSON, Date
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.core.database import Base


class Signal(Base):
    """Signal model representing a computed Forward Factor dislocation."""
    
    __tablename__ = "signals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker = Column(String, nullable=False, index=True)
    as_of_ts = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    front_expiry = Column(Date, nullable=False)
    back_expiry = Column(Date, nullable=False)
    front_dte = Column(Integer, nullable=False)
    back_dte = Column(Integer, nullable=False)
    front_iv = Column(Float, nullable=False)
    back_iv = Column(Float, nullable=False)
    sigma_fwd = Column(Float, nullable=False)
    ff_value = Column(Float, nullable=False, index=True)
    vol_point = Column(String, nullable=False)
    quality_score = Column(Float, nullable=True)
    reason_codes = Column(JSON, default=list)
    dedupe_key = Column(String, unique=True, nullable=False, index=True)
    
    # Snapshot reference
    underlying_price = Column(Float, nullable=True)
    provider = Column(String, nullable=True)


class OptionChainSnapshot(Base):
    """Option chain snapshot from external provider."""
    
    __tablename__ = "option_chain_snapshots"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticker = Column(String, nullable=False, index=True)
    as_of_ts = Column(DateTime, default=datetime.utcnow, nullable=False)
    provider = Column(String, nullable=False)
    underlying_price = Column(Float, nullable=True)
    raw_payload = Column(JSON, nullable=True)
    quality_score = Column(Float, nullable=True)
