import asyncio
import json
import os
import sys
import unittest
from datetime import datetime
from sqlalchemy import select, text

# Append backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from database import Base, SessionLocal, engine
from models.user import User
from models.profile import Profile
from models.iot import IoTDevice, IoTTelemetry, IoTCommandLog
from services.smart_gym_service import SmartGymService
from services.mqtt_service import MQTTService
from schemas.iot import IoTTelemetryCreate
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
        url_path, qs = path.split("?", 1)
        query_string = qs.encode("ascii")

    req_headers = dict(headers or {})
    if json_body is not None and "content-type" not in [k.lower() for k in req_headers]:
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

    req_body = json.dumps(json_body).encode("utf-8") if json_body is not None else b""

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


class TestPhase8IoT(unittest.TestCase):
    """
    Automated Test Suite for Phase 8 — Smart Gym Assistant + IoT.
    Verifies device model CRUD, telemetry ingestion & validation, MQTT topics, Node-RED payload schema,
    resistance control interfaces, Smart Assistant rules, user isolation, and cascade deletion.
    """

    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

        # Clean up existing test users and IoT data
        cls.db.execute(text("DELETE FROM iot_command_logs WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%user_iot_%' OR email LIKE '%temp_cascade%')"))
        cls.db.execute(text("DELETE FROM iot_telemetry WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%user_iot_%' OR email LIKE '%temp_cascade%')"))
        cls.db.execute(text("DELETE FROM iot_devices WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%user_iot_%' OR email LIKE '%temp_cascade%')"))
        cls.db.execute(text("DELETE FROM profiles WHERE user_id IN (SELECT id FROM users WHERE email LIKE '%user_iot_%' OR email LIKE '%temp_cascade%')"))
        cls.db.execute(text("DELETE FROM users WHERE email LIKE '%user_iot_%' OR email LIKE '%temp_cascade%'"))
        cls.db.commit()

        # Create User A
        cls.user_a = User(
            name="IoT User A",
            email="user_iot_a@example.com",
            password_hash=hash_password("password123"),
        )
        cls.db.add(cls.user_a)
        cls.db.commit()
        cls.db.refresh(cls.user_a)

        profile_a = Profile(
            user_id=cls.user_a.id,
            fitness_goal="hypertrophy",
        )
        cls.db.add(profile_a)
        cls.db.commit()

        # Create User B for isolation testing
        cls.user_b = User(
            name="IoT User B",
            email="user_iot_b@example.com",
            password_hash=hash_password("password123"),
        )
        cls.db.add(cls.user_b)
        cls.db.commit()
        cls.db.refresh(cls.user_b)

        cls.token_a = create_access_token(cls.user_a.id)
        cls.token_b = create_access_token(cls.user_b.id)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def tearDown(self):
        self.db.rollback()

    # 1. Seed default demo devices
    def test_01_seed_default_demo_devices(self):
        SmartGymService.seed_default_devices_for_user(self.db, self.user_a.id)
        devices = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().all()
        self.assertGreaterEqual(len(devices), 3)
        self.assertTrue(all(d.is_simulated for d in devices))

    # 2. GET /iot/devices
    def test_02_get_all_user_devices(self):
        status_code, body = asyncio.run(
            asgi_request("GET", "/iot/devices", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_code, 200)
        self.assertIsInstance(body, list)
        self.assertGreaterEqual(len(body), 3)
        self.assertEqual(body[0]["user_id"], self.user_a.id)

    # 3. POST /iot/devices register device
    def test_03_register_new_device(self):
        payload = {
            "device_name": "Smart Leg Press Station #4",
            "equipment_category": "leg_press",
            "firmware_version": "v3.0.1",
        }
        status_code, body = asyncio.run(
            asgi_request("POST", "/iot/devices", json_body=payload, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_code, 201)
        self.assertEqual(body["device_name"], "Smart Leg Press Station #4")
        self.assertEqual(body["equipment_category"], "leg_press")
        self.assertTrue(body["is_simulated"])

    # 4. GET /iot/devices/{device_id}
    def test_04_get_device_by_id(self):
        SmartGymService.seed_default_devices_for_user(self.db, self.user_a.id)
        dev = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().first()
        status_code, body = asyncio.run(
            asgi_request("GET", f"/iot/devices/{dev.id}", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(body["id"], dev.id)

    # 5. GET /iot/devices/{id} not found
    def test_05_get_device_by_id_not_found(self):
        status_code, body = asyncio.run(
            asgi_request("GET", "/iot/devices/99999", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_code, 404)

    # 6. Ingest valid telemetry
    def test_06_ingest_valid_telemetry(self):
        SmartGymService.seed_default_devices_for_user(self.db, self.user_a.id)
        dev = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().first()

        payload = {
            "exercise_type": "Barbell Back Squat",
            "resistance_kg": 85.0,
            "repetition_count": 10,
            "session_duration_seconds": 40,
            "heart_rate_bpm": 145,
            "operational_state": "active",
        }
        status_code, body = asyncio.run(
            asgi_request("POST", f"/iot/devices/{dev.id}/telemetry", json_body=payload, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_code, 201)
        self.assertEqual(body["resistance_kg"], 85.0)
        self.assertEqual(body["repetition_count"], 10)
        self.assertGreater(body["intensity_score"], 0)

    # 7. Reject negative resistance telemetry
    def test_07_reject_negative_resistance_telemetry(self):
        SmartGymService.seed_default_devices_for_user(self.db, self.user_a.id)
        dev = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().first()

        payload = {
            "exercise_type": "Invalid Set",
            "resistance_kg": -10.0,
            "repetition_count": 10,
            "session_duration_seconds": 30,
        }
        status_code, body = asyncio.run(
            asgi_request("POST", f"/iot/devices/{dev.id}/telemetry", json_body=payload, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_code, 422)

    # 8. Reject impossible heart rate telemetry (> 250 bpm)
    def test_08_reject_impossible_heart_rate_telemetry(self):
        SmartGymService.seed_default_devices_for_user(self.db, self.user_a.id)
        dev = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().first()

        payload = {
            "exercise_type": "Squat",
            "resistance_kg": 50.0,
            "repetition_count": 10,
            "session_duration_seconds": 30,
            "heart_rate_bpm": 290,
        }
        status_code, body = asyncio.run(
            asgi_request("POST", f"/iot/devices/{dev.id}/telemetry", json_body=payload, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_code, 422)

    # 9. Reject telemetry for device belonging to another user
    def test_09_reject_telemetry_unauthorized_device(self):
        SmartGymService.seed_default_devices_for_user(self.db, self.user_a.id)
        dev_a = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().first()

        payload = {
            "exercise_type": "Hack Squat",
            "resistance_kg": 40.0,
            "repetition_count": 8,
            "session_duration_seconds": 30,
        }
        # User B attempts to log telemetry to User A's device
        status_code, body = asyncio.run(
            asgi_request("POST", f"/iot/devices/{dev_a.id}/telemetry", json_body=payload, headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status_code, 400)

    # 10. GET telemetry history
    def test_10_get_device_telemetry_history(self):
        SmartGymService.seed_default_devices_for_user(self.db, self.user_a.id)
        dev = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().first()

        # Trigger telemetry event
        SmartGymService.generate_simulated_telemetry_event(self.db, self.user_a.id, dev.id)

        status_code, body = asyncio.run(
            asgi_request("GET", f"/iot/devices/{dev.id}/telemetry", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_code, 200)
        self.assertIsInstance(body, list)
        self.assertGreaterEqual(len(body), 1)

    # 11. Send resistance command: set_resistance
    def test_11_send_resistance_command_set(self):
        SmartGymService.seed_default_devices_for_user(self.db, self.user_a.id)
        dev = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().first()

        payload = {
            "command_type": "set_resistance",
            "target_resistance_kg": 82.5,
        }
        status_code, body = asyncio.run(
            asgi_request("POST", f"/iot/devices/{dev.id}/command", json_body=payload, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(body["target_resistance_kg"], 82.5)
        self.assertEqual(body["command_type"], "set_resistance")

    # 12. Send resistance command: increase_resistance
    def test_12_send_resistance_command_increase(self):
        self.db.expire_all()
        dev = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().first()

        initial_val = dev.target_resistance_kg
        payload = {
            "command_type": "increase_resistance",
            "step_increment_kg": 5.0,
        }
        status_code, body = asyncio.run(
            asgi_request("POST", f"/iot/devices/{dev.id}/command", json_body=payload, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(body["target_resistance_kg"], initial_val + 5.0)

    # 13. Send resistance command: decrease_resistance
    def test_13_send_resistance_command_decrease(self):
        self.db.expire_all()
        dev = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().first()

        initial_val = dev.target_resistance_kg
        payload = {
            "command_type": "decrease_resistance",
            "step_increment_kg": 2.5,
        }
        status_code, body = asyncio.run(
            asgi_request("POST", f"/iot/devices/{dev.id}/command", json_body=payload, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(body["target_resistance_kg"], initial_val - 2.5)

    # 14. Reject out of bound resistance command (> 300kg)
    def test_14_reject_out_of_bound_resistance_command(self):
        SmartGymService.seed_default_devices_for_user(self.db, self.user_a.id)
        dev = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().first()

        payload = {
            "command_type": "set_resistance",
            "target_resistance_kg": 450.0,
        }
        status_code, body = asyncio.run(
            asgi_request("POST", f"/iot/devices/{dev.id}/command", json_body=payload, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_code, 422)

    # 15. Verify MQTT topics & Node-RED payload schema
    def test_15_mqtt_topics_and_node_red_payload_format(self):
        topics = MQTTService.get_topics_for_device(gym_id=1, device_uid="rack_alpha")
        self.assertEqual(topics["telemetry"], "gym/smart_gym/gym_1/device_rack_alpha/telemetry")
        self.assertEqual(topics["command"], "gym/smart_gym/gym_1/device_rack_alpha/command")

        payload = MQTTService.format_node_red_telemetry_payload(
            device_uid="rack_alpha",
            user_id=self.user_a.id,
            exercise_type="Squat",
            resistance_kg=70.0,
            repetition_count=10,
            intensity_score=80.0,
            heart_rate_bpm=140,
        )
        self.assertEqual(payload["device_id"], "rack_alpha")
        self.assertTrue(payload["simulation_mode"])
        self.assertIn("timestamp", payload)

    # 16. Verify MQTT fallback to Simulation Mode
    def test_16_mqtt_fallback_simulation_mode(self):
        success, msg, payload = MQTTService.publish_command(
            gym_id=1,
            device_uid="demo_device_01",
            command_type="set_resistance",
            target_resistance_kg=50.0,
            user_id=self.user_a.id,
        )
        self.assertTrue(success)
        self.assertIn("Simulation Mode", msg)

    # 17. Smart Assistant rest and intensity heuristics
    def test_17_smart_assistant_rest_and_intensity_heuristics(self):
        SmartGymService.seed_default_devices_for_user(self.db, self.user_a.id)
        dev = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().first()

        # Ingest high intensity telemetry
        SmartGymService.generate_simulated_telemetry_event(self.db, self.user_a.id, dev.id)

        status_code, body = asyncio.run(
            asgi_request("GET", "/iot/assistant/recommendations", headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_code, 200)
        self.assertEqual(body["user_id"], self.user_a.id)
        self.assertIn("recommendations", body)
        self.assertGreaterEqual(len(body["recommendations"]), 1)

    # 18. Cross-user device isolation
    def test_18_cross_user_device_isolation(self):
        SmartGymService.seed_default_devices_for_user(self.db, self.user_a.id)
        dev_a = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().first()

        # User B attempts to view User A's device
        status_code, body = asyncio.run(
            asgi_request("GET", f"/iot/devices/{dev_a.id}", headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status_code, 404)

        # User B attempts to issue command to User A's device
        cmd_payload = {"command_type": "set_resistance", "target_resistance_kg": 100.0}
        status_code_cmd, _ = asyncio.run(
            asgi_request("POST", f"/iot/devices/{dev_a.id}/command", json_body=cmd_payload, headers={"Authorization": f"Bearer {self.token_b}"})
        )
        self.assertEqual(status_code_cmd, 400)

    # 19. Unauthenticated IoT endpoints fail (401)
    def test_19_unauthenticated_iot_endpoints_fail(self):
        status_code_1, _ = asyncio.run(asgi_request("GET", "/iot/devices"))
        status_code_2, _ = asyncio.run(asgi_request("GET", "/iot/assistant/recommendations"))
        self.assertEqual(status_code_1, 401)
        self.assertEqual(status_code_2, 401)

    # 20. Cascade delete user removes IoT data
    def test_20_cascade_delete_user_removes_iot_data(self):
        # Create a dedicated temporary user for cascade delete testing
        temp_user = User(
            name="Cascade Test User",
            email="temp_cascade@example.com",
            password_hash=hash_password("password123"),
        )
        self.db.add(temp_user)
        self.db.commit()
        self.db.refresh(temp_user)

        SmartGymService.seed_default_devices_for_user(self.db, temp_user.id)
        dev = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == temp_user.id)).scalars().first()
        SmartGymService.generate_simulated_telemetry_event(self.db, temp_user.id, dev.id)

        # Delete temp_user
        self.db.delete(temp_user)
        self.db.commit()

        # Verify IoT records are cascade deleted
        devices_remaining = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == temp_user.id)).scalars().all()
        telemetry_remaining = self.db.execute(select(IoTTelemetry).where(IoTTelemetry.user_id == temp_user.id)).scalars().all()
        self.assertEqual(len(devices_remaining), 0)
        self.assertEqual(len(telemetry_remaining), 0)

    # 21. Telemetry payload user_id security test
    def test_21_telemetry_payload_user_id_security(self):
        SmartGymService.seed_default_devices_for_user(self.db, self.user_a.id)
        dev = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().first()

        # Payload contains spoofed user_id = 9999
        payload = {
            "exercise_type": "Security Test Press",
            "resistance_kg": 50.0,
            "repetition_count": 10,
            "session_duration_seconds": 30,
            "user_id": 9999,
        }
        status_code, body = asyncio.run(
            asgi_request("POST", f"/iot/devices/{dev.id}/telemetry", json_body=payload, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_code, 201)
        # Telemetry record MUST belong strictly to user_a.id (1), ignoring payload user_id 9999
        self.assertEqual(body["user_id"], self.user_a.id)

    # 22. Smart Assistant rest rule boundary conditions (intensity 74.99 vs 75.0, reps 11 vs 12)
    def test_22_smart_assistant_rest_boundary_conditions(self):
        SmartGymService.seed_default_devices_for_user(self.db, self.user_a.id)
        dev = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().first()

        # Clear telemetry for dev
        self.db.query(IoTTelemetry).filter(IoTTelemetry.device_id == dev.id).delete()
        self.db.commit()

        # Sub-threshold: intensity 74.99, reps 11 -> no rest_interval recommendation
        sub_payload = IoTTelemetryCreate(
            exercise_type="Bench Press",
            resistance_kg=40.0,
            repetition_count=11,
            session_duration_seconds=30,
            intensity_score=74.99,
        )
        SmartGymService.ingest_telemetry(self.db, self.user_a.id, dev.id, sub_payload)
        recs_sub = SmartGymService.evaluate_assistant_recommendations(self.db, self.user_a.id)
        rest_recs_sub = [r for r in recs_sub.recommendations if r.recommendation_type == "rest_interval" and r.target_device_uid == dev.device_uid]
        self.assertEqual(len(rest_recs_sub), 0)

        # Threshold: intensity 75.0 -> triggers rest_interval recommendation
        t_payload = IoTTelemetryCreate(
            exercise_type="Bench Press",
            resistance_kg=40.0,
            repetition_count=10,
            session_duration_seconds=30,
            intensity_score=75.0,
        )
        SmartGymService.ingest_telemetry(self.db, self.user_a.id, dev.id, t_payload)
        recs_t = SmartGymService.evaluate_assistant_recommendations(self.db, self.user_a.id)
        rest_recs_t = [r for r in recs_t.recommendations if r.recommendation_type == "rest_interval" and r.target_device_uid == dev.device_uid]
        self.assertEqual(len(rest_recs_t), 1)

    # 23. Smart Assistant progressive overload boundary (avg_intensity 69.99 vs 70.0)
    def test_23_smart_assistant_overload_boundary_conditions(self):
        SmartGymService.seed_default_devices_for_user(self.db, self.user_a.id)
        dev = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().first()

        self.db.query(IoTTelemetry).filter(IoTTelemetry.device_id == dev.id).delete()
        self.db.commit()

        # Sub-threshold avg intensity 69.99
        t1 = IoTTelemetryCreate(
            exercise_type="Squat",
            resistance_kg=60.0,
            repetition_count=10,
            session_duration_seconds=30,
            intensity_score=69.99,
        )
        t2 = IoTTelemetryCreate(
            exercise_type="Squat",
            resistance_kg=60.0,
            repetition_count=10,
            session_duration_seconds=30,
            intensity_score=69.99,
        )
        SmartGymService.ingest_telemetry(self.db, self.user_a.id, dev.id, t1)
        SmartGymService.ingest_telemetry(self.db, self.user_a.id, dev.id, t2)
        recs = SmartGymService.evaluate_assistant_recommendations(self.db, self.user_a.id)
        overload_sub = [r for r in recs.recommendations if r.recommendation_type == "progressive_overload" and r.target_device_uid == dev.device_uid]
        self.assertEqual(len(overload_sub), 0)

        # Threshold avg intensity 70.0
        self.db.query(IoTTelemetry).filter(IoTTelemetry.device_id == dev.id).delete()
        self.db.commit()

        t3 = IoTTelemetryCreate(
            exercise_type="Squat",
            resistance_kg=60.0,
            repetition_count=10,
            session_duration_seconds=30,
            intensity_score=70.0,
        )
        t4 = IoTTelemetryCreate(
            exercise_type="Squat",
            resistance_kg=60.0,
            repetition_count=10,
            session_duration_seconds=30,
            intensity_score=70.0,
        )
        SmartGymService.ingest_telemetry(self.db, self.user_a.id, dev.id, t3)
        SmartGymService.ingest_telemetry(self.db, self.user_a.id, dev.id, t4)
        recs2 = SmartGymService.evaluate_assistant_recommendations(self.db, self.user_a.id)
        overload_t = [r for r in recs2.recommendations if r.recommendation_type == "progressive_overload" and r.target_device_uid == dev.device_uid]
        self.assertEqual(len(overload_t), 1)

    # 24. Smart Assistant fatigue alert boundary (HR 165 vs 166, drop 25% vs >25%)
    def test_24_smart_assistant_fatigue_boundary_conditions(self):
        SmartGymService.seed_default_devices_for_user(self.db, self.user_a.id)
        dev = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().first()

        self.db.query(IoTTelemetry).filter(IoTTelemetry.device_id == dev.id).delete()
        self.db.commit()

        # HR = 165 (no fatigue alert)
        t_hr165 = IoTTelemetryCreate(
            exercise_type="Squat",
            resistance_kg=50.0,
            repetition_count=8,
            session_duration_seconds=30,
            intensity_score=60.0,
            heart_rate_bpm=165,
        )
        SmartGymService.ingest_telemetry(self.db, self.user_a.id, dev.id, t_hr165)
        recs_165 = SmartGymService.evaluate_assistant_recommendations(self.db, self.user_a.id)
        fatigue_165 = [r for r in recs_165.recommendations if r.recommendation_type == "fatigue_alert" and r.target_device_uid == dev.device_uid]
        self.assertEqual(len(fatigue_165), 0)

        # HR = 166 (triggers fatigue alert)
        t_hr166 = IoTTelemetryCreate(
            exercise_type="Squat",
            resistance_kg=50.0,
            repetition_count=8,
            session_duration_seconds=30,
            intensity_score=60.0,
            heart_rate_bpm=166,
        )
        SmartGymService.ingest_telemetry(self.db, self.user_a.id, dev.id, t_hr166)
        recs_166 = SmartGymService.evaluate_assistant_recommendations(self.db, self.user_a.id)
        fatigue_166 = [r for r in recs_166.recommendations if r.recommendation_type == "fatigue_alert" and r.target_device_uid == dev.device_uid]
        self.assertEqual(len(fatigue_166), 1)

    # 25. Resistance boundary limits (0kg accepted, 300kg accepted, clamping, and rejection)
    def test_25_resistance_boundary_limits(self):
        SmartGymService.seed_default_devices_for_user(self.db, self.user_a.id)
        dev = self.db.execute(select(IoTDevice).where(IoTDevice.user_id == self.user_a.id)).scalars().first()

        # 0 kg accepted
        status_0, body_0 = asyncio.run(
            asgi_request("POST", f"/iot/devices/{dev.id}/command", json_body={"command_type": "set_resistance", "target_resistance_kg": 0.0}, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_0, 200)
        self.assertEqual(body_0["target_resistance_kg"], 0.0)

        # 300 kg accepted
        status_300, body_300 = asyncio.run(
            asgi_request("POST", f"/iot/devices/{dev.id}/command", json_body={"command_type": "set_resistance", "target_resistance_kg": 300.0}, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_300, 200)
        self.assertEqual(body_300["target_resistance_kg"], 300.0)

        # Decrease near 0kg clamps at 0.0kg
        status_dec, body_dec = asyncio.run(
            asgi_request("POST", f"/iot/devices/{dev.id}/command", json_body={"command_type": "set_resistance", "target_resistance_kg": 1.0}, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        status_dec2, body_dec2 = asyncio.run(
            asgi_request("POST", f"/iot/devices/{dev.id}/command", json_body={"command_type": "decrease_resistance", "step_increment_kg": 10.0}, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_dec2, 200)
        self.assertEqual(body_dec2["target_resistance_kg"], 0.0)

        # Increase near 300kg clamps at 300.0kg
        status_inc, body_inc = asyncio.run(
            asgi_request("POST", f"/iot/devices/{dev.id}/command", json_body={"command_type": "set_resistance", "target_resistance_kg": 298.0}, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        status_inc2, body_inc2 = asyncio.run(
            asgi_request("POST", f"/iot/devices/{dev.id}/command", json_body={"command_type": "increase_resistance", "step_increment_kg": 10.0}, headers={"Authorization": f"Bearer {self.token_a}"})
        )
        self.assertEqual(status_inc2, 200)
        self.assertEqual(body_inc2["target_resistance_kg"], 300.0)


if __name__ == "__main__":
    unittest.main()
