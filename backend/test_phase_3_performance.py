"""
AI Gym & Fitness Assistant — Phase 3 Test Suite
Pose-to-Performance Analyzer & Weekly Progress Intelligence

Comprehensive coverage:
1. Aggregation (zero workouts, one workout, multiple workouts, multiple exercises)
2. Performance Trend (improving, declining, stable, insufficient history)
3. Strongest Improvement Area (measurable improvement, no improvement, tie-breaking)
4. Recurring Form Issues (none, one, multiple, tie-breaking)
5. Weekly Performance API (authenticated, unauthenticated, empty history, cross-user isolation)
"""

import asyncio
from datetime import datetime, timedelta
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from auth.token import create_access_token
from database import SessionLocal
from main import app
from models.user import User
from models.exercise import Exercise
from models.workout_session import WorkoutSession
from models.workout_exercise import WorkoutExercise
from models.pose_metric import PoseMetric
from services.performance_service import PerformanceService


async def asgi_request(method, path, body=None, headers=None):
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


class TestPhase3PerformanceService(unittest.TestCase):
    """Direct unit tests for PerformanceService aggregation, trend, improvement, and form issues."""

    def test_01_empty_history(self):
        """Zero workouts -> insufficient_history, None averages, clean empty state."""
        with SessionLocal() as db:
            # Query non-existent user 99999
            report = PerformanceService.get_weekly_performance_report(db, user_id=99999, days=7)

        self.assertEqual(report["total_sessions"], 0)
        self.assertEqual(report["total_reps"], 0)
        self.assertIsNone(report["average_score"])
        self.assertEqual(report["trend"], "insufficient_history")
        self.assertIsNone(report["score_delta"])
        self.assertEqual(report["recurring_form_issue"], "None — Clean Movement Form")
        self.assertIn("first guided workout", report["next_week_focus"])
        self.assertEqual(len(report["exercise_stats"]), 0)
        self.assertEqual(len(report["form_warnings"]), 0)
        self.assertEqual(len(report["session_history"]), 0)

    def test_02_single_session_insufficient_history(self):
        """Single session -> baseline established, insufficient_history for trend."""
        report = PerformanceService._calculate_strongest_improvement([{"form_score": 90.0}])
        self.assertEqual(report, "Baseline session established")

    def test_03_trend_calculations(self):
        """Validates deterministic trend classifications: improving, declining, stable."""
        # 1. Improving trend: 70.0 -> 85.0 (delta +15.0 >= +2.5)
        scores_improving = [70.0, 72.0, 85.0, 88.0]
        mid = len(scores_improving) // 2
        prior_avg = sum(scores_improving[:mid]) / mid
        recent_avg = sum(scores_improving[mid:]) / (len(scores_improving) - mid)
        delta_imp = round(recent_avg - prior_avg, 1)
        self.assertGreaterEqual(delta_imp, 2.5)

        # 2. Declining trend: 90.0 -> 75.0 (delta -15.0 <= -2.5)
        scores_declining = [90.0, 88.0, 76.0, 74.0]
        mid = len(scores_declining) // 2
        prior_avg = sum(scores_declining[:mid]) / mid
        recent_avg = sum(scores_declining[mid:]) / (len(scores_declining) - mid)
        delta_dec = round(recent_avg - prior_avg, 1)
        self.assertLessEqual(delta_dec, -2.5)

        # 3. Stable trend: 80.0, 81.0, 80.5, 81.0
        scores_stable = [80.0, 81.0, 80.5, 81.0]
        mid = len(scores_stable) // 2
        prior_avg = sum(scores_stable[:mid]) / mid
        recent_avg = sum(scores_stable[mid:]) / (len(scores_stable) - mid)
        delta_stab = round(recent_avg - prior_avg, 1)
        self.assertTrue(-2.5 < delta_stab < 2.5)

    def test_04_strongest_improvement_and_tie_breaking(self):
        """Validates strongest improvement detection and deterministic tie-breaking by component priority."""
        # Case A: Clear winner
        sessions_a = [
            {"rom_score": 70.0, "form_score": 80.0},
            {"rom_score": 90.0, "form_score": 82.0},  # ROM improved +20.0
        ]
        result_a = PerformanceService._calculate_strongest_improvement(sessions_a)
        self.assertIn("Range of Motion", result_a)
        self.assertIn("+20.0 pts", result_a)

        # Case B: Exact Tie (+10.0 for both Form and ROM)
        # Form has higher priority than ROM in COMPONENT_PRIORITY
        sessions_b = [
            {"form_score": 75.0, "rom_score": 75.0},
            {"form_score": 85.0, "rom_score": 85.0},
        ]
        result_b = PerformanceService._calculate_strongest_improvement(sessions_b)
        self.assertIn("Posture & Form Accuracy", result_b)
        self.assertIn("+10.0 pts", result_b)

        # Case C: No improvement (all deltas <= 0)
        sessions_c = [
            {"form_score": 90.0, "rom_score": 90.0},
            {"form_score": 85.0, "rom_score": 85.0},
        ]
        result_c = PerformanceService._calculate_strongest_improvement(sessions_c)
        self.assertEqual(result_c, "Consistent Baseline Performance Across All Components")

    def test_05_recurring_form_issues_and_tie_breaking(self):
        """Validates violation aggregation, counting, and severity tie-breaking."""
        # Case A: None
        issue, warnings = PerformanceService._analyze_recurring_issues([])
        self.assertEqual(issue, "None — Clean Movement Form")
        self.assertEqual(len(warnings), 0)

        # Case B: Clear single issue
        issue_b, warnings_b = PerformanceService._analyze_recurring_issues(
            ["INSUFFICIENT_DEPTH", "INSUFFICIENT_DEPTH"]
        )
        self.assertIn("Insufficient Squat Depth", issue_b)
        self.assertEqual(len(warnings_b), 1)
        self.assertEqual(warnings_b[0]["count"], 2)
        self.assertEqual(warnings_b[0]["percentage"], 100.0)

        # Case C: Multiple issues with tie (1 Depth vs 1 Torso)
        # Depth has higher severity priority than Torso
        issue_c, warnings_c = PerformanceService._analyze_recurring_issues(
            ["EXCESSIVE_TORSO_LEAN", "INSUFFICIENT_DEPTH"]
        )
        self.assertEqual(issue_c, "Insufficient Squat Depth")
        self.assertEqual(len(warnings_c), 2)


