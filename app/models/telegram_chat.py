"""Telegram chat model for tracking multiple chats per user."""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.core.database import Base


class TelegramChat(Base):
    """Model to track multiple Telegram chats linked to a user."""
    
    __tablename__ = "telegram_chats"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    chat_id = Column(String, nullable=False, unique=True, index=True)
    first_name = Column(String, nullable=False)  # Always available from Telegram
    last_name = Column(String, nullable=True)    # Optional in Telegram
    username = Column(String, nullable=True)      # Optional in Telegram
    linked_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationship
    user = relationship("User", back_populates="telegram_chats")
