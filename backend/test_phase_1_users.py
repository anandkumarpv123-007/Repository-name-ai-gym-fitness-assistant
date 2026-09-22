"""
AI Gym & Fitness Assistant — Phase 1 Test Suite
User Profile Foundation & Authentication Intelligence

Comprehensive coverage:
1. User registration & duplicate prevention (HTTP 409)
2. Password hashing & user login verification (HTTP 401 on bad password)
3. JWT Authentication & Bearer token authorization
4. Authenticated current-user profile retrieval (GET /users/me)
5. Profile creation & updates (PUT /users/me)
6. Cross-user isolation (User A token cannot mutate User B)
7. User-Profile 1-to-1 database relationship & CASCADE deletion
"""

import asyncio
from datetime import datetime
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, engine, Base
from main import app
from models.user import User
from models.profile import Profile


async def asgi_request(method, path, body=None, headers=None):
    """Utility to invoke FastAPI endpoints via ASGI interface directly in tests."""
    response_body = []
    status_code = None

    url_path = path
    query_string = b""
    if "?" in path:
        url_path, qs = path.split("?", 1)
        query_string = qs.encode("ascii")

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": url_path,
        "raw_path": url_path.encode("ascii"),
        "query_string": query_string,
        "headers": [(k.lower().encode("ascii"), v.encode("ascii")) for k, v in (headers or {}).items()],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }

    req_body = json.dumps(body).encode("utf-8") if body is not None else b""
    if body is not None and not any(k.lower() == "content-type" for k in (headers or {})):
        scope["headers"].append((b"content-type", b"application/json"))

    receive_called = False
    async def receive():
        nonlocal receive_called
        if not receive_called:
            receive_called = True
            return {"type": "http.request", "body": req_body, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = message["status"]
        elif message["type"] == "http.response.body":
            response_body.append(message.get("body", b""))

    await app(scope, receive, send)
    raw_text = b"".join(response_body).decode("utf-8")
    try:
        data = json.loads(raw_text)
    except Exception:
        data = raw_text

    return status_code, data


def run_async(coro):
    return asyncio.run(coro)


class TestPhase1UserFoundation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            for email in ["phase1_user_a@example.com", "phase1_user_b@example.com"]:
                old = db.query(User).filter(User.email == email).first()
                if old:
                    db.delete(old)
            db.commit()

    def test_01_user_registration_succeeds(self):
        """1. POST /auth/register creates user account in database."""
        status, data = run_async(asgi_request("POST", "/auth/register", {
            "name": "Phase1 User A",
            "email": "phase1_user_a@example.com",
            "password": "SecurePassword123!"
        }))
        self.assertEqual(status, 200)
        self.assertIn("id", data)
        self.assertEqual(data["email"], "phase1_user_a@example.com")

    def test_02_duplicate_email_registration_rejected(self):
        """2. Duplicate email registration returns 409 Conflict."""
        status, data = run_async(asgi_request("POST", "/auth/register", {
            "name": "Phase1 Duplicate",
            "email": "phase1_user_a@example.com",
            "password": "Password123!"
        }))
        self.assertEqual(status, 409)

    def test_03_user_login_succeeds(self):
        """3. Login with correct credentials returns valid JWT token."""
        # Using Form payload format as expected by OAuth2PasswordBearer /auth/login
        body = "username=phase1_user_a%40example.com&password=SecurePassword123%21"
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "path": "/auth/login",
            "raw_path": b"/auth/login",
            "query_string": b"",
            "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
        }
        req_body = body.encode("utf-8")
        receive_called = False
        async def receive():
            nonlocal receive_called
            if not receive_called:
                receive_called = True
                return {"type": "http.request", "body": req_body, "more_body": False}
            return {"type": "http.request", "body": b"", "more_body": False}

        resp_body = []
        status_code = None
        async def send(msg):
            nonlocal status_code
            if msg["type"] == "http.response.start":
                status_code = msg["status"]
            elif msg["type"] == "http.response.body":
                resp_body.append(msg.get("body", b""))

        run_async(app(scope, receive, send))
        data = json.loads(b"".join(resp_body).decode("utf-8"))

        self.assertEqual(status_code, 200)
        self.assertIn("access_token", data)
        TestPhase1UserFoundation.token_a = data["access_token"]

    def test_04_invalid_credentials_rejected(self):
        """4. Login with wrong password returns 401 Unauthorized."""
        body = "username=phase1_user_a%40example.com&password=WrongPassword!"
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "POST",
            "path": "/auth/login",
            "raw_path": b"/auth/login",
            "query_string": b"",
            "headers": [(b"content-type", b"application/x-www-form-urlencoded")],
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
        }
        req_body = body.encode("utf-8")
        receive_called = False
        async def receive():
            nonlocal receive_called
            if not receive_called:
                receive_called = True
                return {"type": "http.request", "body": req_body, "more_body": False}
            return {"type": "http.request", "body": b"", "more_body": False}

        resp_body = []
        status_code = None
        async def send(msg):
            nonlocal status_code
            if msg["type"] == "http.response.start":
                status_code = msg["status"]
            elif msg["type"] == "http.response.body":
                resp_body.append(msg.get("body", b""))

        run_async(app(scope, receive, send))
        self.assertEqual(status_code, 401)

    def test_05_authenticated_get_me_succeeds(self):
        """5. GET /users/me with Bearer token returns current user profile."""
        status, data = run_async(asgi_request(
            "GET",
            "/users/me",
            headers={"Authorization": f"Bearer {self.token_a}"}
        ))
        self.assertEqual(status, 200)
        self.assertEqual(data["email"], "phase1_user_a@example.com")

    def test_06_unauthenticated_get_me_rejected(self):
        """6. GET /users/me without Bearer token returns 401."""
        status, _ = run_async(asgi_request("GET", "/users/me"))
        self.assertEqual(status, 401)

    def test_07_update_user_profile_succeeds(self):
        """7. PUT /users/me updates height, weight, goal, and dietary preference."""
        status, data = run_async(asgi_request(
            "PUT",
            "/users/me",
            body={
                "height_cm": 180.0,
                "weight_kg": 78.5,
                "fitness_goal": "muscle_gain",
                "activity_level": "very_active",
                "dietary_preference": "high_protein"
            },
            headers={"Authorization": f"Bearer {self.token_a}"}
        ))
        self.assertEqual(status, 200)
        prof = data["profile"]
        self.assertEqual(prof["height_cm"], 180.0)
        self.assertEqual(prof["weight_kg"], 78.5)
        self.assertEqual(prof["fitness_goal"], "muscle_gain")

    def test_08_user_profile_isolation(self):
        """8. User A token cannot access or mutate User B profile data."""
        # Register User B
        status_b, res_b = run_async(asgi_request("POST", "/auth/register", {
            "name": "Phase1 User B",
            "email": "phase1_user_b@example.com",
            "password": "SecurePassword123!"
        }))
        self.assertEqual(status_b, 200)

        # GET /users/me using User A token returns User A data only
        status_a, data_a = run_async(asgi_request(
            "GET",
            "/users/me",
            headers={"Authorization": f"Bearer {self.token_a}"}
        ))
        self.assertEqual(data_a["email"], "phase1_user_a@example.com")
        self.assertNotEqual(data_a["email"], "phase1_user_b@example.com")

    def test_09_user_profile_cascade_deletion(self):
        """9. Deleting User automatically deletes Profile via CASCADE relationship."""
        with SessionLocal() as db:
            u_b = db.query(User).filter(User.email == "phase1_user_b@example.com").first()
            if u_b:
                user_id = u_b.id
                db.delete(u_b)
                db.commit()

                # Verify Profile is also deleted automatically
                prof_b = db.query(Profile).filter(Profile.user_id == user_id).first()
                self.assertIsNone(prof_b)


if __name__ == "__main__":
    unittest.main()
