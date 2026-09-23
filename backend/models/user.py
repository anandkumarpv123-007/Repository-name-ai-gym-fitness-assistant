from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.profile import Profile
    from models.workout_session import WorkoutSession
    from models.nutrition import NutritionTarget, NutritionLog, DietPlan
    from models.buddy import BuddyMessage
    from models.habit import HabitPrediction
    from models.planner import WorkoutPlan


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

    # 1-to-1 Relationship: User has one NutritionTarget
    nutrition_target: Mapped["NutritionTarget | None"] = relationship(
        "NutritionTarget",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # 1-to-many Relationship: User has many NutritionLogs
    nutrition_logs: Mapped[List["NutritionLog"]] = relationship(
        "NutritionLog",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # 1-to-many Relationship: User has many DietPlans
    diet_plans: Mapped[List["DietPlan"]] = relationship(
        "DietPlan",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # 1-to-many Relationship: User has many BuddyMessages
    buddy_messages: Mapped[List["BuddyMessage"]] = relationship(
        "BuddyMessage",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # 1-to-many Relationship: User has many HabitPredictions
    habit_predictions: Mapped[List["HabitPrediction"]] = relationship(
        "HabitPrediction",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # 1-to-many Relationship: User has many WorkoutPlans
    workout_plans: Mapped[List["WorkoutPlan"]] = relationship(
        "WorkoutPlan",
        back_populates="user",
        cascade="all, delete-orphan",
    )