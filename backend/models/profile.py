from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.user import User


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    date_of_birth: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    gender: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    height_cm: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    weight_kg: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )

    fitness_goal: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    activity_level: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    dietary_preference: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    # Each Profile belongs to one User
    user: Mapped["User"] = relationship(
        "User",
        back_populates="profile"
    )
