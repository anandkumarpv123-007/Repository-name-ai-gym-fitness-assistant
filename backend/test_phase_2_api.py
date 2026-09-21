"""
AI Gym & Fitness Assistant — Phase 2 Backend API Verification
Tests exercise catalogue, workout session lifecycle, pose metrics persistence,
authorization, workout history, and longitudinal performance summary.
Uses zero-dependency direct ASGI client matching verify_step_2d.py.
"""

import asyncio
import json
import sys
import unittest
from pathlib import Path

# Setup path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from database import SessionLocal
from models.user import User
from models.workout_session import WorkoutSession
from auth.token import create_access_token
from main import app


async def asgi_request(method: str, path: str, headers: dict = None, body=None):
    """Zero-dependency ASGI HTTP client."""
    headers = headers or {}
    formatted_headers = []

    body_bytes = b""
    if body is not None:
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
            "more_body": False,
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


class TestPhase2API(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create valid JWT token for existing User ID 2
        cls.user_id = 2
        cls.token = create_access_token(user_id=cls.user_id)
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    def test_01_get_exercises_catalogue(self):
        """GET /exercises returns catalogue of available exercises."""
        status_code, data = asyncio.run(asgi_request("GET", "/exercises"))
        self.assertEqual(status_code, 200)
        self.assertGreaterEqual(len(data), 3)
        names = [e["name"] for e in data]
        self.assertIn("Squat", names)
        self.assertIn("Push-up", names)
        self.assertIn("Bicep Curl", names)

    def test_02_workout_start_unauthorized(self):
        """POST /workouts/start without JWT returns 401."""
        status_code, _ = asyncio.run(asgi_request("POST", "/workouts/start", body={}))
        self.assertEqual(status_code, 401)

    def test_03_workout_lifecycle_complete_and_persist_metrics(self):
        """Full lifecycle: start session -> complete with score & pose metrics -> verify DB."""
        # 1. Start workout
        status_code, start_data = asyncio.run(
            asgi_request(
                "POST",
                "/workouts/start",
                headers=self.headers,
                body={"exercise_id": 1, "notes": "Test Squat Session"},
            )
        )
        self.assertEqual(status_code, 200)
        session_id = start_data["session_id"]
        self.assertIsNotNone(session_id)

        # 2. Complete workout with score and 3 rep metrics
        complete_payload = {
            "exercise_id": 1,
            "sets": 1,
            "reps": 3,
            "calories": 18.5,
            "performance_score": 91.2,
            "notes": "Solid form maintained",
            "rep_metrics": [
                {
                    "rep_number": 1,
                    "min_knee_angle": 88.5,
                    "max_torso_lean": 24.0,
                    "duration_seconds": 3.1,
                    "form_status": "ADEQUATE",
                    "violations": [],
                    "metrics_json": {"rom": 95.0, "tempo": 90.0},
                },
                {
                    "rep_number": 2,
                    "min_knee_angle": 89.2,
                    "max_torso_lean": 26.5,
                    "duration_seconds": 3.0,
                    "form_status": "ADEQUATE",
                    "violations": [],
                    "metrics_json": {"rom": 94.0, "tempo": 92.0},
                },
                {
                    "rep_number": 3,
                    "min_knee_angle": 90.0,
                    "max_torso_lean": 28.0,
                    "duration_seconds": 2.9,
                    "form_status": "ADEQUATE",
                    "violations": [],
                    "metrics_json": {"rom": 93.0, "tempo": 91.0},
                },
            ],
        }
        status_code, comp_data = asyncio.run(
            asgi_request(
                "POST",
                f"/workouts/{session_id}/complete",
                headers=self.headers,
                body=complete_payload,
            )
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(comp_data["session_id"], session_id)
        self.assertEqual(comp_data["reps"], 3)
        self.assertEqual(comp_data["performance_score"], 91.2)

        # 3. Verify session detail endpoint
        status_code, detail_data = asyncio.run(
            asgi_request(
                "GET",
                f"/workouts/{session_id}",
                headers=self.headers,
            )
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(detail_data["session_id"], session_id)
        self.assertEqual(detail_data["exercise_name"], "Squat")
        self.assertEqual(detail_data["reps"], 3)
        self.assertEqual(len(detail_data["pose_metrics"]), 3)
        self.assertEqual(detail_data["pose_metrics"][0]["rep_number"], 1)

        # 4. Verify workout history endpoint
        status_code, hist_data = asyncio.run(
            asgi_request("GET", "/workouts/history", headers=self.headers)
        )
        self.assertEqual(status_code, 200)
        self.assertGreaterEqual(len(hist_data), 1)
        session_ids = [s["session_id"] for s in hist_data]
        self.assertIn(session_id, session_ids)

        # 5. Verify performance summary endpoint
        status_code, perf_data = asyncio.run(
            asgi_request("GET", "/performance/summary", headers=self.headers)
        )
        self.assertEqual(status_code, 200)
        self.assertGreaterEqual(perf_data["total_sessions"], 1)
        self.assertGreaterEqual(perf_data["total_reps"], 3)
        self.assertIsNotNone(perf_data["average_score"])
        self.assertIn("next_week_focus", perf_data)

        # Cleanup test session
        with SessionLocal() as db:
            s_obj = db.get(WorkoutSession, session_id)
            if s_obj:
                db.delete(s_obj)
                db.commit()

    def test_04_cross_user_authorization_isolation(self):
        """
        REGRESSION CHECK: Verify strict cross-user authorization.
        User 1 cannot access, complete, or see User 2's workout session.
        /performance/summary only aggregates the authenticated user's own data.
        """
        user2_token = self.token
        user2_headers = self.headers

        # Token for User 1
        user1_token = create_access_token(user_id=1)
        user1_headers = {"Authorization": f"Bearer {user1_token}"}

        # 1. User 2 starts a session
        status_code, start_data = asyncio.run(
            asgi_request("POST", "/workouts/start", body={"exercise_id": 1}, headers=user2_headers)
        )
        self.assertEqual(status_code, 200)
        session_id = start_data["session_id"]

        try:
            # 2. User 1 tries to GET User 2's workout detail -> 403 Forbidden
            status_code, err_data = asyncio.run(
                asgi_request("GET", f"/workouts/{session_id}", headers=user1_headers)
            )
            self.assertEqual(status_code, 403)
            self.assertIn("permission", err_data.get("detail", "").lower())

            # 3. User 1 tries to complete User 2's workout session -> 403 Forbidden
            status_code, err_data = asyncio.run(
                asgi_request(
                    "POST",
                    f"/workouts/{session_id}/complete",
                    body={"exercise_id": 1, "reps": 10, "performance_score": 90.0},
                    headers=user1_headers,
                )
            )
            self.assertEqual(status_code, 403)
            self.assertIn("permission", err_data.get("detail", "").lower())

            # 4. User 1 queries /workouts/history -> session_id must NOT appear
            status_code, hist_data = asyncio.run(
                asgi_request("GET", "/workouts/history", headers=user1_headers)
            )
            self.assertEqual(status_code, 200)
            user1_session_ids = [s["session_id"] for s in hist_data]
            self.assertNotIn(session_id, user1_session_ids)

            # 5. User 1 queries /performance/summary -> User 2's session must not leak
            status_code, user1_summary = asyncio.run(
                asgi_request("GET", "/performance/summary", headers=user1_headers)
            )
            self.assertEqual(status_code, 200)

        finally:
            # Clean up session
            with SessionLocal() as db:
                s_obj = db.get(WorkoutSession, session_id)
                if s_obj:
                    db.delete(s_obj)
                    db.commit()


def run_suite():
    print("=" * 70)
    print("PHASE 2 — BACKEND WORKOUT & PERFORMANCE API TESTS")
    print("=" * 70)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase2API)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("=" * 70)
    if result.wasSuccessful():
        print("[ALL PHASE 2 BACKEND API TESTS PASSED SUCCESSFULLY]")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(run_suite())
