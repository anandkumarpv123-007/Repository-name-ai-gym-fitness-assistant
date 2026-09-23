from datetime import datetime
from typing import Optional, List
from sqlalchemy import DateTime, Float, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Gym(Base):
    """
    Gym catalogue entity storing facility metadata, equipment lists,
    price tiers, location details, and supported workout types.
    """
    __tablename__ = "gyms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), default="Metro City", nullable=False)
    price_category: Mapped[str] = mapped_column(String(30), default="mid_tier", nullable=False)  # "budget", "mid_tier", "premium"
    rating: Mapped[float] = mapped_column(Float, default=4.5, nullable=False)
    opening_hours: Mapped[str] = mapped_column(String(100), default="06:00 AM - 10:00 PM", nullable=False)
    facilities_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON string list
    equipment_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)   # JSON string list
    supported_workout_types_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON string list
    is_verified_sample: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
