"""Master ticker registry model."""
from sqlalchemy import Column, String, Integer, DateTime
from datetime import datetime
from app.core.database import Base


class MasterTicker(Base):
    """Master ticker registry tracking all monitored tickers."""
    
    __tablename__ = "master_tickers"
    
    ticker = Column(String, primary_key=True, index=True)
    active_subscriber_count = Column(Integer, default=0, nullable=False)
    last_scan_at = Column(DateTime(timezone=True), nullable=True)
    scan_tier = Column(String, default="low", nullable=False)  # high, medium, low
