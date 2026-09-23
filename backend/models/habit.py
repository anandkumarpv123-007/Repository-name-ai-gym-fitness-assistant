from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.user import User


class HabitPrediction(Base):
    """
    Stores behavioral prediction telemetry and snapshot history for a user over time.
    """
    __tablename__ = "habit_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    
    prediction_date: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Predicted probability of skipping next expected workout window [0.00, 1.00]
    skip_probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # "low", "moderate", "high", or "insufficient_data"
    risk_level: Mapped[str] = mapped_column(String(30), default="insufficient_data", nullable=False)
    
    # Primary behavioral factor associated with prediction
    primary_factor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Grounded non-medical behavioral nudge text
    nudge_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Evidence-based historical schedule recommendation text
    recommended_schedule: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationship back to User
    user: Mapped["User"] = relationship("User", back_populates="habit_predictions")
