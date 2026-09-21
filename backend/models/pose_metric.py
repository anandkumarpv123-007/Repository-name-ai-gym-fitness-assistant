from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.workout_session import WorkoutSession


class PoseMetric(Base):
    """
    Biomechanical pose and performance metrics record for an individual repetition
    within a workout session, matching the master implementation specification.
    """
    __tablename__ = "pose_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workout_session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workout_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rep_number: Mapped[int] = mapped_column(Integer, nullable=False)
    min_knee_angle: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_torso_lean: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    form_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    violations: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metrics_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    workout_session: Mapped["WorkoutSession"] = relationship(
        "WorkoutSession",
        back_populates="pose_metrics",
    )
