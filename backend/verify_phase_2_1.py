import sys
from datetime import datetime, timezone
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from database import SessionLocal
from models import User, Profile, Exercise, WorkoutSession, WorkoutExercise
from seed_exercises import seed_exercises
from sqlalchemy.exc import IntegrityError


def run_phase_2_1_tests():
    print("=" * 70)
    print("PHASE 2.1 — EXERCISE CATALOGUE & WORKOUT SESSION MODEL VERIFICATION")
    print("=" * 70)

    db = SessionLocal()
    temp_session_id = None

    try:
        # -------------------------------------------------------------
        # TEST 1: Exercise can be read / queried
        # -------------------------------------------------------------
        print("\n[TEST 1] Verifying Exercise catalogue queries...")
        exercises = db.query(Exercise).order_by(Exercise.id).all()
        print(f"  Total exercises found: {len(exercises)}")
        for ex in exercises:
            print(f"   - [{ex.id}] {ex.name} ({ex.category}): {ex.description}")
        assert len(exercises) >= 3, f"Expected at least 3 exercises, found {len(exercises)}"
        squat = db.query(Exercise).filter(Exercise.name == "Squat").first()
        assert squat is not None, "Squat exercise not found!"
        print("  -> PASS: Exercise catalogue read successfully.")

        # -------------------------------------------------------------
        # TEST 2: Existing users and profiles are preserved
        # -------------------------------------------------------------
        print("\n[TEST 2] Verifying existing users & profiles integrity...")
        users = db.query(User).order_by(User.id).all()
        profiles = db.query(Profile).order_by(Profile.user_id).all()
        print(f"  Existing users count: {len(users)}")
        print(f"  Existing profiles count: {len(profiles)}")
        assert len(users) == 2, f"Expected 2 users, found {len(users)}"
        assert len(profiles) == 2, f"Expected 2 profiles, found {len(profiles)}"
        user2 = db.query(User).filter(User.id == 2).first()
        assert user2 is not None, "User 2 not found!"
        assert user2.profile is not None, "User 2 profile not found!"
        assert user2.profile.height_cm == 175.0
        print("  -> PASS: Existing users and profiles 100% intact.")

        # -------------------------------------------------------------
        # TEST 3: Workout session can reference an existing user
        # -------------------------------------------------------------
        print("\n[TEST 3] Creating WorkoutSession referencing User 2...")
        session = WorkoutSession(
            user_id=user2.id,
            started_at=datetime.now(timezone.utc),
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        temp_session_id = session.id
        print(f"  Created WorkoutSession ID: {session.id} for User ID: {session.user_id}")
        assert session.id is not None
        assert session.user_id == user2.id
        print("  -> PASS: WorkoutSession created referencing User.")

        # -------------------------------------------------------------
        # TEST 4: WorkoutExercise can reference WorkoutSession and Exercise
        # -------------------------------------------------------------
        print("\n[TEST 4] Creating WorkoutExercise referencing Session and Exercise...")
        we = WorkoutExercise(
            workout_session_id=session.id,
            exercise_id=squat.id,
            sets=3,
            reps=10,
        )
        db.add(we)
        db.commit()
        db.refresh(we)
        print(f"  Created WorkoutExercise ID: {we.id} (Session: {we.workout_session_id}, Exercise: {we.exercise_id}, Sets: {we.sets}, Reps: {we.reps})")
        assert we.id is not None
        assert we.workout_session_id == session.id
        assert we.exercise_id == squat.id
        print("  -> PASS: WorkoutExercise created referencing Session and Exercise.")

        # -------------------------------------------------------------
        # TEST 5: Bidirectional relationship navigation
        # -------------------------------------------------------------
        print("\n[TEST 5] Verifying bidirectional SQLAlchemy relationships...")
        db.expire_all()

        loaded_session = db.query(WorkoutSession).filter(WorkoutSession.id == session.id).first()
        # Session -> User
        assert loaded_session.user.id == user2.id
        print(f"  loaded_session.user: {loaded_session.user.name} ({loaded_session.user.email})")

        # Session -> WorkoutExercises
        assert len(loaded_session.workout_exercises) == 1
        loaded_we = loaded_session.workout_exercises[0]
        print(f"  loaded_session.workout_exercises[0]: exercise_id={loaded_we.exercise_id}, reps={loaded_we.reps}")

        # WorkoutExercise -> Exercise
        assert loaded_we.exercise.name == "Squat"
        print(f"  loaded_we.exercise: {loaded_we.exercise.name} ({loaded_we.exercise.category})")

        # User -> WorkoutSessions
        loaded_user = db.query(User).filter(User.id == user2.id).first()
        user_session_ids = [s.id for s in loaded_user.workout_sessions]
        assert session.id in user_session_ids
        print(f"  loaded_user.workout_sessions contains session {session.id}: {session.id in user_session_ids}")

        # Exercise -> WorkoutExercises
        loaded_exercise = db.query(Exercise).filter(Exercise.id == squat.id).first()
        ex_we_ids = [item.id for item in loaded_exercise.workout_exercises]
        assert we.id in ex_we_ids
        print(f"  loaded_exercise.workout_exercises contains record {we.id}: {we.id in ex_we_ids}")

        print("  -> PASS: All bidirectional relationships verified.")

        # -------------------------------------------------------------
        # TEST 6: Foreign key violation rejection
        # -------------------------------------------------------------
        print("\n[TEST 6] Verifying foreign key constraint enforcement...")
        invalid_session = WorkoutSession(
            user_id=9999999,  # Non-existent user ID
            started_at=datetime.now(timezone.utc),
        )
        db.add(invalid_session)
        try:
            db.commit()
            raise AssertionError("Database allowed invalid user_id foreign key!")
        except IntegrityError:
            db.rollback()
            print("  -> PASS: Invalid user_id in WorkoutSession correctly rejected by ForeignKey constraint.")

        invalid_we = WorkoutExercise(
            workout_session_id=session.id,
            exercise_id=9999999,  # Non-existent exercise ID
            sets=1,
            reps=10,
        )
        db.add(invalid_we)
        try:
            db.commit()
            raise AssertionError("Database allowed invalid exercise_id foreign key!")
        except IntegrityError:
            db.rollback()
            print("  -> PASS: Invalid exercise_id in WorkoutExercise correctly rejected by ForeignKey constraint.")

        # -------------------------------------------------------------
        # TEST 7: Safe Deletion Behavior (ON DELETE RESTRICT on exercises)
        # -------------------------------------------------------------
        print("\n[TEST 7] Verifying ON DELETE RESTRICT prevents deleting exercises with existing workout history...")
        try:
            db.delete(squat)
            db.commit()
            raise AssertionError("Database allowed deleting exercise that has active workout history!")
        except IntegrityError:
            db.rollback()
            print("  -> PASS: Attempt to delete exercise with workout history was safely BLOCKED by ON DELETE RESTRICT.")

        # -------------------------------------------------------------
        # TEST 8: Non-negative sets & reps check constraint enforcement
        # -------------------------------------------------------------
        print("\n[TEST 8] Verifying non-negative check constraints on sets and reps...")
        # Negative sets
        negative_sets_we = WorkoutExercise(
            workout_session_id=session.id,
            exercise_id=squat.id,
            sets=-1,
            reps=10,
        )
        db.add(negative_sets_we)
        try:
            db.commit()
            raise AssertionError("Database allowed negative sets (-1)!")
        except IntegrityError:
            db.rollback()
            print("  -> PASS: Negative sets (-1) correctly rejected by check constraint.")

        # Negative reps
        negative_reps_we = WorkoutExercise(
            workout_session_id=session.id,
            exercise_id=squat.id,
            sets=3,
            reps=-5,
        )
        db.add(negative_reps_we)
        try:
            db.commit()
            raise AssertionError("Database allowed negative reps (-5)!")
        except IntegrityError:
            db.rollback()
            print("  -> PASS: Negative reps (-5) correctly rejected by check constraint.")

        # -------------------------------------------------------------
        # TEST 9: Duplicate seed execution does not create duplicate exercises
        # -------------------------------------------------------------
        print("\n[TEST 9] Verifying idempotent seed execution...")
        seed_exercises()
        final_exercises = db.query(Exercise).all()
        assert len(final_exercises) == len(exercises), f"Exercise count changed! {len(final_exercises)} vs {len(exercises)}"
        print(f"  Exercise count remains stable: {len(final_exercises)}")
        print("  -> PASS: Zero duplicate exercises created on repeated seed.")

        # -------------------------------------------------------------
        # CLEANUP: Delete temporary test session (cascade deletes test workout_exercise)
        # -------------------------------------------------------------
        print("\n[CLEANUP] Cleaning up test workout session...")
        if temp_session_id:
            s_to_del = db.query(WorkoutSession).filter(WorkoutSession.id == temp_session_id).first()
            if s_to_del:
                db.delete(s_to_del)
                db.commit()
                print(f"  Deleted test WorkoutSession ID {temp_session_id} (and cascaded workout_exercises).")

        # Verify test workout exercise was cascade-deleted
        remaining_we = db.query(WorkoutExercise).filter(WorkoutExercise.workout_session_id == temp_session_id).count()
        assert remaining_we == 0
        print("  -> PASS: Cleanup complete. No residual test workout data left.")

        print("\n" + "=" * 70)
        print("[ALL PHASE 2.1 VERIFICATION CHECKS PASSED WITH ZERO ERRORS]")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    run_phase_2_1_tests()
