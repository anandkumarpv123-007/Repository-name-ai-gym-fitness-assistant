from typing import TYPE_CHECKING
from sqlalchemy import CheckConstraint, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.workout_session import WorkoutSession
    from models.exercise import Exercise


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"
    __table_args__ = (
        CheckConstraint("sets >= 0", name="check_sets_non_negative"),
        CheckConstraint("reps >= 0", name="check_reps_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workout_session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("workout_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Safe non-destructive deletion: Deleting a catalogue exercise is RESTRICTED if workout history exists
    exercise_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("exercises.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sets: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)

    # Many-to-1 relationship: Each workout exercise record belongs to one WorkoutSession
    workout_session: Mapped["WorkoutSession"] = relationship(
        "WorkoutSession",
        back_populates="workout_exercises",
    )

    # Many-to-1 relationship: Each workout exercise record belongs to one Exercise
    exercise: Mapped["Exercise"] = relationship(
        "Exercise",
        back_populates="workout_exercises",
    )
