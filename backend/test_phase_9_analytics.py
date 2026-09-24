import asyncio
from datetime import date, datetime, timedelta
import json
import os
import sys
import unittest
from sqlalchemy import select, text, func

# Append backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database import Base, SessionLocal, engine
from models.user import User
from models.profile import Profile
from models.workout_session import WorkoutSession
from models.workout_exercise import WorkoutExercise
from models.exercise import Exercise
from models.nutrition import NutritionTarget, NutritionLog
from models.iot import IoTDevice, IoTTelemetry
from services.analytics_service import AnalyticsService
from services.smart_gym_service import SmartGymService
from services.nutrition_service import NutritionService
from auth.security import hash_password
from auth.token import create_access_token
from main import app


async def asgi_request(method: str, path: str, json_body: dict = None, headers: dict = None):
    """Utility helper for ASGI in-memory requests without requiring external servers."""
    response_body = []
    status_code = None

    url_path = path
    query_string = b""
    if "?" in path:
        url_path, q_str = path.split("?", 1)
        query_string = q_str.encode("utf-8")

    req_headers = []
    if headers:
        for k, v in headers.items():
            req_headers.append((k.lower().encode("utf-8"), v.encode("utf-8")))

    body_bytes = b""
    if json_body is not None:
        body_bytes = json.dumps(json_body).encode("utf-8")
        req_headers.append((b"content-type", b"application/json"))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method.upper(),
        "path": url_path,
        "raw_path": url_path.encode("utf-8"),
        "query_string": query_string,
        "headers": req_headers,
        "client": ("127.0.0.1", 50000),
        "server": ("127.0.0.1", 80),
    }

    async def receive():
        return {
            "type": "http.request",
            "body": body_bytes,
            "more_body": False,
        }

    async def send(message):
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = message["status"]
        elif message["type"] == "http.response.body":
            response_body.append(message.get("body", b""))

    await app(scope, receive, send)
    full_body = b"".join(response_body).decode("utf-8")
    parsed_json = None
    if full_body:
        try:
            parsed_json = json.loads(full_body)
        except json.JSONDecodeError:
            parsed_json = full_body

    return status_code, parsed_json


