import asyncio
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode

# Setup path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from database import SessionLocal
from models.user import User
from models.profile import Profile
from main import app
from auth.token import create_access_token
import psycopg


async def asgi_request(method: str, path: str, headers: dict = None, body=None, form_data: dict = None):
    """Zero-dependency ASGI HTTP client."""
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
    response_body = []

    async def receive():
        return {
            "type": "http.request",
            "body": body_bytes,
            "more_body": False
        }

    async def send(message):
        nonlocal status_code, response_body
        if message["type"] == "http.response.start":
            status_code = message["status"]
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
        data = json.loads(raw_text)
    except Exception:
        data = raw_text

    return status_code, data


async def run_step_2d_verification():
    print("=" * 70)
    print("STEP 2D — USER/PROFILE FOUNDATION CLEANUP & COMPLETE VERIFICATION")
    print("=" * 70)

    db = SessionLocal()
    test_email = "step2d_verify_user@example.com"
    test_password = "VerificationSecret123!"
    temp_user_id = None

    try:
        # 1. Clean up any lingering test user
        old_test = db.query(User).filter(User.email == test_email).first()
        if old_test:
            db.delete(old_test)
            db.commit()

        # -------------------------------------------------------------
        # CHECK 1: Server startup & Root endpoint (GET /)
        # -------------------------------------------------------------
        print("\n[CHECK 1] Testing Server root endpoint (GET /)...")
        status, body = await asgi_request("GET", "/")
        print(f"  GET / -> Status: {status}, Body: {body}")
        assert status == 200, f"Root returned {status}"
        assert body.get("message") == "AI Gym & Fitness Assistant API is running"
        print("  -> PASS: Root endpoint verified.")

        # -------------------------------------------------------------
        # CHECK 2: Health router (GET /health)
        # -------------------------------------------------------------
        print("\n[CHECK 2] Testing Health endpoint (GET /health)...")
        status, body = await asgi_request("GET", "/health")
        print(f"  GET /health -> Status: {status}, Body: {body}")
        assert status == 200, f"Health returned {status}"
        assert body.get("status") == "healthy"
        print("  -> PASS: Health check verified.")

        # -------------------------------------------------------------
        # CHECK 3: User Registration (POST /auth/register)
        # -------------------------------------------------------------
        print("\n[CHECK 3] Testing User Registration (POST /auth/register)...")
        status, body = await asgi_request("POST", "/auth/register", body={
            "name": "Step 2D Tester",
            "email": test_email,
            "password": test_password
        })
        print(f"  POST /auth/register -> Status: {status}, Response: {body}")
        assert status == 200, f"Register failed with {status}: {body}"
        temp_user_id = body["id"]
        assert body["email"] == test_email
        print(f"  -> PASS: User registered with ID {temp_user_id}.")

        # -------------------------------------------------------------
        # CHECK 4: User Login (POST /auth/login)
        # -------------------------------------------------------------
        print("\n[CHECK 4] Testing User Login (POST /auth/login)...")
        status, body = await asgi_request("POST", "/auth/login", form_data={
            "username": test_email,
            "password": test_password
        })
        print(f"  POST /auth/login -> Status: {status}, Token present: {bool(body.get('access_token'))}")
        assert status == 200, f"Login failed: {body}"
        token = body["access_token"]
        auth_header = {"Authorization": f"Bearer {token}"}
        print("  -> PASS: Login successful and JWT token received.")

        # -------------------------------------------------------------
        # CHECK 5: Invalid JWT handling (Expect 401)
        # -------------------------------------------------------------
        print("\n[CHECK 5] Testing Invalid JWT rejection...")
        status, body = await asgi_request("GET", "/users/me", headers={"Authorization": "Bearer fake.tampered.token"})
        print(f"  GET /users/me with bad token -> Status: {status}, Detail: {body}")
        assert status == 401, f"Expected 401, got {status}"
        status_compat, body_compat = await asgi_request("GET", "/auth/me", headers={"Authorization": "Bearer bad_token"})
        assert status_compat == 401
        print("  -> PASS: Both endpoints rejected invalid JWT with 401.")

        # -------------------------------------------------------------
        # CHECK 6: GET /users/me (User with NO Profile)
        # -------------------------------------------------------------
        print("\n[CHECK 6] Testing GET /users/me for fresh user (no profile yet)...")
        status, body = await asgi_request("GET", "/users/me", headers=auth_header)
        print(f"  GET /users/me -> Status: {status}, Profile data: {body}")
        assert status == 200
        assert body["id"] == temp_user_id
        assert body["height_cm"] is None
        assert body["weight_kg"] is None
        print("  -> PASS: GET /users/me handles absent profile cleanly.")

        # -------------------------------------------------------------
        # CHECK 7: Profile Creation via PUT /users/me
        # -------------------------------------------------------------
        print("\n[CHECK 7] Testing Profile Creation (PUT /users/me)...")
        init_profile = {
            "gender": "male",
            "height_cm": 180.0,
            "weight_kg": 75.0,
            "fitness_goal": "fat_loss",
            "activity_level": "moderate",
            "dietary_preference": "keto"
        }
        status, body = await asgi_request("PUT", "/users/me", headers=auth_header, body=init_profile)
        print(f"  PUT /users/me -> Status: {status}, Body: {body}")
        assert status == 200
        assert body["profile"]["height_cm"] == 180.0
        assert body["profile"]["fitness_goal"] == "fat_loss"

        # Verify in DB
        db.expire_all()
        created_p = db.query(Profile).filter(Profile.user_id == temp_user_id).first()
        assert created_p is not None, "Profile row missing in database!"
        assert created_p.height_cm == 180.0
        print("  -> PASS: Profile created successfully in database.")

        # -------------------------------------------------------------
        # CHECK 8: Profile Update via PUT /users/me & No Duplication
        # -------------------------------------------------------------
        print("\n[CHECK 8] Testing Profile Update & duplicate prevention (PUT /users/me)...")
        update_profile = {
            "weight_kg": 73.5,
            "fitness_goal": "hypertrophy"
        }
        status, body = await asgi_request("PUT", "/users/me", headers=auth_header, body=update_profile)
        print(f"  PUT /users/me (update) -> Status: {status}, Updated weight: {body['profile']['weight_kg']}")
        assert status == 200
        assert body["profile"]["weight_kg"] == 73.5
        assert body["profile"]["fitness_goal"] == "hypertrophy"

        # Check database profile count for this user
        count_for_user = db.query(Profile).filter(Profile.user_id == temp_user_id).count()
        print(f"  Profile count for user in DB: {count_for_user}")
        assert count_for_user == 1, f"Expected exactly 1 profile, found {count_for_user}!"
        print("  -> PASS: Existing profile updated in place. Zero duplicates.")

        # -------------------------------------------------------------
        # CHECK 9: Compatibility Aliases (/auth/me and /auth/profile)
        # -------------------------------------------------------------
        print("\n[CHECK 9] Testing Compatibility aliases (/auth/me and /auth/profile)...")
        status, body = await asgi_request("GET", "/auth/me", headers=auth_header)
        assert status == 200
        assert body["weight_kg"] == 73.5
        print(f"  GET /auth/me -> Status: {status}, weight: {body['weight_kg']}")

        status, body = await asgi_request("PUT", "/auth/profile", headers=auth_header, body={"weight_kg": 73.0})
        assert status == 200
        assert body["profile"]["weight_kg"] == 73.0
        print(f"  PUT /auth/profile -> Status: {status}, updated weight: {body['profile']['weight_kg']}")
        print("  -> PASS: Compatibility aliases function identically.")

        # -------------------------------------------------------------
        # CHECK 10: Existing Pre-migrated User (User ID 2) Retrieval
        # -------------------------------------------------------------
        print("\n[CHECK 10] Testing Existing Pre-migrated User (User ID 2)...")
        user2 = db.query(User).filter(User.id == 2).first()
        assert user2 is not None, "Original User 2 not found!"
        token2 = create_access_token(user2.id)
        status, body = await asgi_request("GET", "/users/me", headers={"Authorization": f"Bearer {token2}"})
        print(f"  GET /users/me (User 2) -> Status: {status}, height: {body['height_cm']}, goal: {body['fitness_goal']}")
        assert status == 200
        assert body["height_cm"] == 175.0
        assert body["fitness_goal"] == "muscle_gain"
        print("  -> PASS: Pre-migrated user profile retrieved accurately.")

        # -------------------------------------------------------------
        # CHECK 11: SQLAlchemy Models & Bidirectional Relationship
        # -------------------------------------------------------------
        print("\n[CHECK 11] Verifying SQLAlchemy model bidirectional relationships...")
        db.expire_all()
        u2 = db.query(User).filter(User.id == 2).first()
        p2 = db.query(Profile).filter(Profile.user_id == 2).first()

        # User -> Profile
        assert hasattr(u2, "profile"), "User has no 'profile' relationship!"
        assert u2.profile is not None, "u2.profile is None!"
        assert u2.profile.height_cm == 175.0

        # Profile -> User
        assert hasattr(p2, "user"), "Profile has no 'user' relationship!"
        assert p2.user is not None, "p2.user is None!"
        assert p2.user.id == 2
        assert p2.user.email == "anandkumarpv123@gmail.com"

        # Verify no direct profile properties on User model
        direct_props = [p for p in ['height_cm', 'weight_kg', 'fitness_goal'] if p in User.__dict__]
        print(f"  Direct profile properties remaining on User model: {direct_props}")
        assert len(direct_props) == 0, f"User model still has backward compatibility properties: {direct_props}"
        print("  -> PASS: Bidirectional relationships verified. Temporary properties removed.")

        # -------------------------------------------------------------
        # CHECK 12: PostgreSQL Database Integrity & Constraint Verification
        # -------------------------------------------------------------
        print("\n[CHECK 12] Verifying Live PostgreSQL schema & constraints...")
        load_conn = os.getenv("DATABASE_URL").replace("+psycopg", "")
        with psycopg.connect(load_conn) as conn:
            with conn.cursor() as cur:
                # 1. Foreign key constraint
                cur.execute("""
                    SELECT tc.constraint_name, rc.delete_rule 
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.referential_constraints rc ON tc.constraint_name = rc.constraint_name
                    WHERE tc.table_name = 'profiles' AND tc.constraint_type = 'FOREIGN KEY';
                """)
                fk = cur.fetchall()
                print(f"  FK constraint in DB: {fk}")
                assert len(fk) > 0 and fk[0][1] == "CASCADE", "Foreign key constraint invalid or missing!"

                # 2. Legacy columns in users
                cur.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name IN ('height_cm', 'weight_kg', 'fitness_goal');
                """)
                legacy_cols = [c[0] for c in cur.fetchall()]
                print(f"  Legacy columns in users table: {legacy_cols}")
                assert len(legacy_cols) == 3, "Legacy columns were dropped prematurely!"

                # 3. Duplicate profiles check across entire database
                cur.execute("""
                    SELECT user_id, COUNT(*) 
                    FROM profiles 
                    GROUP BY user_id 
                    HAVING COUNT(*) > 1;
                """)
                dups = cur.fetchall()
                print(f"  Duplicate profiles in database: {dups}")
                assert len(dups) == 0, f"Duplicate profiles found: {dups}"

        print("  -> PASS: Live PostgreSQL integrity, schema, and constraints verified.")

        # -------------------------------------------------------------
        # CLEANUP: Remove temporary test user
        # -------------------------------------------------------------
        print("\n[CLEANUP] Removing temporary test user...")
        if temp_user_id:
            del_user = db.query(User).filter(User.id == temp_user_id).first()
            if del_user:
                db.delete(del_user)
                db.commit()
            print(f"  -> Deleted test user ID {temp_user_id} and associated profile.")

        # Final count check
        final_users = db.query(User).count()
        final_profiles = db.query(Profile).count()
        print(f"  Final users count: {final_users}, Final profiles count: {final_profiles}")
        assert final_users == 2 and final_profiles == 2, f"Final count mismatch! users={final_users}, profiles={final_profiles}"

        print("\n" + "=" * 70)
        print("[ALL STEP 2D VERIFICATIONS PASSED WITH ZERO ERRORS]")
        print("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(run_step_2d_verification())
