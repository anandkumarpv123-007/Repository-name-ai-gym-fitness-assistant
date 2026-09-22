"""
AI Gym & Fitness Assistant — Phase 5 Test Suite
Virtual Gym Buddy & Conversational Fitness Intelligence

Comprehensive testing covering:
1. Authenticated chat request succeeds.
2. Unauthenticated request is rejected (401).
3. User isolation works (User A cannot view User B's history/context).
4. Profile context is correctly scoped.
5. Workout/performance context is correctly scoped.
6. Nutrition context is correctly scoped where available.
7. Missing user data (0 workouts, 0 nutrition logs) is handled safely.
8. Missing LLM API configuration is handled with deterministic fallback.
9. LLM/provider failure is handled with graceful fallback.
10. Malformed provider response is handled with graceful fallback.
11. Unsafe/medical-style requests receive safety boundary responses.
12. LLM/Fallback cannot fabricate unavailable user data.
13. Conversation persistence and history clearing work.
"""

import asyncio
from datetime import date, datetime
import json
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from auth.token import create_access_token
from database import SessionLocal
from main import app
from models.user import User
from models.profile import Profile
from models.workout_session import WorkoutSession
from models.exercise import Exercise
from models.workout_exercise import WorkoutExercise
from models.nutrition import NutritionTarget, NutritionLog
from models.buddy import BuddyMessage
from services.buddy_context_engine import BuddyContextEngine
from services.buddy_service import BuddyService


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


