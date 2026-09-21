"""
AI Gym & Fitness Assistant — Phase 2 End-to-End Practical Smoke Test
Validates:
Dashboard -> Start workout -> Pose/rep tracking -> Complete -> DB Persistence -> History -> Performance Summary
"""

import asyncio
import json
import os
import sys

# Ensure backend root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from auth.token import create_access_token
from database import SessionLocal
from main import app
from models.workout_session import WorkoutSession
from schemas.workout import WorkoutCompleteRequest, RepMetricItem


async def asgi_request(method, path, body=None, headers=None):
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
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

    response_status = 200
    response_body = []
    async def send(msg):
        nonlocal response_status
        if msg["type"] == "http.response.start":
            response_status = msg["status"]
        elif msg["type"] == "http.response.body":
            response_body.append(msg.get("body", b""))

    await app(scope, receive, send)
    raw = b"".join(response_body).decode("utf-8")
    try:
        data = json.loads(raw)
    except Exception:
        data = raw
    return response_status, data


def run_smoke_test():
    print("=" * 70)
    print("PHASE 2 END-TO-END PRACTICAL SMOKE TEST")
    print("=" * 70)

    user_id = 2
    token = create_access_token(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: User navigates from Dashboard -> fetches available exercises
    print("\n[STEP 1] Fetching Exercise Catalogue (GET /exercises)...")
    status, exercises = asyncio.run(asgi_request("GET", "/exercises"))
    assert status == 200, f"Expected 200, got {status}"
    squat_ex = next((e for e in exercises if e["name"].lower() == "squat"), None)
    assert squat_ex is not None, "Squat exercise not found in catalogue"
    print(f"  -> SUCCESS: Found exercise: {squat_ex['name']} (ID: {squat_ex['id']})")

    # Step 2: User starts workout session (POST /workouts/start)
    print("\n[STEP 2] Starting Active Workout Session (POST /workouts/start)...")
    status, start_res = asyncio.run(asgi_request("POST", "/workouts/start", body={"exercise_id": squat_ex["id"]}, headers=headers))
    assert status == 200, f"Expected 200, got {status}: {start_res}"
    session_id = start_res["session_id"]
    print(f"  -> SUCCESS: Workout Session initiated with ID: {session_id}")

    try:
        # Step 3: Pose Tracking & Rep Counting Simulation
        print("\n[STEP 3] Simulating Pose Tracking & Biomechanical Rep Evaluation...")
        reps_done = 3
        rep_metrics_payload = [
            {
                "rep_number": 1,
                "min_knee_angle": 84.5,
                "max_torso_lean": 28.2,
                "duration_seconds": 2.8,
                "form_status": "GOOD",
                "violations": [],
                "metrics_json": {"rom_score": 94.0, "tempo_score": 88.0, "completion_quality": 100.0},
            },
            {
                "rep_number": 2,
                "min_knee_angle": 86.0,
                "max_torso_lean": 31.0,
                "duration_seconds": 3.0,
                "form_status": "GOOD",
                "violations": [],
                "metrics_json": {"rom_score": 92.0, "tempo_score": 90.0, "completion_quality": 100.0},
            },
            {
                "rep_number": 3,
                "min_knee_angle": 88.5,
                "max_torso_lean": 34.5,
                "duration_seconds": 3.1,
                "form_status": "GOOD",
                "violations": [],
                "metrics_json": {"rom_score": 90.0, "tempo_score": 86.0, "completion_quality": 100.0},
            },
        ]
        calculated_score = 90.5
        calories = 12.5
        print(f"  -> Evaluated {reps_done} full-depth reps. Score: {calculated_score}, Calories: {calories} kcal")

        # Step 4: Complete workout session (POST /workouts/{id}/complete)
        print(f"\n[STEP 4] Completing Workout Session (POST /workouts/{session_id}/complete)...")
        complete_body = {
            "exercise_id": squat_ex["id"],
            "reps": reps_done,
            "performance_score": calculated_score,
            "calories": calories,
            "notes": "E2E Smoke Test Session",
            "rep_metrics": rep_metrics_payload,
        }
        status, comp_res = asyncio.run(asgi_request("POST", f"/workouts/{session_id}/complete", body=complete_body, headers=headers))
        assert status == 200, f"Expected 200, got {status}: {comp_res}"
        print(f"  -> SUCCESS: Session marked complete. Score: {comp_res['performance_score']}")

        # Step 5: Verify Persistence & Detailed View (GET /workouts/{id})
        print(f"\n[STEP 5] Inspecting Session Detail & Pose Metrics (GET /workouts/{session_id})...")
        status, detail = asyncio.run(asgi_request("GET", f"/workouts/{session_id}", headers=headers))
        assert status == 200, f"Expected 200, got {status}"
        assert detail["performance_score"] == calculated_score
        assert len(detail["pose_metrics"]) == 3
        print(f"  -> SUCCESS: 3 individual PoseMetric rows verified for session {session_id}.")

        # Step 6: Verify Workout History (GET /workouts/history)
        print("\n[STEP 6] Fetching Workout History (GET /workouts/history)...")
        status, history = asyncio.run(asgi_request("GET", "/workouts/history", headers=headers))
        assert status == 200, f"Expected 200, got {status}"
        found = any(s["session_id"] == session_id for s in history)
        assert found, "Completed workout session not found in user history!"
        print(f"  -> SUCCESS: Session found in history with {history[0]['reps']} reps.")

        # Step 7: Verify Performance Summary & Trend (GET /performance/summary)
        print("\n[STEP 7] Fetching Longitudinal Performance Summary (GET /performance/summary)...")
        status, summary = asyncio.run(asgi_request("GET", "/performance/summary", headers=headers))
        assert status == 200, f"Expected 200, got {status}"
        assert summary["total_sessions"] >= 1
        assert summary["average_score"] is not None
        print(f"  -> SUCCESS: Summary verified: Total sessions = {summary['total_sessions']}, Avg Score = {summary['average_score']}, Trend = {summary['score_trend']}")

        print("\n" + "=" * 70)
        print("[END-TO-END PRACTICAL SMOKE TEST COMPLETED 100% SUCCESSFULLY]")
        print("=" * 70)

    finally:
        # Cleanup test session
        with SessionLocal() as db:
            s_obj = db.get(WorkoutSession, session_id)
            if s_obj:
                db.delete(s_obj)
                db.commit()
                print(f"[CLEANUP] Deleted smoke test session {session_id}.")


if __name__ == "__main__":
    run_smoke_test()
