from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.user import User


class BuddyMessage(Base):
    __tablename__ = "buddy_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    
    # "user" or "assistant"
    sender: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Raw conversation text
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Provider used for response: "llm_gemini", "llm_openai", "deterministic_buddy_fallback", "system_safety"
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationship back to User
    user: Mapped["User"] = relationship("User", back_populates="buddy_messages")
