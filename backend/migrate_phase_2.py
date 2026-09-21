"""
Database schema migration for Phase 2:
Adds performance_score, calories, and notes to workout_sessions.
Creates pose_metrics table.
Preserves all existing users, profiles, and exercises.
"""

from sqlalchemy import text
from database import engine, Base
from models import User, Profile, Exercise, WorkoutSession, WorkoutExercise, PoseMetric


def run_migration():
    print("--- Running Phase 2 Database Schema Migration ---")
    with engine.connect() as conn:
        # 1. Add columns to workout_sessions if they don't exist
        print("[1] Checking columns on workout_sessions...")
        conn.execute(text("""
            ALTER TABLE workout_sessions
            ADD COLUMN IF NOT EXISTS performance_score DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS calories DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS notes VARCHAR(255);
        """))
        conn.commit()
        print("  -> OK: workout_sessions columns verified.")

        # 2. Create pose_metrics table if it doesn't exist
        print("[2] Creating pose_metrics table if not exists...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS pose_metrics (
                id SERIAL PRIMARY KEY,
                workout_session_id INTEGER NOT NULL REFERENCES workout_sessions(id) ON DELETE CASCADE,
                rep_number INTEGER NOT NULL,
                min_knee_angle DOUBLE PRECISION,
                max_torso_lean DOUBLE PRECISION,
                duration_seconds DOUBLE PRECISION,
                form_status VARCHAR(50),
                violations VARCHAR(255),
                metrics_json TEXT,
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
            );
            CREATE INDEX IF NOT EXISTS ix_pose_metrics_workout_session_id ON pose_metrics(workout_session_id);
            CREATE INDEX IF NOT EXISTS ix_pose_metrics_id ON pose_metrics(id);
        """))
        conn.commit()
        print("  -> OK: pose_metrics table verified.")

        # 3. Verify row counts on existing tables
        user_count = conn.execute(text("SELECT count(*) FROM users")).scalar()
        profile_count = conn.execute(text("SELECT count(*) FROM profiles")).scalar()
        exercise_count = conn.execute(text("SELECT count(*) FROM exercises")).scalar()
        session_count = conn.execute(text("SELECT count(*) FROM workout_sessions")).scalar()

        print(f"[3] Data integrity check:")
        print(f"    users: {user_count}")
        print(f"    profiles: {profile_count}")
        print(f"    exercises: {exercise_count}")
        print(f"    workout_sessions: {session_count}")
        print("--- Phase 2 Database Migration Complete ---")


if __name__ == "__main__":
    run_migration()
