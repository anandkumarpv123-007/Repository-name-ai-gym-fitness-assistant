from datetime import datetime
from typing import TYPE_CHECKING, List
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.user import User
    from models.workout_exercise import WorkoutExercise
    from models.pose_metric import PoseMetric


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    performance_score: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    calories: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    notes: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    # Many-to-1 relationship: Each workout session belongs to one User
    user: Mapped["User"] = relationship(
        "User",
        back_populates="workout_sessions",
    )

    # 1-to-many relationship: One workout session has many workout_exercises
    workout_exercises: Mapped[List["WorkoutExercise"]] = relationship(
        "WorkoutExercise",
        back_populates="workout_session",
        cascade="all, delete-orphan",
    )

    # 1-to-many relationship: One workout session has many pose_metrics
    pose_metrics: Mapped[List["PoseMetric"]] = relationship(
        "PoseMetric",
        back_populates="workout_session",
        cascade="all, delete-orphan",
    )
