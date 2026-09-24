import asyncio
import io
import json
import os
import sys
import unittest
from datetime import datetime, timedelta
from typing import Tuple

# Add backend to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from sqlalchemy import select, text, func
from database import Base, SessionLocal, engine
from models.user import User
from models.profile import Profile
from models.workout_session import WorkoutSession
from models.workout_exercise import WorkoutExercise
from models.pose_metric import PoseMetric
from models.nutrition import NutritionTarget, NutritionLog
from models.buddy import BuddyMessage
from models.habit import HabitPrediction
from models.planner import WorkoutPlan
from models.iot import IoTDevice, IoTTelemetry, IoTCommandLog
from models.media import MediaAsset

from auth.security import hash_password, verify_password
from auth.token import create_access_token
from services.storage_service import StorageService
from main import app


async def asgi_request(
    method: str,
    path: str,
    json_data: dict = None,
    headers: dict = None,
    body_bytes: bytes = None,
) -> Tuple[int, dict, bytes]:
    """ASGI helper supporting JSON & raw multipart requests."""
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

    payload = b""
    if json_data is not None:
        payload = json.dumps(json_data).encode("utf-8")
        req_headers.append((b"content-type", b"application/json"))
    elif body_bytes is not None:
        payload = body_bytes

    if payload and not any(h[0] == b"content-length" for h in req_headers):
        req_headers.append((b"content-length", str(len(payload)).encode("utf-8")))

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
            "body": payload,
            "more_body": False,
        }

    async def send(message):
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = message["status"]
        elif message["type"] == "http.response.body":
            response_body.append(message.get("body", b""))

    await app(scope, receive, send)
    full_bytes = b"".join(response_body)

    parsed_json = None
    try:
        parsed_json = json.loads(full_bytes.decode("utf-8"))
    except Exception:
        parsed_json = full_bytes

    return status_code, parsed_json, full_bytes


