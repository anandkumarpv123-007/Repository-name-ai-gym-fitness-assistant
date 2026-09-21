from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.profile import Profile
    from models.workout_session import WorkoutSession


class User(Base):
    __tablename__ = "users"

    # Core authentication & account fields
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # 1-to-1 Relationship: User has one Profile
    profile: Mapped["Profile | None"] = relationship(
        "Profile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # 1-to-many Relationship: User has many WorkoutSessions
    workout_sessions: Mapped[List["WorkoutSession"]] = relationship(
        "WorkoutSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