class TestPhase3WeeklyAPI(unittest.TestCase):
    """Validates GET /performance/weekly endpoint, authentication, and cross-user isolation."""

    @classmethod
    def setUpClass(cls):
        # Create isolated test users
        with SessionLocal() as db:
            for email in ("phase3_tester@example.com", "phase3_empty@example.com", "phase3_other@example.com"):
                old = db.execute(select(User).where(User.email == email)).scalars().first()
                if old:
                    db.delete(old)
            db.commit()

            u_test = User(name="Phase 3 Tester", email="phase3_tester@example.com", password_hash="test_hash")
            u_empty = User(name="Phase 3 Empty", email="phase3_empty@example.com", password_hash="test_hash")
            u_other = User(name="Phase 3 Other", email="phase3_other@example.com", password_hash="test_hash")
            db.add_all([u_test, u_empty, u_other])
            db.commit()
            db.refresh(u_test)
            db.refresh(u_empty)
            db.refresh(u_other)
            cls.test_user_id = u_test.id
            cls.empty_user_id = u_empty.id
            cls.other_user_id = u_other.id

        cls.test_token = create_access_token(user_id=cls.test_user_id)
        cls.test_headers = {"Authorization": f"Bearer {cls.test_token}"}

        cls.empty_token = create_access_token(user_id=cls.empty_user_id)
        cls.empty_headers = {"Authorization": f"Bearer {cls.empty_token}"}

        cls.other_token = create_access_token(user_id=cls.other_user_id)
        cls.other_headers = {"Authorization": f"Bearer {cls.other_token}"}

    @classmethod
    def tearDownClass(cls):
        with SessionLocal() as db:
            for uid in (cls.test_user_id, cls.empty_user_id, cls.other_user_id):
                u = db.get(User, uid)
                if u:
                    db.delete(u)
            db.commit()

    def test_06_unauthenticated_request_rejected(self):
        """GET /performance/weekly without token returns 401."""
        status_code, _ = asyncio.run(asgi_request("GET", "/performance/weekly"))
        self.assertEqual(status_code, 401)

    def test_07_weekly_api_lifecycle_and_aggregation(self):
        """
        Creates two structured workout sessions for test user with distinct dates and metrics,
        queries GET /performance/weekly, verifies metrics aggregation, trend, and cleans up.
        """
        now = datetime.now()
        with SessionLocal() as db:
            # Session 1: Earlier in week
            s1 = WorkoutSession(
                user_id=self.test_user_id,
                started_at=now - timedelta(days=4),
                ended_at=now - timedelta(days=4, minutes=-20),
                performance_score=78.0,
                calories=15.0,
                notes="Week Start Session",
            )
            db.add(s1)
            db.flush()

            we1 = WorkoutExercise(
                workout_session_id=s1.id,
                exercise_id=1,  # Squat
                sets=1,
                reps=10,
            )
            db.add(we1)

            pm1 = PoseMetric(
                workout_session_id=s1.id,
                rep_number=1,
                min_knee_angle=105.0,
                max_torso_lean=30.0,
                duration_seconds=3.0,
                form_status="INSUFFICIENT",
                violations="INSUFFICIENT_DEPTH",
                metrics_json=json.dumps({"rom_score": 70.0, "form_score": 75.0}),
            )
            db.add(pm1)

            # Session 2: Later in week (Improved)
            s2 = WorkoutSession(
                user_id=self.test_user_id,
                started_at=now - timedelta(days=1),
                ended_at=now - timedelta(days=1, minutes=-25),
                performance_score=88.0,
                calories=20.0,
                notes="Week End Session",
            )
            db.add(s2)
            db.flush()

            we2 = WorkoutExercise(
                workout_session_id=s2.id,
                exercise_id=1,  # Squat
                sets=1,
                reps=12,
            )
            db.add(we2)

            pm2 = PoseMetric(
                workout_session_id=s2.id,
                rep_number=1,
                min_knee_angle=84.0,
                max_torso_lean=25.0,
                duration_seconds=2.9,
                form_status="GOOD",
                violations=None,
                metrics_json=json.dumps({"rom_score": 92.0, "form_score": 90.0}),
            )
            db.add(pm2)

            db.commit()
            s1_id, s2_id = s1.id, s2.id

        try:
            # Query GET /performance/weekly for test user
            status_code, data = asyncio.run(
                asgi_request("GET", "/performance/weekly?days=7", headers=self.test_headers)
            )
            self.assertEqual(status_code, 200)

            # Verify response schema fields
            self.assertIn("reporting_period", data)
            self.assertIn("total_sessions", data)
            self.assertIn("total_reps", data)
            self.assertIn("average_score", data)
            self.assertIn("trend", data)
            self.assertIn("strongest_improvement", data)
            self.assertIn("recurring_form_issue", data)
            self.assertIn("next_week_focus", data)
            self.assertIn("exercise_stats", data)
            self.assertIn("form_warnings", data)
            self.assertIn("session_history", data)

            self.assertEqual(data["total_sessions"], 2)
            self.assertEqual(data["total_reps"], 22)
            self.assertEqual(data["trend"], "improving")
            self.assertGreater(data["score_delta"], 0)
            self.assertIn("Range of Motion", data["strongest_improvement"])
            self.assertIn("Insufficient Squat Depth", data["recurring_form_issue"])

            # Verify exercise-level stats
            self.assertGreaterEqual(len(data["exercise_stats"]), 1)
            ex_stat = data["exercise_stats"][0]
            self.assertEqual(ex_stat["name"], "Squat")
            self.assertEqual(ex_stat["total_reps"], 22)

            # Verify form warnings list
            self.assertGreaterEqual(len(data["form_warnings"]), 1)
            self.assertEqual(data["form_warnings"][0]["violation_code"], "INSUFFICIENT_DEPTH")

            # Verify cross-user isolation: Other user queries weekly report
            # Other user must NOT see test user's session metrics!
            status_other, data_other = asyncio.run(
                asgi_request("GET", "/performance/weekly?days=7", headers=self.other_headers)
            )
            self.assertEqual(status_other, 200)
            self.assertEqual(data_other["total_sessions"], 0)
            other_s_ids = [s["session_id"] for s in data_other.get("session_history", [])]
            self.assertNotIn(s1_id, other_s_ids)
            self.assertNotIn(s2_id, other_s_ids)

        finally:
            # Cleanup test sessions
            with SessionLocal() as db:
                for sid in (s1_id, s2_id):
                    s_obj = db.get(WorkoutSession, sid)
                db.commit()

    def test_08_empty_history_api(self):
        """Authenticated call for a user with zero workouts returns 200 with structured empty report."""
        status_code, data = asyncio.run(
            asgi_request("GET", "/performance/weekly", headers=self.empty_headers)
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(data["total_sessions"], 0)
        self.assertEqual(data["total_reps"], 0)
        self.assertIsNone(data["average_score"])
        self.assertEqual(data["trend"], "insufficient_history")
        self.assertIsNone(data["score_delta"])
        self.assertEqual(data["recurring_form_issue"], "None — Clean Movement Form")

    def test_09_multiple_exercises_aggregation(self):
        """Verifies weekly aggregation accurately breaks down metrics across multiple exercises (Squat & Push-up)."""
        now = datetime.now()
        with SessionLocal() as db:
            # Squat session
            s_squat = WorkoutSession(
                user_id=self.test_user_id,
                started_at=now - timedelta(days=2),
                ended_at=now - timedelta(days=2, minutes=-15),
                performance_score=85.0,
                calories=12.0,
            )
            db.add(s_squat)
            db.flush()
            we_squat = WorkoutExercise(workout_session_id=s_squat.id, exercise_id=1, sets=1, reps=15)
            db.add(we_squat)

            # Push-up session
            s_pushup = WorkoutSession(
                user_id=self.test_user_id,
                started_at=now - timedelta(days=1),
                ended_at=now - timedelta(days=1, minutes=-10),
                performance_score=92.0,
                calories=14.0,
            )
            db.add(s_pushup)
            db.flush()
            we_pushup = WorkoutExercise(workout_session_id=s_pushup.id, exercise_id=2, sets=1, reps=20)
            db.add(we_pushup)

            db.commit()
            sq_id, pu_id = s_squat.id, s_pushup.id

        try:
            status_code, data = asyncio.run(
                asgi_request("GET", "/performance/weekly?days=7", headers=self.test_headers)
            )
            self.assertEqual(status_code, 200)
            self.assertGreaterEqual(data["total_sessions"], 2)
            self.assertGreaterEqual(data["total_reps"], 35)

            ex_names = [e["name"] for e in data["exercise_stats"]]
            self.assertIn("Squat", ex_names)
            self.assertIn("Push-up", ex_names)

        finally:
            with SessionLocal() as db:
                for sid in (sq_id, pu_id):
                    s_obj = db.get(WorkoutSession, sid)
                    if s_obj:
                        db.delete(s_obj)
                db.commit()

    def test_10_declining_trend_api(self):
        """Verifies declining trend detection when recent performance degrades."""
        now = datetime.now()
        with SessionLocal() as db:
            s_high = WorkoutSession(
                user_id=self.test_user_id,
                started_at=now - timedelta(days=3),
                ended_at=now - timedelta(days=3, minutes=-20),
                performance_score=94.0,
            )
            db.add(s_high)
            db.flush()
            we_high = WorkoutExercise(workout_session_id=s_high.id, exercise_id=1, sets=1, reps=10)
            db.add(we_high)

            s_low = WorkoutSession(
                user_id=self.test_user_id,
                started_at=now - timedelta(days=1),
                ended_at=now - timedelta(days=1, minutes=-15),
                performance_score=72.0,  # Delta = 72 - 94 = -22.0
            )
            db.add(s_low)
            db.flush()
            we_low = WorkoutExercise(workout_session_id=s_low.id, exercise_id=1, sets=1, reps=10)
            db.add(we_low)

            db.commit()
            h_id, l_id = s_high.id, s_low.id

        try:
            status_code, data = asyncio.run(
                asgi_request("GET", "/performance/weekly?days=7", headers=self.test_headers)
            )
            self.assertEqual(status_code, 200)
            self.assertEqual(data["trend"], "declining")
            self.assertLessEqual(data["score_delta"], -2.5)

        finally:
            with SessionLocal() as db:
                for sid in (h_id, l_id):
                    s_obj = db.get(WorkoutSession, sid)
                    if s_obj:
                        db.delete(s_obj)
                db.commit()


def run_suite():
    print("=" * 70)
    print("PHASE 3 — POSE-TO-PERFORMANCE ANALYZER & WEEKLY INTELLIGENCE TESTS")
    print("=" * 70)
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("=" * 70)
    if result.wasSuccessful():
        print(f"[ALL {result.testsRun} PHASE 3 TESTS PASSED SUCCESSFULLY]")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(run_suite())
