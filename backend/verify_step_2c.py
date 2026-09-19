import asyncio
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode

# Setup paths
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from database import SessionLocal
from models.user import User
from models.profile import Profile
from main import app
from auth.security import hash_password
from auth.token import create_access_token


async def asgi_client(method: str, path: str, headers: dict = None, body=None, form_data: dict = None):
    """Zero-dependency ASGI HTTP client for testing FastAPI application."""
    headers = headers or {}
    formatted_headers = []
    
    body_bytes = b""
    if form_data is not None:
        body_bytes = urlencode(form_data).encode("utf-8")
        headers["content-type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        if isinstance(body, (dict, list)):
            body_bytes = json.dumps(body).encode("utf-8")
            headers["content-type"] = "application/json"
        elif isinstance(body, str):
            body_bytes = body.encode("utf-8")
        elif isinstance(body, bytes):
            body_bytes = body

    headers["content-length"] = str(len(body_bytes))
    headers["host"] = "testserver"

    for k, v in headers.items():
        formatted_headers.append((k.lower().encode("latin1"), v.encode("latin1")))

    status_code = 0
    response_headers = []
    response_body = []

    async def receive():
        return {
            "type": "http.request",
            "body": body_bytes,
            "more_body": False
        }

    async def send(message):
        nonlocal status_code, response_headers, response_body
        if message["type"] == "http.response.start":
            status_code = message["status"]
            response_headers = message.get("headers", [])
        elif message["type"] == "http.response.body":
            response_body.append(message.get("body", b""))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": formatted_headers,
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }

    await app(scope, receive, send)

    raw_text = b"".join(response_body).decode("utf-8")
    try:
        json_data = json.loads(raw_text)
    except Exception:
        json_data = raw_text

    return status_code, json_data


