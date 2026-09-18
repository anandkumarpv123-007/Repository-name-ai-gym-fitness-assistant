from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))

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

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )