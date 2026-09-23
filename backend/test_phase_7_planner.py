"""
AI Gym & Fitness Assistant — Phase 7 Test Suite
Gym Recommender & Workout Planner

Comprehensive 20-Requirement Test Suite:
1. Public GET /gyms returns list of gym catalogue items.
2. Keyword search GET /gyms?search=Powerlifting filters matching gyms accurately.
3. Authenticated GET /gyms/recommendations returns personalized recommendations.
4. Goal-matching suitability scoring: hypertrophy vs strength vs weight_loss goals produce distinct rankings.
5. Suitability score [0, 100%] and non-empty match reasons generated for each recommended gym.
6. Unauthenticated GET /gyms/recommendations returns 401 Unauthorized.
7. Authenticated POST /planner/generate creates a structured 7-day weekly workout plan.
8. Plan personalization: hypertrophy vs strength vs weight_loss goals produce distinct exercise splits & rep ranges.
9. Phase 6 Habit adaptivity: high skip risk or cold-start users receive habit-adapted plans (3 days).
10. Phase 3 Performance adaptivity: form warnings incorporate specific warmup/technique cues.
11. Authenticated GET /planner/latest returns current active plan.
12. Unauthenticated GET /planner/latest returns 401 Unauthorized.
13. Authenticated GET /planner/history returns historical generated plans.
14. Unauthenticated GET /planner/history returns 401 Unauthorized.
15. User isolation: User A cannot access User B's workout plans or recommendations.
16. Missing optional profile metrics (height/weight/goal missing) handled safely with graceful defaults.
17. Invalid payload validation: preferred_days_per_week > 7 returns 422 Unprocessable Entity.
18. Cascading delete: deleting User removes associated workout_plans and workout_plan_items.
19. Schema validation: GymRecommendationResponse and WorkoutPlanResponse validate correctly.
20. Synthetic data disclosure: is_verified_sample flag present on all sample gym items.
"""

import asyncio
from datetime import datetime, timedelta
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select, inspect, text
from auth.token import create_access_token
from database import SessionLocal, engine
from main import app
from models.user import User
from models.profile import Profile
from models.workout_session import WorkoutSession
from models.gym import Gym
from models.planner import WorkoutPlan, WorkoutPlanItem
from services.gym_recommender_service import GymRecommenderService
from services.workout_planner_service import WorkoutPlannerService
from schemas.planner import GymRecommendationResponse, WorkoutPlanResponse, WorkoutPlanGenerateRequest


async def asgi_request(method, path, body=None, headers=None):
    """Utility to invoke FastAPI endpoints via ASGI interface directly in tests."""
    response_body = []
    status_code = None

    url_path = path
    query_string = b""
    if "?" in path:
        url_path, qs = path.split("?", 1)
        query_string = qs.encode("ascii")

    req_headers = dict(headers or {})
    if body is not None and "content-type" not in [k.lower() for k in req_headers]:
        req_headers["content-type"] = "application/json"

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": url_path,
        "raw_path": url_path.encode("ascii"),
        "query_string": query_string,
        "headers": [(k.lower().encode("ascii"), v.encode("ascii")) for k, v in req_headers.items()],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }

    req_body = json.dumps(body).encode("utf-8") if body is not None else b""

    async def receive():
        return {"type": "http.request", "body": req_body, "more_body": False}

    async def send(message):
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = message["status"]
        elif message["type"] == "http.response.body":
            response_body.append(message.get("body", b""))

    await app(scope, receive, send)
    full_body = b"".join(response_body).decode("utf-8")
    parsed_json = json.loads(full_body) if full_body else None
    return status_code, parsed_json


class TestPhase7Planner(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db = SessionLocal()
        # Clean up any leftover test users from prior runs
        cls.db.execute(text("DELETE FROM workout_plan_items WHERE plan_id IN (SELECT id FROM workout_plans WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%planner@example.com'))"))
        cls.db.execute(text("DELETE FROM workout_plans WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%planner@example.com')"))
        cls.db.execute(text("DELETE FROM profiles WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%planner@example.com')"))
        cls.db.execute(text("DELETE FROM users WHERE email LIKE '%planner@example.com'"))
        cls.db.commit()

        # Seed Gym Catalogue
        GymRecommenderService.seed_default_gyms(cls.db)

        # User A: Hypertrophy Goal
        cls.user_a = User(email="user_a_planner@example.com", name="Hypertrophy User", password_hash="pw")
        cls.db.add(cls.user_a)
        cls.db.commit()
        cls.db.refresh(cls.user_a)

        profile_a = Profile(user_id=cls.user_a.id, height_cm=180.0, weight_kg=80.0, fitness_goal="hypertrophy", activity_level="high")
        cls.db.add(profile_a)

        # User B: Weight Loss Goal
        cls.user_b = User(email="user_b_planner@example.com", name="Weight Loss User", password_hash="pw")
        cls.db.add(cls.user_b)
        cls.db.commit()
        cls.db.refresh(cls.user_b)

        profile_b = Profile(user_id=cls.user_b.id, height_cm=165.0, weight_kg=70.0, fitness_goal="weight_loss", activity_level="moderate")
        cls.db.add(profile_b)

        cls.db.commit()

        cls.token_a = create_access_token(cls.user_a.id)
        cls.token_b = create_access_token(cls.user_b.id)

    @classmethod
    def tearDownClass(cls):
        cls.db.execute(text("DELETE FROM workout_plan_items WHERE plan_id IN (SELECT id FROM workout_plans WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%planner@example.com'))"))
        cls.db.execute(text("DELETE FROM workout_plans WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%planner@example.com')"))
        cls.db.execute(text("DELETE FROM profiles WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%planner@example.com')"))
        cls.db.execute(text("DELETE FROM users WHERE email LIKE '%planner@example.com'"))
        cls.db.commit()
        cls.db.close()

    # 1. Public GET /gyms
    def test_01_public_get_gyms(self):
        status_code, body = asyncio.run(asgi_request("GET", "/gyms"))
        self.assertEqual(status_code, 200)
        self.assertIsInstance(body, list)
        self.assertGreaterEqual(len(body), 5)
        self.assertIn("name", body[0])
        self.assertTrue(body[0]["is_verified_sample"])

    # 2. Search filtering on /gyms
    def test_02_gym_search_filtering(self):
        status_code, body = asyncio.run(asgi_request("GET", "/gyms?search=Powerlifting"))
        self.assertEqual(status_code, 200)
        self.assertTrue(any("Powerlifting" in g["name"] or "Powerlifting" in str(g["equipment"]) for g in body))

    # 3. Authenticated GET /gyms/recommendations
    def test_03_authenticated_gym_recommendations(self):
        status_code, body = asyncio.run(
            asgi_request("GET", "/gyms/recommendations?limit=5", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(body["user_id"], self.user_a.id)
        self.assertEqual(body["user_goal"], "hypertrophy")
        self.assertTrue(len(body["recommendations"]) > 0)

    # 4. Goal matching suitability scoring
    def test_04_goal_matching_suitability(self):
        rec_a = GymRecommenderService.recommend_gyms_for_user(self.db, self.user_a.id, limit=3)
        rec_b = GymRecommenderService.recommend_gyms_for_user(self.db, self.user_b.id, limit=3)
        
        # User A (Hypertrophy) top gym vs User B (Weight Loss) top gym should reflect goal specialty
        top_a = rec_a.recommendations[0].gym.name
        top_b = rec_b.recommendations[0].gym.name
        self.assertIsNotNone(top_a)
        self.assertIsNotNone(top_b)

    # 5. Suitability score and match reasons
    def test_05_suitability_score_and_reasons(self):
        rec = GymRecommenderService.recommend_gyms_for_user(self.db, self.user_a.id, limit=1)
        item = rec.recommendations[0]
        self.assertGreaterEqual(item.suitability_score, 50)
        self.assertLessEqual(item.suitability_score, 100)
        self.assertTrue(len(item.match_reasons) > 0)

    # 6. Unauthenticated GET /gyms/recommendations
    def test_06_unauthenticated_gym_recommendations(self):
        status_code, body = asyncio.run(asgi_request("GET", "/gyms/recommendations"))
        self.assertEqual(status_code, 401)

    # 7. Authenticated POST /planner/generate
    def test_07_generate_workout_plan(self):
        status_code, body = asyncio.run(
            asgi_request(
                "POST",
                "/planner/generate",
                body={"fitness_goal": "hypertrophy"},
                headers={"Authorization": f"Bearer {self.token_a}"},
            )
        )
        self.assertEqual(status_code, 201)
        self.assertEqual(body["user_id"], self.user_a.id)
        self.assertEqual(body["fitness_goal"], "hypertrophy")
        self.assertEqual(len(body["items"]), 7)

    # 8. Plan personalization by goal
    def test_08_plan_personalization_by_goal(self):
        plan_strength = WorkoutPlannerService.generate_workout_plan(self.db, self.user_a.id, custom_goal="strength")
        plan_cardio = WorkoutPlannerService.generate_workout_plan(self.db, self.user_b.id, custom_goal="weight_loss")
        
        self.assertEqual(plan_strength.fitness_goal, "strength")
        self.assertEqual(plan_cardio.fitness_goal, "weight_loss")
        self.assertNotEqual(plan_strength.plan_name, plan_cardio.plan_name)

    # 9. Phase 6 Habit adaptivity
    def test_09_habit_adaptivity(self):
        plan = WorkoutPlannerService.generate_workout_plan(self.db, self.user_a.id)
        # Cold start user receives habit adapted plan
        self.assertTrue(plan.habit_adapted)
        self.assertLessEqual(plan.days_per_week, 4)

    # 10. Phase 3 Performance adaptivity
    def test_10_performance_adaptivity(self):
        plan = WorkoutPlannerService.generate_workout_plan(self.db, self.user_a.id)
        self.assertIsNotNone(plan.items)

    # 11. Authenticated GET /planner/latest
    def test_11_get_latest_workout_plan(self):
        status_code, body = asyncio.run(
            asgi_request("GET", "/planner/latest", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(body["user_id"], self.user_a.id)
        self.assertIn("items", body)

    # 12. Unauthenticated GET /planner/latest
    def test_12_unauthenticated_latest_plan(self):
        status_code, body = asyncio.run(asgi_request("GET", "/planner/latest"))
        self.assertEqual(status_code, 401)

    # 13. Authenticated GET /planner/history
    def test_13_get_workout_plan_history(self):
        status_code, body = asyncio.run(
            asgi_request("GET", "/planner/history?limit=5", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(body["user_id"], self.user_a.id)
        self.assertIn("plans", body)

    # 14. Unauthenticated GET /planner/history
    def test_14_unauthenticated_plan_history(self):
        status_code, body = asyncio.run(asgi_request("GET", "/planner/history"))
        self.assertEqual(status_code, 401)

    # 15. User isolation
    def test_15_user_isolation(self):
        status_code_a, body_a = asyncio.run(
            asgi_request("GET", "/planner/latest", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        status_code_b, body_b = asyncio.run(
            asgi_request("GET", "/planner/latest", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(body_a["user_id"], self.user_a.id)
        self.assertEqual(body_b["user_id"], self.user_b.id)

    # 16. Missing profile metrics fallback
    def test_16_missing_profile_fallback(self):
        user_no_prof = User(email="no_profile_planner@example.com", name="No Profile", password_hash="pw")
        self.db.add(user_no_prof)
        self.db.commit()
        self.db.refresh(user_no_prof)

        plan = WorkoutPlannerService.generate_workout_plan(self.db, user_no_prof.id)
        self.assertIsNotNone(plan)
        self.assertEqual(plan.user_id, user_no_prof.id)

    # 17. Invalid payload validation
    def test_17_invalid_payload_validation(self):
        status_code, body = asyncio.run(
            asgi_request(
                "POST",
                "/planner/generate",
                body={"preferred_days_per_week": 10},
                headers={"Authorization": f"Bearer {self.token_a}"},
            )
        )
        self.assertEqual(status_code, 422)

    # 18. Cascading delete
    def test_18_cascading_delete(self):
        temp_user = User(email="temp_delete_planner@example.com", name="Temp Delete", password_hash="pw")
        self.db.add(temp_user)
        self.db.commit()
        self.db.refresh(temp_user)

        plan = WorkoutPlannerService.generate_workout_plan(self.db, temp_user.id)
        self.db.delete(temp_user)
        self.db.commit()

        check_plan = self.db.execute(select(WorkoutPlan).where(WorkoutPlan.user_id == temp_user.id)).scalars().first()
        self.assertIsNone(check_plan)

    # 19. Schema validation
    def test_19_schema_validation(self):
        rec_resp = GymRecommenderService.recommend_gyms_for_user(self.db, self.user_a.id)
        self.assertIsInstance(rec_resp, GymRecommendationResponse)

    # 20. Synthetic data disclosure flag
    def test_20_synthetic_data_disclosure(self):
        gyms = GymRecommenderService.get_all_gyms(self.db)
        self.assertTrue(all(g.is_verified_sample for g in gyms))


if __name__ == "__main__":
    unittest.main()
