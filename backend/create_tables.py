from database import Base, engine
from models import (
    User,
    Profile,
    Exercise,
    WorkoutSession,
    WorkoutExercise,
    PoseMetric,
    NutritionTarget,
    NutritionLog,
    DietPlan,
    BuddyMessage,
    HabitPrediction,
    Gym,
    WorkoutPlan,
    WorkoutPlanItem,
    IoTDevice,
    IoTTelemetry,
    IoTCommandLog,
)

from sqlalchemy import text

Base.metadata.create_all(bind=engine)

# Migration helper for Phase 8 gym_id column
with engine.connect() as conn:
    conn.execute(text("ALTER TABLE iot_devices ADD COLUMN IF NOT EXISTS gym_id INTEGER DEFAULT 1;"))
    conn.commit()

print("Database tables created successfully!")