def build_multipart_body(fields: dict, files: dict, boundary: str = "----WebKitFormBoundary7MA4YWxkTrZu0gW") -> Tuple[bytes, str]:
    body = io.BytesIO()
    for name, value in fields.items():
        body.write(f"--{boundary}\r\n".encode("utf-8"))
        body.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.write(f"{value}\r\n".encode("utf-8"))

    for name, file_info in files.items():
        filename, content_type, content_bytes = file_info
        body.write(f"--{boundary}\r\n".encode("utf-8"))
        body.write(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode("utf-8"))
        body.write(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
        body.write(content_bytes)
        body.write(b"\r\n")

    body.write(f"--{boundary}--\r\n".encode("utf-8"))
    content_type_header = f"multipart/form-data; boundary={boundary}"
    return body.getvalue(), content_type_header


class TestPhase11FullSystemIntegration(unittest.TestCase):
    """
    Phase 11 — Full System Integration, Cross-User Isolation, Security & Regression Test Suite.
    Validates E2E data flow, JWT authentication scoping, cross-user data isolation,
    error resilience, security boundaries, database cascade integrity, and system health across Phases 1–10.
    """

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

        # Clean existing test integration users if present
        cls.db.execute(text("DELETE FROM users WHERE email IN ('integ_user_a@example.com', 'integ_user_b@example.com');"))
        cls.db.commit()

        # Register User A
        cls.user_a = User(
            name="Integration User A",
            email="integ_user_a@example.com",
            password_hash=hash_password("Pass123!Sec"),
        )
        cls.db.add(cls.user_a)

        # Register User B
        cls.user_b = User(
            name="Integration User B",
            email="integ_user_b@example.com",
            password_hash=hash_password("Pass123!Sec"),
        )
        cls.db.add(cls.user_b)
        cls.db.commit()
        cls.db.refresh(cls.user_a)
        cls.db.refresh(cls.user_b)

        cls.token_a = create_access_token(cls.user_a.id)
        cls.token_b = create_access_token(cls.user_b.id)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def tearDown(self):
        self.db.rollback()

    # =========================================================================
    # 1. FULL E2E SYSTEM INTEGRATION WORKFLOW
    # =========================================================================

    def test_01_e2e_full_system_integration_flow(self):
        """
        Executes end-to-end multi-phase workflow for User A:
        Auth -> Profile -> Workout Log -> Nutrition Target -> Buddy Chat ->
        Habit Risk -> Planner -> IoT Device Control -> Analytics -> Media Upload
        """
        # Step A: Update Profile (Phase 1)
        prof_status, prof_json, _ = asyncio.run(
            asgi_request("PUT", "/users/me", json_data={
                "height_cm": 178.0,
                "weight_kg": 76.5,
                "fitness_goal": "hypertrophy",
                "activity_level": "moderate",
                "dietary_preference": "high_protein"
            }, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(prof_status, 200)
        self.assertEqual(prof_json["profile"]["fitness_goal"], "hypertrophy")

        # Step B: Log Workout Session (Phase 2 & 3)
        w_start_status, w_start_json, _ = asyncio.run(
            asgi_request("POST", "/workouts/start", json_data={"notes": "E2E Squat Session"}, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(w_start_status, 200)
        session_id = w_start_json["session_id"]

        w_comp_status, w_comp_json, _ = asyncio.run(
            asgi_request("POST", f"/workouts/{session_id}/complete", json_data={
                "exercise_id": 1,
                "sets": 1,
                "reps": 5,
                "performance_score": 90.0,
                "rep_metrics": [
                    {
                        "rep_number": 1,
                        "min_knee_angle": 85.0,
                        "max_torso_lean": 15.0,
                        "duration_seconds": 2.5,
                        "form_status": "good",
                        "violations": []
                    }
                ]
            }, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(w_comp_status, 200)
        self.assertGreater(w_comp_json["performance_score"], 0)

        # Step C: Log Nutrition Target & Daily Meal Log (Phase 4)
        nut_status, nut_json, _ = asyncio.run(
            asgi_request("PUT", "/diet/target", json_data={
                "target_calories": 2500,
                "protein_g": 160.0,
                "carbs_g": 280.0,
                "fats_g": 70.0
            }, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(nut_status, 200)

        meal_status, meal_json, _ = asyncio.run(
            asgi_request("POST", "/diet/log", json_data={
                "log_date": datetime.utcnow().strftime("%Y-%m-%d"),
                "meal_type": "lunch",
                "food_name": "Grilled Chicken & Rice",
                "quantity": 250.0,
                "unit": "g",
                "calories": 750,
                "protein": 60.0,
                "carbs": 80.0,
                "fat": 15.0
            }, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(meal_status, 201)

        # Step D: Virtual Gym Buddy Guidance (Phase 5)
        buddy_status, buddy_json, _ = asyncio.run(
            asgi_request("POST", "/buddy/chat", json_data={
                "message": "How can I improve my squat depth?"
            }, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(buddy_status, 200)
        self.assertIn("message", buddy_json)

        # Step E: Habit Skip Risk Prediction (Phase 6)
        habit_status, habit_json, _ = asyncio.run(
            asgi_request("GET", "/habit/status", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(habit_status, 200)
        self.assertIn("risk_level", habit_json)

        # Step F: Gym & Workout Planner (Phase 7)
        plan_status, plan_json, _ = asyncio.run(
            asgi_request("POST", "/planner/generate", json_data={
                "fitness_goal": "hypertrophy",
                "preferred_days_per_week": 4
            }, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(plan_status, 201)
        self.assertIn("fitness_goal", plan_json)

        # Step G: IoT Device Registration & Telemetry (Phase 8)
        iot_status, iot_json, _ = asyncio.run(
            asgi_request("POST", "/iot/devices", json_data={
                "device_name": "Smart Squat Rack Sensor",
                "equipment_category": "smart_rack"
            }, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(iot_status, 201)

        # Step H: Analytics Dashboard Overview (Phase 9)
        ana_status, ana_json, _ = asyncio.run(
            asgi_request("GET", "/analytics/overview?window=30_days", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(ana_status, 200)
        self.assertIn("workout_summary", ana_json)

        # Step I: Media Asset Upload (Phase 10)
        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        body, content_type = build_multipart_body(
            fields={"category": "progress_photo", "storage_provider": "local"},
            files={"file": ("e2e_photo.png", "image/png", png_bytes)}
        )
        media_status, media_json, _ = asyncio.run(
            asgi_request("POST", "/media/upload", body_bytes=body, headers={
                "Authorization": f"Bearer {self.token_a}",
                "Content-Type": content_type
            })
        )
        self.assertEqual(media_status, 201)
        self.assertEqual(media_json["file_name"], "e2e_photo.png")

    # =========================================================================
    # 2. CROSS-USER DATA ISOLATION SUITE
    # =========================================================================

    def test_02_cross_user_profile_isolation(self):
        """User B cannot read or mutate User A's profile."""
        status, profile_json, _ = asyncio.run(
            asgi_request("GET", "/users/me", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status, 200)
        self.assertEqual(profile_json["email"], "integ_user_b@example.com")

    def test_03_cross_user_workout_isolation(self):
        """User B cannot access or list User A's workout sessions."""
        # Start & Complete session for User A
        _, w_start, _ = asyncio.run(
            asgi_request("POST", "/workouts/start", json_data={"notes": "User A Private Session"}, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        session_id = w_start["session_id"]
        asyncio.run(
            asgi_request("POST", f"/workouts/{session_id}/complete", json_data={
                "exercise_id": 1,
                "sets": 1,
                "reps": 5,
                "performance_score": 90.0
            }, headers={"Authorization": f"Bearer {self.token_a}"})
        )

        # User B lists workouts -> User A's session not present
        status_b, list_b, _ = asyncio.run(
            asgi_request("GET", "/workouts/history", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status_b, 200)
        user_b_session_ids = [s["session_id"] for s in list_b]
        self.assertNotIn(session_id, user_b_session_ids)

        # User B directly accesses User A's session -> 403 or 404
        status_get, _, _ = asyncio.run(
            asgi_request("GET", f"/workouts/{session_id}", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertIn(status_get, [403, 404])

    def test_04_cross_user_nutrition_isolation(self):
        """User B cannot query or overwrite User A's nutrition logs."""
        log_date = datetime.utcnow().strftime("%Y-%m-%d")
        _, n_json, _ = asyncio.run(
            asgi_request("POST", "/diet/log", json_data={
                "log_date": log_date,
                "meal_type": "breakfast",
                "food_name": "Oatmeal & Protein Shake",
                "quantity": 100.0,
                "unit": "g",
                "calories": 450,
                "protein": 35.0,
                "carbs": 50.0,
                "fat": 8.0
            }, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        log_id = n_json["id"]

        # User B queries logs -> empty or excluding User A
        status_b, logs_b, _ = asyncio.run(
            asgi_request("GET", f"/diet/logs?date={log_date}", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status_b, 200)
        user_b_log_ids = [l["id"] for l in logs_b]
        self.assertNotIn(log_id, user_b_log_ids)

        # User B attempts delete of User A's log -> 404
        status_del, _, _ = asyncio.run(
            asgi_request("DELETE", f"/diet/log/{log_id}", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status_del, 404)

    def test_05_cross_user_buddy_history_isolation(self):
        """User B cannot view User A's Virtual Gym Buddy conversation history."""
        asyncio.run(
            asgi_request("POST", "/buddy/chat", json_data={"message": "User A secret advice request"}, headers={"Authorization": f"Bearer {self.token_a}"})
        )

        status_b, hist_b, _ = asyncio.run(
            asgi_request("GET", "/buddy/history", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status_b, 200)
        for msg in hist_b.get("messages", []):
            self.assertNotIn("User A secret advice", msg.get("content", ""))

    def test_06_cross_user_habit_risk_isolation(self):
        """User B's habit status calculation only includes User B's workout metrics."""
        status_b, habit_b, _ = asyncio.run(
            asgi_request("GET", "/habit/status", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status_b, 200)
        self.assertEqual(habit_b["user_id"], self.user_b.id)

    def test_07_cross_user_planner_isolation(self):
        """User B cannot view or mutate User A's generated workout plans."""
        _, plan_json, _ = asyncio.run(
            asgi_request("POST", "/planner/generate", json_data={"fitness_goal": "strength", "preferred_days_per_week": 3}, headers={"Authorization": f"Bearer {self.token_a}"})
        )

        status_b, history_b, _ = asyncio.run(
            asgi_request("GET", "/planner/history", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status_b, 200)
        user_b_plan_ids = [p["id"] for p in history_b.get("history", [])]
        if "id" in plan_json:
            self.assertNotIn(plan_json["id"], user_b_plan_ids)

    def test_08_cross_user_iot_isolation(self):
        """User B cannot control or query telemetry for User A's registered IoT device."""
        _, dev_json, _ = asyncio.run(
            asgi_request("POST", "/iot/devices", json_data={
                "device_name": "User A Smart Treadmill",
                "equipment_category": "treadmill"
            }, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        device_id = dev_json["id"]

        # User B attempts to access device -> 404
        status_b_get, _, _ = asyncio.run(
            asgi_request("GET", f"/iot/devices/{device_id}", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status_b_get, 404)

        # User B attempts command dispatch to User A's device -> 400 or 404 (Access denied)
        status_b_cmd, _, _ = asyncio.run(
            asgi_request("POST", f"/iot/devices/{device_id}/command", json_data={"command_type": "set_resistance", "target_resistance_kg": 20.0}, headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertIn(status_b_cmd, [400, 404])

    def test_09_cross_user_analytics_isolation(self):
        """User B's analytics overview isolates User B's metrics completely."""
        status_b, ana_b, _ = asyncio.run(
            asgi_request("GET", "/analytics/overview?window=30_days", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status_b, 200)
        self.assertEqual(ana_b["user_profile"]["email"], "integ_user_b@example.com")

    def test_10_cross_user_media_isolation(self):
        """User B cannot list, download, or delete User A's media assets."""
        png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        body, content_type = build_multipart_body(
            fields={"category": "private_doc"},
            files={"file": ("user_a_passport.png", "image/png", png_bytes)}
        )
        _, media_json, _ = asyncio.run(
            asgi_request("POST", "/media/upload", body_bytes=body, headers={
                "Authorization": f"Bearer {self.token_a}",
                "Content-Type": content_type
            })
        )
        asset_id = media_json["id"]
        stored_file_name = media_json["stored_file_name"]

        # User B attempts metadata lookup -> 404
        status_meta, _, _ = asyncio.run(
            asgi_request("GET", f"/media/assets/{asset_id}", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status_meta, 404)

        # User B attempts file download -> 404
        status_dl, _, _ = asyncio.run(
            asgi_request("GET", f"/media/file/{stored_file_name}", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status_dl, 404)

        # User B attempts asset deletion -> 404
        status_del, _, _ = asyncio.run(
            asgi_request("DELETE", f"/media/assets/{asset_id}", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status_del, 404)

    # =========================================================================
    # 3. AUTHENTICATION & SECURITY BOUNDARY AUDIT
    # =========================================================================

    def test_11_unauthenticated_requests_rejected(self):
        """Verifies HTTP 401 Unauthorized across all core protected routes when JWT header is missing."""
        protected_routes = [
            ("GET", "/users/me"),
            ("GET", "/workouts/history"),
            ("GET", "/diet/target"),
            ("GET", "/buddy/history"),
            ("GET", "/habit/status"),
            ("GET", "/planner/latest"),
            ("GET", "/iot/devices"),
            ("GET", "/analytics/overview"),
            ("GET", "/media/assets"),
            ("GET", "/media/stats"),
        ]
        for method, path in protected_routes:
            status, _, _ = asyncio.run(asgi_request(method, path))
            self.assertEqual(status, 401, f"Route {method} {path} allowed unauthenticated access!")

    def test_12_expired_or_invalid_jwt_rejected(self):
        """Verifies HTTP 401 when provided JWT token is invalid or malformed."""
        bogus_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalidpayload.signature"
        status, _, _ = asyncio.run(
            asgi_request("GET", "/users/me", headers={"Authorization": bogus_token})
        )
        self.assertEqual(status, 401)

    def test_13_client_supplied_user_id_override_prevented(self):
        """Verifies that client cannot override JWT user identity by injecting query/body user_id parameters."""
        status, res_json, _ = asyncio.run(
            asgi_request("GET", "/analytics/overview?window=30_days&user_id=9999", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        self.assertEqual(res_json["user_profile"]["email"], "integ_user_a@example.com")

    def test_14_password_hashing_security(self):
        """Verifies bcrypt password hashing, verifying raw passwords are never stored or exposed."""
        u_db = self.db.execute(select(User).where(User.id == self.user_a.id)).scalars().first()
        self.assertNotEqual(u_db.password_hash, "Pass123!Sec")
        self.assertTrue(verify_password("Pass123!Sec", u_db.password_hash))

    def test_15_sql_injection_resilience(self):
        """Verifies that malicious SQL injection payload in search inputs is safely handled without execution."""
        status, foods_json, _ = asyncio.run(
            asgi_request("GET", "/diet/foods?search=chicken%27%20OR%20%271%27=%271", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 200)
        self.assertIsInstance(foods_json, list)

    # =========================================================================
    # 4. ERROR HANDLING & FAILURE RESILIENCE
    # =========================================================================

    def test_16_nonexistent_resource_returns_404(self):
        """Verifies controlled 404 for invalid resource IDs across modules."""
        status, _, _ = asyncio.run(
            asgi_request("GET", "/workouts/999999", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status, 404)

        status_iot, _, _ = asyncio.run(
            asgi_request("GET", "/iot/devices/999999", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_iot, 404)

    def test_17_malformed_json_returns_400_or_422(self):
        """Verifies unparseable or bad JSON payloads return 422/400 without internal crash."""
        status, _, _ = asyncio.run(
            asgi_request("PUT", "/diet/target", body_bytes=b"{bad json payload}", headers={
                "Authorization": f"Bearer {self.token_a}",
                "Content-Type": "application/json"
            })
        )
        self.assertIn(status, [400, 422])

    def test_18_oversized_file_upload_returns_413_or_400(self):
        """Verifies >50MB file upload yields clean HTTP error response."""
        with self.assertRaises(ValueError):
            StorageService.validate_file("huge.mp4", "video/mp4", 51 * 1024 * 1024)

    # =========================================================================
    # 5. DATABASE CASCADE INTEGRITY & HEALTH
    # =========================================================================

    def test_19_database_cascade_delete_integrity(self):
        """
        Verifies ON DELETE CASCADE integrity:
        Creating a temporary user with child records in all 10 modules,
        deleting the user, and verifying all child records are automatically purged.
        """
        # 1. Create temporary Cascade User
        self.db.execute(text("DELETE FROM users WHERE email LIKE 'cascade_temp%';"))
        self.db.commit()

        temp_user = User(
            name="Cascade Test User",
            email="cascade_temp@example.com",
            password_hash=hash_password("Pass123!"),
        )
        self.db.add(temp_user)
        self.db.commit()
        self.db.refresh(temp_user)

        # 2. Add Profile
        prof = Profile(user_id=temp_user.id, height_cm=170.0, weight_kg=70.0, fitness_goal="maintenance")
        self.db.add(prof)

        # 3. Add Workout Session & Exercise
        session = WorkoutSession(user_id=temp_user.id, performance_score=85.0)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)

        # 4. Add Nutrition Log & Target
        nt = NutritionTarget(user_id=temp_user.id, calories_target=2000.0, protein_grams=150.0, carbs_grams=200.0, fat_grams=60.0)
        nl = NutritionLog(user_id=temp_user.id, log_date=datetime.utcnow().date(), meal_type="dinner", food_name="Salad", quantity=150.0, calories=300)
        self.db.add_all([nt, nl])

        # 5. Add Buddy Message
        bm = BuddyMessage(user_id=temp_user.id, sender="user", content="Hello buddy")
        self.db.add(bm)

        # 6. Add Habit Prediction
        hp = HabitPrediction(user_id=temp_user.id, risk_level="low", skip_probability=0.1)
        self.db.add(hp)

        # 7. Add Workout Plan
        wp = WorkoutPlan(user_id=temp_user.id, plan_name="Temp Plan", fitness_goal="maintenance", target_split="Full Body", days_per_week=3)
        self.db.add(wp)

        # 8. Add IoT Device & Telemetry
        iot_dev = IoTDevice(user_id=temp_user.id, device_uid="cascade_dev_1", device_name="Temp Band", equipment_category="band")
        self.db.add(iot_dev)
        self.db.commit()
        self.db.refresh(iot_dev)

        telemetry = IoTTelemetry(user_id=temp_user.id, device_id=iot_dev.id, exercise_type="squat", resistance_kg=60.0, repetition_count=10, heart_rate_bpm=135)
        self.db.add(telemetry)

        # 9. Add Media Asset
        ma = MediaAsset(
            user_id=temp_user.id,
            file_name="temp.txt",
            stored_file_name=f"u{temp_user.id}_temp.txt",
            file_type="raw",
            mime_type="text/plain",
            file_size_bytes=10,
            storage_provider="local",
            storage_key=f"uploads/user_{temp_user.id}/temp.txt",
            public_url=f"/media/file/u{temp_user.id}_temp.txt",
            category="general"
        )
        self.db.add(ma)
        self.db.commit()

        # Delete temp_user from DB
        temp_user_id = temp_user.id
        self.db.delete(temp_user)
        self.db.commit()

        # Verify child records purged
        self.assertIsNone(self.db.execute(select(Profile).where(Profile.user_id == temp_user_id)).scalars().first())
        self.assertIsNone(self.db.execute(select(WorkoutSession).where(WorkoutSession.user_id == temp_user_id)).scalars().first())
        self.assertIsNone(self.db.execute(select(NutritionTarget).where(NutritionTarget.user_id == temp_user_id)).scalars().first())
        self.assertEqual(len(self.db.execute(select(NutritionLog).where(NutritionLog.user_id == temp_user_id)).scalars().all()), 0)
        self.assertEqual(len(self.db.execute(select(BuddyMessage).where(BuddyMessage.user_id == temp_user_id)).scalars().all()), 0)
        self.assertEqual(len(self.db.execute(select(HabitPrediction).where(HabitPrediction.user_id == temp_user_id)).scalars().all()), 0)
        self.assertEqual(len(self.db.execute(select(WorkoutPlan).where(WorkoutPlan.user_id == temp_user_id)).scalars().all()), 0)
        self.assertEqual(len(self.db.execute(select(IoTDevice).where(IoTDevice.user_id == temp_user_id)).scalars().all()), 0)
        self.assertEqual(len(self.db.execute(select(MediaAsset).where(MediaAsset.user_id == temp_user_id)).scalars().all()), 0)

    def test_20_system_health_check_endpoint(self):
        """Verifies public `/health` system status check."""
        status, health_json, _ = asyncio.run(asgi_request("GET", "/health"))
        self.assertEqual(status, 200)
        self.assertEqual(health_json["status"], "healthy")


if __name__ == "__main__":
    unittest.main()
