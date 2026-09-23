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
)

Base.metadata.create_all(bind=engine)

print("Database tables created successfully!")