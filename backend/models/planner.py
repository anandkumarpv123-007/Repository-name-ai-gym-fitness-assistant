from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.user import User


class WorkoutPlan(Base):
    """
    Stores generated weekly workout plans for users, incorporating
    goal orientation, Phase 3 performance feedback, and Phase 6 habit adaptivity.
    """
    __tablename__ = "workout_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    plan_name: Mapped[str] = mapped_column(String(200), nullable=False)
    fitness_goal: Mapped[str] = mapped_column(String(50), nullable=False)
    target_split: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Push/Pull/Legs", "Upper/Lower"
    days_per_week: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    habit_adapted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    performance_adapted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    adaptation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="workout_plans")
    items: Mapped[List["WorkoutPlanItem"]] = relationship(
        "WorkoutPlanItem",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="WorkoutPlanItem.id.asc()",
    )


class WorkoutPlanItem(Base):
    """
    Represents a single day schedule item within a weekly workout plan.
    """
    __tablename__ = "workout_plan_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workout_plans.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    day_of_week: Mapped[str] = mapped_column(String(20), nullable=False)  # "Monday".."Sunday"
    day_title: Mapped[str] = mapped_column(String(100), nullable=False)   # e.g. "Upper Body Strength", "Rest & Recovery"
    is_rest_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    target_muscle_groups: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    exercises_json: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON string list of exercises
    warmup_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship back to WorkoutPlan
    plan: Mapped["WorkoutPlan"] = relationship("WorkoutPlan", back_populates="items")
