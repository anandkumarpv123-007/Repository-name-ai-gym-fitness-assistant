import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from database import SessionLocal
from models import User, Profile

def run_step_2b_verifications():
    print("=" * 60)
    print("STEP 2B — SQLALCHEMY MODEL VERIFICATION")
    print("=" * 60)

    db = SessionLocal()
    try:
        # 1. Verify User and Profile loading
        users = db.query(User).order_by(User.id).all()
        profiles = db.query(Profile).order_by(Profile.user_id).all()

        print(f"1. Loading Models:")
        print(f"   - Total User objects loaded: {len(users)}")
        print(f"   - Total Profile objects loaded: {len(profiles)}")
        assert len(users) > 0, "No users found in database!"
        assert len(profiles) > 0, "No profiles found in database!"

        # 2. Verify User -> Profile (1-to-1) relationship navigation
        print(f"\n2. Verifying User -> Profile Relationship:")
        for user in users:
            assert hasattr(user, "profile"), f"User {user.id} missing 'profile' attribute!"
            print(f"   - User ID {user.id} ({user.name}, email: {user.email})")
            if user.profile:
                print(f"     -> Profile attached: user_id={user.profile.user_id}, height={user.profile.height_cm}cm, weight={user.profile.weight_kg}kg, goal={user.profile.fitness_goal}")
                assert user.profile.user_id == user.id, f"Profile user_id mismatch! Expected {user.id}, got {user.profile.user_id}"
            else:
                print(f"     -> [WARN] No profile record found for user {user.id}")

        # 3. Verify Profile -> User back-reference
        print(f"\n3. Verifying Profile -> User Back-Reference:")
        for profile in profiles:
            assert hasattr(profile, "user"), f"Profile {profile.user_id} missing 'user' attribute!"
            assert profile.user is not None, f"Profile {profile.user_id} has None for .user!"
            assert profile.user.id == profile.user_id, f"Back-reference ID mismatch! Profile user_id={profile.user_id}, User id={profile.user.id}"
            print(f"   - Profile user_id={profile.user_id} belongs to User {profile.user.name} ({profile.user.email})")

        # 4. Verify specific user data parity (User 2 test data)
        user2 = db.query(User).filter(User.id == 2).first()
        if user2:
            print(f"\n4. Verifying Known User 2 Data Parity:")
            print(f"   - user2.profile.height_cm: {user2.profile.height_cm} (Expected 175.0)")
            print(f"   - user2.profile.weight_kg: {user2.profile.weight_kg} (Expected 70.0)")
            print(f"   - user2.profile.fitness_goal: {user2.profile.fitness_goal} (Expected 'muscle_gain')")
            assert user2.profile.height_cm == 175.0, f"Expected 175.0, got {user2.profile.height_cm}"
            assert user2.profile.weight_kg == 70.0, f"Expected 70.0, got {user2.profile.weight_kg}"
            assert user2.profile.fitness_goal == "muscle_gain", f"Expected 'muscle_gain', got {user2.profile.fitness_goal}"

            # Test backward compatibility delegation
            print(f"   - user2.height_cm property delegation: {user2.height_cm}")
            assert user2.height_cm == 175.0, "Backward-compatibility property delegation failed!"

        # 5. Verify existing router imports still work cleanly
        print(f"\n5. Verifying Existing Application Router Imports:")
        from routers.auth import router as auth_router
        from routers.health import router as health_router
        print(f"   - auth_router imported cleanly: {auth_router.prefix}")
        print(f"   - health_router imported cleanly: {health_router.prefix if hasattr(health_router, 'prefix') else 'health'}")

        print("\n" + "=" * 60)
        print("[ALL STEP 2B VERIFICATIONS PASSED SUCCESSFULLY]")
        print("=" * 60)

    finally:
        db.close()

if __name__ == "__main__":
    run_step_2b_verifications()