async def run_step_2c_tests():
    print("=" * 65)
    print("STEP 2C — AUTH / PROFILE API MIGRATION VERIFICATION")
    print("=" * 65)

    db = SessionLocal()
    test_user_email = "step2c_temp_user@example.com"
    test_pwd = "TestPassword123!"

    try:
        # Clean up any leftover test user from prior aborted runs
        existing = db.query(User).filter(User.email == test_user_email).first()
        if existing:
            db.delete(existing)
            db.commit()

        # -------------------------------------------------------------
        # TEST 1: Invalid JWT returns 401 Unauthorized
        # -------------------------------------------------------------
        print("\n[TEST 1] Verifying invalid / missing JWT handling (401 Unauthorized)...")
        status, resp = await asgi_client("GET", "/users/me", headers={"Authorization": "Bearer invalid_token_12345"})
        print(f"  GET /users/me with invalid token: Status {status} -> {resp}")
        assert status == 401, f"Expected 401, got {status}"

        status_alias, resp_alias = await asgi_client("GET", "/auth/me", headers={"Authorization": "Bearer invalid_token_12345"})
        print(f"  GET /auth/me with invalid token: Status {status_alias} -> {resp_alias}")
        assert status_alias == 401, f"Expected 401, got {status_alias}"
        print("  -> PASS: Both endpoints rejected invalid JWT with 401.")

        # -------------------------------------------------------------
        # TEST 2: User registration and authentication preserves JWT
        # -------------------------------------------------------------
        print("\n[TEST 2] Verifying User Registration and Login flow...")
        status, reg_resp = await asgi_client("POST", "/auth/register", body={
            "name": "Step2C User",
            "email": test_user_email,
            "password": test_pwd
        })
        print(f"  POST /auth/register: Status {status} -> {reg_resp}")
        assert status == 200, f"Registration failed with status {status}: {reg_resp}"
        new_user_id = reg_resp["id"]

        # Login via Form data
        status, login_resp = await asgi_client("POST", "/auth/login", form_data={
            "username": test_user_email,
            "password": test_pwd
        })
        print(f"  POST /auth/login: Status {status} -> Token received: {bool(login_resp.get('access_token'))}")
        assert status == 200, f"Login failed: {login_resp}"
        token = login_resp["access_token"]
        auth_header = {"Authorization": f"Bearer {token}"}
        print("  -> PASS: Registration and Login work seamlessly.")

        # -------------------------------------------------------------
        # TEST 3: User without profile can GET profile (returns null fields)
        # -------------------------------------------------------------
        print("\n[TEST 3] Verifying User without Profile can GET profile...")
        status, me_resp = await asgi_client("GET", "/users/me", headers=auth_header)
        print(f"  GET /users/me: Status {status} -> {me_resp}")
        assert status == 200
        assert me_resp["id"] == new_user_id
        assert me_resp["email"] == test_user_email
        assert me_resp["height_cm"] is None
        assert me_resp["weight_kg"] is None
        print("  -> PASS: GET /users/me correctly read current_user.profile as None without error.")

        # -------------------------------------------------------------
        # TEST 4: User without profile can CREATE profile via UPDATE endpoint
        # -------------------------------------------------------------
        print("\n[TEST 4] Verifying User without Profile can CREATE profile via PUT...")
        profile_data = {
            "gender": "male",
            "height_cm": 182.5,
            "weight_kg": 76.0,
            "fitness_goal": "endurance",
            "activity_level": "very_active",
            "dietary_preference": "vegetarian"
        }
        status, update_resp = await asgi_client("PUT", "/users/me", headers=auth_header, body=profile_data)
        print(f"  PUT /users/me: Status {status} -> {update_resp}")
        assert status == 200
        assert update_resp["profile"]["height_cm"] == 182.5
        assert update_resp["profile"]["fitness_goal"] == "endurance"

        # Verify in database that Profile row was created
        db.expire_all()
        created_profile = db.query(Profile).filter(Profile.user_id == new_user_id).first()
        assert created_profile is not None, "Profile was not created in database!"
        assert created_profile.height_cm == 182.5
        print(f"  -> PASS: Profile created with user_id={created_profile.user_id}, height={created_profile.height_cm}cm.")

        # -------------------------------------------------------------
        # TEST 5: Repeated UPDATE updates existing profile & does NOT duplicate
        # -------------------------------------------------------------
        print("\n[TEST 5] Verifying repeated UPDATE updates existing profile without duplicates...")
        update2_data = {
            "weight_kg": 78.0,
            "fitness_goal": "strength"
        }
        status, update2_resp = await asgi_client("PUT", "/users/me", headers=auth_header, body=update2_data)
        print(f"  PUT /users/me (repeat): Status {status} -> {update2_resp}")
        assert status == 200
        assert update2_resp["profile"]["weight_kg"] == 78.0
        assert update2_resp["profile"]["fitness_goal"] == "strength"

        # Check database profile count for this user
        profile_count_for_user = db.query(Profile).filter(Profile.user_id == new_user_id).count()
        print(f"  Profiles count for user {new_user_id} in DB: {profile_count_for_user}")
        assert profile_count_for_user == 1, f"Expected exactly 1 profile, found {profile_count_for_user}!"
        print("  -> PASS: Profile updated in place. Exactly 1 profile exists.")

        # -------------------------------------------------------------
        # TEST 6: Compatibility endpoints (/auth/me and /auth/profile)
        # -------------------------------------------------------------
        print("\n[TEST 6] Verifying compatibility endpoints (/auth/me and /auth/profile)...")
        status, auth_me_resp = await asgi_client("GET", "/auth/me", headers=auth_header)
        assert status == 200
        assert auth_me_resp["weight_kg"] == 78.0
        assert auth_me_resp["fitness_goal"] == "strength"
        print(f"  GET /auth/me: Status {status} -> matches current_user.profile")

        status, auth_prof_resp = await asgi_client("PUT", "/auth/profile", headers=auth_header, body={"weight_kg": 78.5})
        assert status == 200
        assert auth_prof_resp["profile"]["weight_kg"] == 78.5
        print(f"  PUT /auth/profile: Status {status} -> successfully updated profile")
        print("  -> PASS: Compatibility aliases function identically.")

        # -------------------------------------------------------------
        # TEST 7: Existing User 2 with pre-existing profile
        # -------------------------------------------------------------
        print("\n[TEST 7] Verifying pre-existing user (User ID 2) with profile...")
        user2 = db.query(User).filter(User.id == 2).first()
        if user2:
            token2 = create_access_token(user2.id)
            auth_header2 = {"Authorization": f"Bearer {token2}"}
            status, u2_resp = await asgi_client("GET", "/users/me", headers=auth_header2)
            print(f"  GET /users/me for User 2: Status {status} -> {u2_resp}")
            assert status == 200
            assert u2_resp["id"] == 2
            assert u2_resp["email"] == user2.email
            assert u2_resp["height_cm"] == 175.0
            print("  -> PASS: Pre-existing user profile retrieved accurately.")

        # -------------------------------------------------------------
        # TEST 8: Live Database Consistency Checks
        # -------------------------------------------------------------
        print("\n[TEST 8] Database Consistency & Constraint Verification...")
        total_users = db.query(User).count()
        total_profiles = db.query(Profile).count()
        print(f"  Total users in DB: {total_users}")
        print(f"  Total profiles in DB: {total_profiles}")

        # Check unique constraint: exactly one profile per user
        from sqlalchemy import func
        duplicates = (
            db.query(Profile.user_id, func.count(Profile.user_id))
            .group_by(Profile.user_id)
            .having(func.count(Profile.user_id) > 1)
            .all()
        )
        print(f"  Duplicate profiles detected: {len(duplicates)}")
        assert len(duplicates) == 0, f"Found duplicate profiles: {duplicates}"

        # Verify old profile columns still present in users table
        import psycopg
        load_conn = os.getenv("DATABASE_URL").replace("+psycopg", "")
        with psycopg.connect(load_conn) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name IN ('height_cm', 'weight_kg', 'fitness_goal');
                """)
                old_cols = cur.fetchall()
                print(f"  Legacy columns in users table: {[c[0] for c in old_cols]}")
                assert len(old_cols) == 3, "Legacy columns were unexpectedly removed from users table!"

        print("  -> PASS: Database integrity verified, legacy columns intact, no duplicates.")

        # Cleanup test user
        print("\n[CLEANUP] Cleaning up temporary test user...")
        user_to_clean = db.query(User).filter(User.id == new_user_id).first()
        if user_to_clean:
            db.delete(user_to_clean)
            db.commit()
        print("  -> Cleanup complete.")

        print("\n" + "=" * 65)
        print("[ALL STEP 2C VERIFICATIONS PASSED SUCCESSFULLY]")
        print("=" * 65)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run_step_2c_tests())
