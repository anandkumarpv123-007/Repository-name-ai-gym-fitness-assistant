import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from database import SessionLocal
from models.exercise import Exercise

INITIAL_EXERCISES = [
    {
        "name": "Squat",
        "category": "Legs",
        "description": "Lower-body compound exercise targeting quadriceps, hamstrings, and glutes.",
    },
    {
        "name": "Push-up",
        "category": "Chest",
        "description": "Upper-body bodyweight exercise targeting chest, shoulders, and triceps.",
    },
    {
        "name": "Bicep Curl",
        "category": "Arms",
        "description": "Isolation exercise targeting the biceps brachii via elbow flexion.",
    },
]


def seed_exercises():
    """Idempotent seed function to populate default exercises."""
    db = SessionLocal()
    try:
        added_count = 0
        existing_count = 0

        for item in INITIAL_EXERCISES:
            existing = db.query(Exercise).filter(Exercise.name == item["name"]).first()
            if not existing:
                exercise = Exercise(
                    name=item["name"],
                    category=item["category"],
                    description=item["description"],
                )
                db.add(exercise)
                added_count += 1
                print(f"[SEED] Added exercise: {item['name']} ({item['category']})")
            else:
                existing_count += 1
                print(f"[SEED] Exercise already exists: {item['name']} (skipped)")

        if added_count > 0:
            db.commit()
            print(f"[SUCCESS] Seeded {added_count} new exercise(s).")
        else:
            print("[INFO] All seed exercises already present. Zero duplicates created.")

    finally:
        db.close()


if __name__ == "__main__":
    seed_exercises()
