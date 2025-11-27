"""Signal model for storing computed Forward Factor signals."""
from sqlalchemy import Column, String, DateTime, Integer, Float, JSON, Date, Boolean
from datetime import datetime, timezone
import uuid
from app.core.database import Base


class Signal(Base):
    """Signal model representing a computed Forward Factor dislocation."""
    
    __tablename__ = "signals"
    
    # Composite primary key for TimescaleDB hypertable
    # TimescaleDB requires partitioning column (as_of_ts) to be part of primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    as_of_ts = Column(DateTime, primary_key=True, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    ticker = Column(String, nullable=False, index=True)
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
    dedupe_key = Column(String, nullable=False, index=True)
    is_discovery = Column(Boolean, default=False, nullable=False)  # Whether this signal came from discovery mode
    
    # Snapshot reference
    underlying_price = Column(Float, nullable=True)
    provider = Column(String, nullable=True)


class OptionChainSnapshot(Base):
    """Option chain snapshot from external provider."""
    
    __tablename__ = "option_chain_snapshots"
    
    # Composite primary key for TimescaleDB hypertable
    # TimescaleDB requires partitioning column (as_of_ts) to be part of primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    as_of_ts = Column(DateTime, primary_key=True, default=lambda: datetime.now(timezone.utc), nullable=False)
    ticker = Column(String, nullable=False, index=True)
    provider = Column(String, nullable=False)
    underlying_price = Column(Float, nullable=True)
    raw_payload = Column(JSON, nullable=True)
    quality_score = Column(Float, nullable=True)