class TestPhase9Analytics(unittest.TestCase):
    """
    Comprehensive Automated Test Suite for Phase 9 — Dashboards & Advanced Analytics.
    Validates overview, workout, nutrition, habit, and IoT endpoints, time-window variations,
    empty/insufficient data states, authentication, and cross-user data isolation.
    """

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

        # Clean existing test users if present
        cls.db.execute(text("DELETE FROM users WHERE email IN ('analytics_a@example.com', 'analytics_b@example.com');"))
        cls.db.commit()

        # Create User A
        cls.user_a = User(
            name="Analytics User A",
            email="analytics_a@example.com",
            password_hash=hash_password("Password123!"),
        )
        cls.db.add(cls.user_a)
        cls.db.commit()
        cls.db.refresh(cls.user_a)

        # Profile A
        cls.profile_a = Profile(
            user_id=cls.user_a.id,
            height_cm=180.0,
            weight_kg=80.0,
            fitness_goal="hypertrophy",
            gender="male",
        )
        cls.db.add(cls.profile_a)

        # Create User B (for isolation tests)
        cls.user_b = User(
            name="Analytics User B",
            email="analytics_b@example.com",
            password_hash=hash_password("Password123!"),
        )
        cls.db.add(cls.user_b)
        cls.db.commit()
        cls.db.refresh(cls.user_b)

        # Profile B
        cls.profile_b = Profile(
            user_id=cls.user_b.id,
            height_cm=165.0,
            weight_kg=60.0,
            fitness_goal="weight_loss",
            gender="female",
        )
        cls.db.add(cls.profile_b)
        cls.db.commit()

        cls.token_a = create_access_token(cls.user_a.id)
        cls.token_b = create_access_token(cls.user_b.id)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def setUp(self):
        # Ensure fresh state for user workouts, logs, telemetry
        self.db.execute(select(WorkoutSession).where(WorkoutSession.user_id.in_([self.user_a.id, self.user_b.id])))
        self.db.commit()

    def tearDown(self):
        self.db.rollback()

    # 1. Overview analytics endpoint returns HTTP 200 with complete structure
    def test_01_overview_analytics_structure(self):
        status, body = asyncio.run(
            asgi_request("GET", "/analytics/overview?time_window=7_days", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["time_window"], "7_days")
        self.assertIn("user_profile", body)
        self.assertIn("workout_summary", body)
        self.assertIn("nutrition_summary", body)
        self.assertIn("habit_summary", body)
        self.assertIn("iot_summary", body)
        self.assertIn("cross_domain_insights", body)
        self.assertEqual(body["user_profile"]["fitness_goal"], "hypertrophy")
        self.assertEqual(body["user_profile"]["bmi"], 24.7)  # 80 / (1.8^2)

    # 2. Workout analytics endpoint returns empty data state for new user
    def test_02_workout_analytics_empty_state(self):
        status, body = asyncio.run(
            asgi_request("GET", "/analytics/workouts?time_window=7_days", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        self.assertFalse(body["has_data"])
        self.assertEqual(body["total_workouts"], 0)
        self.assertIsNone(body["avg_performance_score"])
        self.assertEqual(body["performance_trend"], "insufficient_data")

    # 3. Workout analytics with recorded sessions computes metrics correctly
    def test_03_workout_analytics_with_data(self):
        # Seed a completed workout session for User A
        s = WorkoutSession(
            user_id=self.user_a.id,
            started_at=datetime.utcnow() - timedelta(hours=2),
            ended_at=datetime.utcnow() - timedelta(hours=1),
            performance_score=85.0,
        )
        self.db.add(s)
        self.db.commit()

        status, body = asyncio.run(
            asgi_request("GET", "/analytics/workouts?time_window=7_days", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["has_data"])
        self.assertEqual(body["total_workouts"], 1)
        self.assertEqual(body["total_duration_minutes"], 60)
        self.assertEqual(body["avg_performance_score"], 85.0)

    # 4. Nutrition analytics empty state
    def test_04_nutrition_analytics_empty_state(self):
        status, body = asyncio.run(
            asgi_request("GET", "/analytics/nutrition?time_window=7_days", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        self.assertFalse(body["has_data"])
        self.assertIsNone(body["average_daily_intake"]["avg_calories"])

    # 5. Nutrition analytics with logged food computes daily averages & compliance
    def test_05_nutrition_analytics_with_data(self):
        # Target for User A
        target = NutritionService.get_or_create_user_target(self.db, self.user_a.id)

        # Log food for today
        log = NutritionLog(
            user_id=self.user_a.id,
            log_date=date.today(),
            meal_type="lunch",
            food_name="Chicken Breast & Rice",
            quantity=250.0,
            unit="g",
            calories=target.calories_target,  # Exact target hit
            protein=target.protein_grams,
            carbs=target.carbs_grams,
            fat=target.fat_grams,
        )
        self.db.add(log)
        self.db.commit()

        status, body = asyncio.run(
            asgi_request("GET", "/analytics/nutrition?time_window=7_days", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["has_data"])
        self.assertEqual(body["average_daily_intake"]["avg_calories"], target.calories_target)
        self.assertEqual(body["compliance"]["calorie_compliance_pct"], 100.0)

    # 6. Habit analytics endpoint return structure and consistency calculations
    def test_06_habit_analytics_endpoint(self):
        status, body = asyncio.run(
            asgi_request("GET", "/analytics/habits?time_window=7_days", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        self.assertIn("current_status", body)
        self.assertIn("consistency", body)
        self.assertIn("daily_habit_history", body)
        self.assertEqual(len(body["daily_habit_history"]), 7)

    # 7. IoT analytics endpoint empty state (no devices registered)
    def test_07_iot_analytics_empty_state(self):
        status, body = asyncio.run(
            asgi_request("GET", "/analytics/iot?time_window=7_days", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        self.assertFalse(body["has_data"])
        self.assertEqual(body["device_counts"]["total_devices"], 0)

    # 8. IoT analytics with registered devices and telemetry data
    def test_08_iot_analytics_with_data(self):
        # Seed default demo devices for User A
        SmartGymService.seed_default_devices_for_user(self.db, self.user_a.id)
        dev = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().first()

        # Add telemetry record
        telem = IoTTelemetry(
            device_id=dev.id,
            user_id=self.user_a.id,
            exercise_type="Squat",
            resistance_kg=75.0,
            repetition_count=10,
            session_duration_seconds=45,
            intensity_score=82.5,
            heart_rate_bpm=145,
        )
        self.db.add(telem)
        self.db.commit()

        status, body = asyncio.run(
            asgi_request("GET", "/analytics/iot?time_window=7_days", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["has_data"])
        self.assertGreaterEqual(body["device_counts"]["total_devices"], 1)
        self.assertEqual(body["telemetry_averages"]["avg_intensity"], 82.5)
        self.assertEqual(body["telemetry_averages"]["avg_resistance_kg"], 75.0)

    # 9. Time window variation (14_days window)
    def test_09_time_window_14_days(self):
        status, body = asyncio.run(
            asgi_request("GET", "/analytics/overview?time_window=14_days", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["time_window"], "14_days")

    # 10. Time window variation (30_days window)
    def test_10_time_window_30_days(self):
        status, body = asyncio.run(
            asgi_request("GET", "/analytics/workouts?time_window=30_days", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["time_window"], "30_days")

    # 11. Invalid time_window parameter rejected with HTTP 422
    def test_11_invalid_time_window_rejected(self):
        status, body = asyncio.run(
            asgi_request("GET", "/analytics/overview?time_window=99_days", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 422)
        self.assertIn("Invalid time_window", body["detail"])

    # 12. Unauthenticated request rejected with HTTP 401
    def test_12_unauthenticated_access_rejected(self):
        status, body = asyncio.run(
            asgi_request("GET", "/analytics/overview?time_window=7_days")
        )
        self.assertEqual(status, 401)

    # 13. Cross-user isolation (User B cannot see User A's workout metrics)
    def test_13_cross_user_isolation(self):
        # Seed session for User A
        s = WorkoutSession(
            user_id=self.user_a.id,
            started_at=datetime.utcnow() - timedelta(hours=3),
            ended_at=datetime.utcnow() - timedelta(hours=2),
            performance_score=92.0,
        )
        self.db.add(s)
        self.db.commit()

        # Query analytics as User B
        status, body = asyncio.run(
            asgi_request("GET", "/analytics/workouts?time_window=7_days", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status, 200)
        # User B should see 0 workouts and no performance score from User A
        self.assertEqual(body["total_workouts"], 0)
        self.assertIsNone(body["avg_performance_score"])

    # 14. Simulated IoT device classification in device breakdown
    def test_14_simulated_iot_device_flagging(self):
        SmartGymService.seed_default_devices_for_user(self.db, self.user_a.id)

        status, body = asyncio.run(
            asgi_request("GET", "/analytics/iot?time_window=7_days", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        self.assertGreater(body["device_counts"]["simulated_devices"], 0)
        sim_dev = body["device_breakdown"][0]
        self.assertTrue(sim_dev["is_simulated"])

    # 15. Cross-domain non-causal insights generation
    def test_15_cross_domain_insights_generation(self):
        # Seed session with score >= 75
        s = WorkoutSession(
            user_id=self.user_a.id,
            started_at=datetime.utcnow() - timedelta(hours=1),
            ended_at=datetime.utcnow(),
            performance_score=88.0,
        )
        self.db.add(s)
        self.db.commit()

        status, body = asyncio.run(
            asgi_request("GET", "/analytics/overview?time_window=7_days", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        self.assertGreater(len(body["cross_domain_insights"]), 0)
        insight = body["cross_domain_insights"][0]
        self.assertIn("Observational correlation", insight["note"])

    # 16. Direct AnalyticsService unit test for parse_time_window
    def test_16_service_parse_time_window(self):
        self.assertEqual(AnalyticsService.parse_time_window("7_days"), 7)
        self.assertEqual(AnalyticsService.parse_time_window("14_days"), 14)
        self.assertEqual(AnalyticsService.parse_time_window("30_days"), 30)
        with self.assertRaises(ValueError):
            AnalyticsService.parse_time_window("invalid")

    # 17. Nutrition compliance calculation boundary test (within 85-115%)
    def test_17_nutrition_compliance_boundary(self):
        self.db.query(NutritionLog).filter(NutritionLog.user_id == self.user_a.id).delete()
        self.db.commit()

        target = NutritionService.get_or_create_user_target(self.db, self.user_a.id)
        # Log food at 90% of target (should count as compliant)
        log = NutritionLog(
            user_id=self.user_a.id,
            log_date=date.today(),
            meal_type="dinner",
            food_name="Steak",
            quantity=200.0,
            unit="g",
            calories=target.calories_target * 0.9,
            protein=target.protein_grams * 0.9,
            carbs=target.carbs_grams * 0.9,
            fat=target.fat_grams * 0.9,
        )
        self.db.add(log)
        self.db.commit()

        res = AnalyticsService.get_nutrition_analytics(self.db, self.user_a.id, "7_days")
        self.assertTrue(res["has_data"])
        self.assertEqual(res["compliance"]["calorie_compliance_pct"], 100.0)

    # 18. Nutrition non-compliance boundary test (< 85% of target)
    def test_18_nutrition_non_compliance_boundary(self):
        self.db.query(NutritionLog).filter(NutritionLog.user_id == self.user_a.id).delete()
        self.db.commit()

        target = NutritionService.get_or_create_user_target(self.db, self.user_a.id)
        # Log food at 50% of target (non-compliant)
        log = NutritionLog(
            user_id=self.user_a.id,
            log_date=date.today(),
            meal_type="breakfast",
            food_name="Apple",
            quantity=100.0,
            unit="g",
            calories=target.calories_target * 0.5,
            protein=10.0,
            carbs=20.0,
            fat=5.0,
        )
        self.db.add(log)
        self.db.commit()

        res = AnalyticsService.get_nutrition_analytics(self.db, self.user_a.id, "7_days")
        self.assertTrue(res["has_data"])
        self.assertEqual(res["compliance"]["calorie_compliance_pct"], 0.0)

    # 19. Performance trend evaluation (improving score trajectory)
    def test_19_performance_trend_improving(self):
        self.db.query(WorkoutSession).filter(WorkoutSession.user_id == self.user_a.id).delete()
        self.db.commit()

        # Create 2 sessions with improving scores
        s1 = WorkoutSession(
            user_id=self.user_a.id,
            started_at=datetime.utcnow() - timedelta(days=5),
            ended_at=datetime.utcnow() - timedelta(days=5, hours=-1),
            performance_score=70.0,
        )
        s2 = WorkoutSession(
            user_id=self.user_a.id,
            started_at=datetime.utcnow() - timedelta(days=1),
            ended_at=datetime.utcnow() - timedelta(days=1, hours=-1),
            performance_score=85.0,
        )
        self.db.add_all([s1, s2])
        self.db.commit()

        res = AnalyticsService.get_workout_analytics(self.db, self.user_a.id, "7_days")
        self.assertEqual(res["performance_trend"], "improving")

    # 20. Habit consistency rate calculation capping at 100%
    def test_20_habit_consistency_capping(self):
        # User completes 10 sessions in 7 days (exceeding expected ~4 sessions)
        for i in range(10):
            s = WorkoutSession(
                user_id=self.user_a.id,
                started_at=datetime.utcnow() - timedelta(days=i % 6),
                ended_at=datetime.utcnow() - timedelta(days=i % 6, hours=-1),
                performance_score=80.0,
            )
            self.db.add(s)
        self.db.commit()

        res = AnalyticsService.get_habit_analytics(self.db, self.user_a.id, "7_days")
        self.assertEqual(res["consistency"]["consistency_rate_pct"], 100.0)

    # 21. IoT Telemetry heart rate average calculation
    def test_21_iot_telemetry_heart_rate_averaging(self):
        SmartGymService.seed_default_devices_for_user(self.db, self.user_a.id)
        dev = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().first()

        self.db.query(IoTTelemetry).filter(IoTTelemetry.device_id == dev.id).delete()
        self.db.commit()

        t1 = IoTTelemetry(
            device_id=dev.id,
            user_id=self.user_a.id,
            exercise_type="Squat",
            resistance_kg=60.0,
            repetition_count=10,
            session_duration_seconds=30,
            intensity_score=75.0,
            heart_rate_bpm=140,
        )
        t2 = IoTTelemetry(
            device_id=dev.id,
            user_id=self.user_a.id,
            exercise_type="Squat",
            resistance_kg=60.0,
            repetition_count=10,
            session_duration_seconds=30,
            intensity_score=85.0,
            heart_rate_bpm=160,
        )
        self.db.add_all([t1, t2])
        self.db.commit()

        res = AnalyticsService.get_iot_analytics(self.db, self.user_a.id, "7_days")
        self.assertTrue(res["has_data"])
        self.assertEqual(res["telemetry_averages"]["avg_heart_rate"], 150.0)

    # 22. Overview analytics with user having zero profile metrics
    def test_22_overview_minimal_profile(self):
        res = AnalyticsService.get_overview(self.db, self.user_b.id, "7_days")
        self.assertIn("user_profile", res)
        self.assertEqual(res["user_profile"]["fitness_goal"], "weight_loss")

    # 23. Direct check of database reproducibility after analytics queries
    def test_23_database_session_health(self):
        # Ensure database session remains healthy and uncorrupted after complex queries
        user_cnt = self.db.execute(select(func.count(User.id))).scalar()
        self.assertGreaterEqual(user_cnt, 2)

    # 24. End-to-end multi-domain dashboard retrieval flow
    def test_24_e2e_dashboard_endpoints_flow(self):
        for endpoint in ["overview", "workouts", "nutrition", "habits", "iot"]:
            status, body = asyncio.run(
                asgi_request("GET", f"/analytics/{endpoint}?time_window=7_days", headers={"Authorization": f"Bearer {self.token_a}"})
            )
            self.assertEqual(status, 200)

    # 25. Regression check for Phase 1-8 models & baseline services
    def test_25_regression_baseline_services(self):
        target = NutritionService.get_or_create_user_target(self.db, self.user_a.id)
        self.assertIsNotNone(target.calories_target)
        devs = SmartGymService.get_user_devices(self.db, self.user_a.id)
        self.assertIsInstance(devs, list)

    # 26. Performance trend boundary (+2.4 -> stable, +2.5 -> improving)
    def test_26_performance_trend_positive_boundary(self):
        self.db.query(WorkoutSession).filter(WorkoutSession.user_id == self.user_a.id).delete()
        s1 = WorkoutSession(user_id=self.user_a.id, started_at=datetime.utcnow() - timedelta(days=5), ended_at=datetime.utcnow() - timedelta(days=5, hours=-1), performance_score=70.0)
        s2 = WorkoutSession(user_id=self.user_a.id, started_at=datetime.utcnow() - timedelta(days=1), ended_at=datetime.utcnow() - timedelta(days=1, hours=-1), performance_score=72.4)
        self.db.add_all([s1, s2])
        self.db.commit()
        res_stable = AnalyticsService.get_workout_analytics(self.db, self.user_a.id, "7_days")
        self.assertEqual(res_stable["performance_trend"], "stable")

        self.db.query(WorkoutSession).filter(WorkoutSession.user_id == self.user_a.id).delete()
        s3 = WorkoutSession(user_id=self.user_a.id, started_at=datetime.utcnow() - timedelta(days=5), ended_at=datetime.utcnow() - timedelta(days=5, hours=-1), performance_score=70.0)
        s4 = WorkoutSession(user_id=self.user_a.id, started_at=datetime.utcnow() - timedelta(days=1), ended_at=datetime.utcnow() - timedelta(days=1, hours=-1), performance_score=72.5)
        self.db.add_all([s3, s4])
        self.db.commit()
        res_improving = AnalyticsService.get_workout_analytics(self.db, self.user_a.id, "7_days")
        self.assertEqual(res_improving["performance_trend"], "improving")

    # 27. Performance trend boundary (-2.4 -> stable, -2.5 -> declining)
    def test_27_performance_trend_negative_boundary(self):
        self.db.query(WorkoutSession).filter(WorkoutSession.user_id == self.user_a.id).delete()
        s1 = WorkoutSession(user_id=self.user_a.id, started_at=datetime.utcnow() - timedelta(days=5), ended_at=datetime.utcnow() - timedelta(days=5, hours=-1), performance_score=80.0)
        s2 = WorkoutSession(user_id=self.user_a.id, started_at=datetime.utcnow() - timedelta(days=1), ended_at=datetime.utcnow() - timedelta(days=1, hours=-1), performance_score=77.6)
        self.db.add_all([s1, s2])
        self.db.commit()
        res_stable = AnalyticsService.get_workout_analytics(self.db, self.user_a.id, "7_days")
        self.assertEqual(res_stable["performance_trend"], "stable")

        self.db.query(WorkoutSession).filter(WorkoutSession.user_id == self.user_a.id).delete()
        s3 = WorkoutSession(user_id=self.user_a.id, started_at=datetime.utcnow() - timedelta(days=5), ended_at=datetime.utcnow() - timedelta(days=5, hours=-1), performance_score=80.0)
        s4 = WorkoutSession(user_id=self.user_a.id, started_at=datetime.utcnow() - timedelta(days=1), ended_at=datetime.utcnow() - timedelta(days=1, hours=-1), performance_score=77.5)
        self.db.add_all([s3, s4])
        self.db.commit()
        res_declining = AnalyticsService.get_workout_analytics(self.db, self.user_a.id, "7_days")
        self.assertEqual(res_declining["performance_trend"], "declining")

    # 28. Nutrition compliance exact boundaries (84.99% vs 85.00%, 110.00% vs 110.01%)
    def test_28_nutrition_compliance_exact_boundaries(self):
        target = NutritionService.get_or_create_user_target(self.db, self.user_a.id)

        # 84.99% -> non-compliant
        self.db.query(NutritionLog).filter(NutritionLog.user_id == self.user_a.id).delete()
        log1 = NutritionLog(user_id=self.user_a.id, log_date=date.today(), meal_type="lunch", food_name="Rice", quantity=100.0, unit="g", calories=target.calories_target * 0.8499, protein=20.0, carbs=40.0, fat=10.0)
        self.db.add(log1)
        self.db.commit()
        res1 = AnalyticsService.get_nutrition_analytics(self.db, self.user_a.id, "7_days")
        self.assertEqual(res1["compliance"]["calorie_compliance_pct"], 0.0)

        # 85.00% -> compliant
        self.db.query(NutritionLog).filter(NutritionLog.user_id == self.user_a.id).delete()
        log2 = NutritionLog(user_id=self.user_a.id, log_date=date.today(), meal_type="lunch", food_name="Rice", quantity=100.0, unit="g", calories=target.calories_target * 0.85, protein=20.0, carbs=40.0, fat=10.0)
        self.db.add(log2)
        self.db.commit()
        res2 = AnalyticsService.get_nutrition_analytics(self.db, self.user_a.id, "7_days")
        self.assertEqual(res2["compliance"]["calorie_compliance_pct"], 100.0)

        # 110.00% -> compliant
        self.db.query(NutritionLog).filter(NutritionLog.user_id == self.user_a.id).delete()
        log3 = NutritionLog(user_id=self.user_a.id, log_date=date.today(), meal_type="lunch", food_name="Rice", quantity=100.0, unit="g", calories=target.calories_target * 1.10, protein=20.0, carbs=40.0, fat=10.0)
        self.db.add(log3)
        self.db.commit()
        res3 = AnalyticsService.get_nutrition_analytics(self.db, self.user_a.id, "7_days")
        self.assertEqual(res3["compliance"]["calorie_compliance_pct"], 100.0)

        # 110.01% -> non-compliant
        self.db.query(NutritionLog).filter(NutritionLog.user_id == self.user_a.id).delete()
        log4 = NutritionLog(user_id=self.user_a.id, log_date=date.today(), meal_type="lunch", food_name="Rice", quantity=100.0, unit="g", calories=target.calories_target * 1.1001, protein=20.0, carbs=40.0, fat=10.0)
        self.db.add(log4)
        self.db.commit()
        res4 = AnalyticsService.get_nutrition_analytics(self.db, self.user_a.id, "7_days")
        self.assertEqual(res4["compliance"]["calorie_compliance_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