class TestPhase5VirtualGymBuddy(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with SessionLocal() as db:
            # Clean old test users if existing
            for email in ["userA_buddy@example.com", "userB_buddy@example.com"]:
                old_u = db.query(User).filter(User.email == email).first()
                if old_u:
                    db.delete(old_u)
            db.commit()

            # Seed Exercise
            squat = db.query(Exercise).filter(Exercise.name == "Squat").first()
            if not squat:
                squat = Exercise(name="Squat", category="Legs", description="Barbell squat")
                db.add(squat)
                db.commit()
                db.refresh(squat)
            cls.squat_id = squat.id

            # User A
            u_a = User(name="User A Buddy", email="userA_buddy@example.com", password_hash="pass_hash")
            db.add(u_a)
            db.commit()
            db.refresh(u_a)
            cls.user_a_id = u_a.id

            p_a = Profile(
                user_id=u_a.id,
                height_cm=175.0,
                weight_kg=75.0,
                fitness_goal="muscle_gain",
                activity_level="moderate",
                dietary_preference="high_protein",
                gender="male"
            )
            db.add(p_a)

            # User B
            u_b = User(name="User B Buddy", email="userB_buddy@example.com", password_hash="pass_hash")
            db.add(u_b)
            db.commit()
            db.refresh(u_b)
            cls.user_b_id = u_b.id

            p_b = Profile(
                user_id=u_b.id,
                height_cm=165.0,
                weight_kg=60.0,
                fitness_goal="weight_loss",
                activity_level="light",
                dietary_preference="vegetarian",
                gender="female"
            )
            db.add(p_b)
            db.commit()

            # Seed Workout Session for User A
            session_a = WorkoutSession(
                user_id=cls.user_a_id,
                started_at=datetime.utcnow(),
                ended_at=datetime.utcnow(),
                performance_score=85.0,
                notes="Great squat session"
            )
            db.add(session_a)
            db.commit()
            db.refresh(session_a)

            we_a = WorkoutExercise(
                workout_session_id=session_a.id,
                exercise_id=cls.squat_id,
                reps=10,
                sets=1,
            )
            db.add(we_a)

            # Seed Nutrition Log for User A
            log_a = NutritionLog(
                user_id=cls.user_a_id,
                log_date=date.today(),
                meal_type="lunch",
                food_name="Chicken Breast",
                quantity=200.0,
                unit="g",
                calories=330.0,
                protein=62.0,
                carbs=0.0,
                fat=7.2
            )
            db.add(log_a)
            db.commit()

        # Generate JWT tokens
        cls.token_a = create_access_token(cls.user_a_id)
        cls.token_b = create_access_token(cls.user_b_id)

    @classmethod
    def tearDownClass(cls):
        with SessionLocal() as db:
            for uid in [cls.user_a_id, cls.user_b_id]:
                u = db.get(User, uid)
                if u:
                    db.delete(u)
            db.commit()

    def test_01_authenticated_chat_succeeds(self):
        """1. Authenticated chat request succeeds with status 200."""
        status, data = run_async(asgi_request(
            "POST",
            "/buddy/chat",
            {"message": "How did I perform this week?"},
            {"Authorization": f"Bearer {self.token_a}"}
        ))
        self.assertEqual(status, 200)
        self.assertIn("message", data)
        self.assertIn("provider", data)
        self.assertIn("disclaimer", data)
        self.assertIn("context_summary", data)

    def test_02_unauthenticated_request_rejected(self):
        """2. Unauthenticated request is rejected with 401."""
        status_chat, _ = run_async(asgi_request("POST", "/buddy/chat", {"message": "Hello"}))
        self.assertEqual(status_chat, 401)

        status_hist, _ = run_async(asgi_request("GET", "/buddy/history"))
        self.assertEqual(status_hist, 401)

    def test_03_user_isolation(self):
        """3. User isolation works: User A cannot view User B's history/context."""
        # Send chat as User A
        run_async(asgi_request(
            "POST",
            "/buddy/chat",
            {"message": "User A secret message"},
            {"Authorization": f"Bearer {self.token_a}"}
        ))

        # Get history for User B
        status_b, data_b = run_async(asgi_request(
            "GET",
            "/buddy/history",
            headers={"Authorization": f"Bearer {self.token_b}"}
        ))
        self.assertEqual(status_b, 200)
        messages_b = data_b["messages"]
        for m in messages_b:
            self.assertNotIn("User A secret message", m["content"])

    def test_04_profile_context_scoped(self):
        """4. Profile context is correctly scoped to current authenticated user."""
        with SessionLocal() as db:
            ctx_a = BuddyContextEngine.gather_user_context(db, self.user_a_id)
            ctx_b = BuddyContextEngine.gather_user_context(db, self.user_b_id)

        self.assertEqual(ctx_a["profile"]["fitness_goal"], "muscle_gain")
        self.assertEqual(ctx_b["profile"]["fitness_goal"], "weight_loss")

    def test_05_workout_performance_context_scoped(self):
        """5. Workout/performance context is correctly scoped."""
        with SessionLocal() as db:
            ctx_a = BuddyContextEngine.gather_user_context(db, self.user_a_id)
            ctx_b = BuddyContextEngine.gather_user_context(db, self.user_b_id)

        self.assertEqual(ctx_a["workout_performance"]["total_workouts"], 1)
        self.assertEqual(ctx_b["workout_performance"]["total_workouts"], 0)

    def test_06_nutrition_context_scoped(self):
        """6. Nutrition context is correctly scoped where available."""
        with SessionLocal() as db:
            ctx_a = BuddyContextEngine.gather_user_context(db, self.user_a_id)
            ctx_b = BuddyContextEngine.gather_user_context(db, self.user_b_id)

        self.assertGreater(ctx_a["nutrition"]["consumed_calories_today"], 0)
        self.assertEqual(ctx_b["nutrition"]["consumed_calories_today"], 0.0)

    def test_07_missing_user_data_handled_safely(self):
        """7. Missing user data (0 workouts, 0 nutrition logs) is handled safely."""
        status, data = run_async(asgi_request(
            "POST",
            "/buddy/chat",
            {"message": "How was my weekly performance?"},
            {"Authorization": f"Bearer {self.token_b}"}
        ))
        self.assertEqual(status, 200)
        msg = data["message"]
        self.assertIn("haven't logged any completed workout sessions yet", msg)

    def test_08_missing_llm_api_key_handled(self):
        """8. Missing LLM API configuration falls back cleanly to deterministic engine."""
        with patch.dict(os.environ, {}, clear=True):
            status, data = run_async(asgi_request(
                "POST",
                "/buddy/chat",
                {"message": "Give me some motivation for today's workout."},
                {"Authorization": f"Bearer {self.token_a}"}
            ))
            self.assertEqual(status, 200)
            self.assertEqual(data["provider"], "deterministic_buddy_fallback")
            self.assertIn("Consistency beats intensity", data["message"])

    def test_09_llm_provider_failure_handled(self):
        """9. LLM/provider error handles gracefully with deterministic fallback."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_123"}):
            with patch("urllib.request.urlopen", side_effect=Exception("Connection timed out")):
                status, data = run_async(asgi_request(
                    "POST",
                    "/buddy/chat",
                    {"message": "What should I focus on next?"},
                    {"Authorization": f"Bearer {self.token_a}"}
                ))
                self.assertEqual(status, 200)
                self.assertEqual(data["provider"], "deterministic_buddy_fallback")
                self.assertIn("Next Workout Action Plan", data["message"])

    def test_10_malformed_provider_response_handled(self):
        """10. Malformed provider response is handled cleanly with fallback."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake_key_123"}):
            mock_resp = unittest.mock.MagicMock()
            mock_resp.read.return_value = b'{"candidates": []}'
            mock_resp.__enter__.return_value = mock_resp
            with patch("urllib.request.urlopen", return_value=mock_resp):
                status, data = run_async(asgi_request(
                    "POST",
                    "/buddy/chat",
                    {"message": "How is my nutrition status?"},
                    {"Authorization": f"Bearer {self.token_a}"}
                ))
                self.assertEqual(status, 200)
                self.assertEqual(data["provider"], "deterministic_buddy_fallback")
                self.assertIn("Nutrition Status", data["message"])

    def test_11_unsafe_medical_requests_safety(self):
        """11. Unsafe/medical-style requests receive appropriate safety boundary."""
        status, data = run_async(asgi_request(
            "POST",
            "/buddy/chat",
            {"message": "I am having severe chest pain while squatting, please diagnose me."},
            {"Authorization": f"Bearer {self.token_a}"}
        ))
        self.assertEqual(status, 200)
        self.assertEqual(data["provider"], "system_safety")
        self.assertIn("NOT a medical doctor", data["message"])
        self.assertIn("consult a qualified medical professional", data["message"])

    def test_12_cannot_fabricate_data(self):
        """12. LLM/Fallback engine cannot fabricate unavailable user data."""
        # Query User B who has 0 workouts logged
        status, data = run_async(asgi_request(
            "POST",
            "/buddy/chat",
            {"message": "What was my squat form score yesterday?"},
            {"Authorization": f"Bearer {self.token_b}"}
        ))
        self.assertEqual(status, 200)
        msg = data["message"]
        # Must acknowledge missing sessions rather than claiming a fake score
        self.assertIn("haven't logged", msg)

    def test_13_chat_persistence_and_deletion(self):
        """13. Chat history persistence and deletion endpoints work as expected."""
        # Send message
        run_async(asgi_request(
            "POST",
            "/buddy/chat",
            {"message": "Persistent test question"},
            {"Authorization": f"Bearer {self.token_a}"}
        ))

        # Get history
        status_hist, data_hist = run_async(asgi_request(
            "GET",
            "/buddy/history",
            headers={"Authorization": f"Bearer {self.token_a}"}
        ))
        self.assertEqual(status_hist, 200)
        messages = data_hist["messages"]
        self.assertGreater(len(messages), 0)

        # Clear history
        status_del, data_del = run_async(asgi_request(
            "DELETE",
            "/buddy/history",
            headers={"Authorization": f"Bearer {self.token_a}"}
        ))
        self.assertEqual(status_del, 200)

        # Re-verify history is empty
        _, data_after = run_async(asgi_request(
            "GET",
            "/buddy/history",
            headers={"Authorization": f"Bearer {self.token_a}"}
        ))
        self.assertEqual(len(data_after["messages"]), 0)


if __name__ == "__main__":
    unittest.main()
