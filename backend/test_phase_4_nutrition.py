"""
AI Gym & Fitness Assistant — Phase 4 Test Suite
Nutrition Foundation, Food Tracking, AI Dietician & Grocery Planning

Comprehensive test coverage:
1. Deterministic BMI, BMR, TDEE, Caloric & Macro calculations (including edge cases & invalid inputs)
2. Nutrition Targets CRUD & Persistence
3. Verified Food Catalogue retrieval and searching
4. Food logging, daily aggregation, remaining budgets, and deletion
5. AI Dietician meal plan generation & deterministic expert fallback
6. Categorized grocery list generation
7. Security: JWT Authentication and strict cross-user data isolation
"""

import asyncio
from datetime import date, datetime, timedelta
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
from models.profile import Profile
from models.nutrition import NutritionTarget, NutritionLog, DietPlan
from services.nutrition_service import NutritionService
from services.dietician_service import DieticianService


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


class TestPhase4NutritionFoundation(unittest.TestCase):
    """Unit tests for deterministic nutrition mathematical models and formulas."""

    def test_01_bmi_calculation_and_categories(self):
        """Verifies BMI calculation and correct WHO category classifications."""
        # 1. Normal: 70kg, 175cm -> BMI = 70 / (1.75^2) = 22.86 -> 22.9 (Normal weight)
        res_normal = NutritionService.calculate_bmi(height_cm=175.0, weight_kg=70.0)
        self.assertEqual(res_normal["bmi"], 22.9)
        self.assertEqual(res_normal["category"], "Normal weight")
        self.assertEqual(res_normal["healthy_weight_min_kg"], 56.7)
        self.assertEqual(res_normal["healthy_weight_max_kg"], 76.3)

        # 2. Underweight: 45kg, 170cm -> BMI = 45 / (1.7^2) = 15.6 (Underweight)
        res_under = NutritionService.calculate_bmi(height_cm=170.0, weight_kg=45.0)
        self.assertEqual(res_under["category"], "Underweight")

        # 3. Overweight: 85kg, 175cm -> BMI = 85 / (1.75^2) = 27.8 (Overweight)
        res_over = NutritionService.calculate_bmi(height_cm=175.0, weight_kg=85.0)
        self.assertEqual(res_over["category"], "Overweight")

        # 4. Obese: 110kg, 175cm -> BMI = 110 / (1.75^2) = 35.9 (Obese)
        res_obese = NutritionService.calculate_bmi(height_cm=175.0, weight_kg=110.0)
        self.assertEqual(res_obese["category"], "Obese")

    def test_02_bmi_boundary_and_invalid_inputs(self):
        """Verifies boundary values and strict rejection of impossible physiological measurements."""
        # Valid boundaries
        self.assertIsNotNone(NutritionService.calculate_bmi(height_cm=50.0, weight_kg=20.0))
        self.assertIsNotNone(NutritionService.calculate_bmi(height_cm=260.0, weight_kg=350.0))

        # Invalid heights
        with self.assertRaises(ValueError):
            NutritionService.calculate_bmi(height_cm=40.0, weight_kg=70.0)
        with self.assertRaises(ValueError):
            NutritionService.calculate_bmi(height_cm=270.0, weight_kg=70.0)

        # Invalid weights
        with self.assertRaises(ValueError):
            NutritionService.calculate_bmi(height_cm=170.0, weight_kg=10.0)
        with self.assertRaises(ValueError):
            NutritionService.calculate_bmi(height_cm=170.0, weight_kg=400.0)

    def test_03_bmr_and_tdee_formulas(self):
        """Verifies Mifflin-St Jeor equation and activity multiplier logic."""
        # Male: 75kg, 180cm, 30yo -> 10*75 + 6.25*180 - 5*30 + 5 = 750 + 1125 - 150 + 5 = 1730
        bmr_male = NutritionService.calculate_bmr(height_cm=180.0, weight_kg=75.0, age=30, gender="male")
        self.assertEqual(bmr_male, 1730.0)

        # Female: 60kg, 165cm, 25yo -> 10*60 + 6.25*165 - 5*25 - 161 = 600 + 1031.25 - 125 - 161 = 1345.25 -> 1345.2
        bmr_female = NutritionService.calculate_bmr(height_cm=165.0, weight_kg=60.0, age=25, gender="female")
        self.assertAlmostEqual(bmr_female, 1345.2, places=1)

        # TDEE multipliers
        tdee_sedentary = NutritionService.calculate_tdee(bmr=1500.0, activity_level="sedentary")
        self.assertEqual(tdee_sedentary, 1800.0)  # 1500 * 1.2

        tdee_moderate = NutritionService.calculate_tdee(bmr=1500.0, activity_level="moderate")
        self.assertEqual(tdee_moderate, 2325.0)  # 1500 * 1.55

    def test_04_caloric_and_macro_targets_by_goal(self):
        """Verifies deterministic macro calculation and goal adjustments."""
        # 1. Fat loss deficit
        res_cut = NutritionService.calculate_nutrition_targets(
            height_cm=180.0, weight_kg=80.0, fitness_goal="fat_loss", activity_level="moderate"
        )
        self.assertLess(res_cut["recommended_calories"], res_cut["tdee"])
        self.assertGreaterEqual(res_cut["recommended_protein_g"], 160.0)  # 2.0g/kg for 80kg

        # 2. Muscle gain surplus
        res_bulk = NutritionService.calculate_nutrition_targets(
            height_cm=180.0, weight_kg=80.0, fitness_goal="muscle_gain", activity_level="moderate"
        )
        self.assertGreater(res_bulk["recommended_calories"], res_bulk["tdee"])
        self.assertGreaterEqual(res_bulk["recommended_protein_g"], 176.0)  # 2.2g/kg

        # 3. Keto ratio: 70% Fat, 25% Protein, 5% Carbs
        res_keto = NutritionService.calculate_nutrition_targets(
            height_cm=175.0, weight_kg=70.0, dietary_preference="keto"
        )
        # 5% of calories in carbs:
        expected_carb_g = round((res_keto["recommended_calories"] * 0.05) / 4.0, 1)
        self.assertAlmostEqual(res_keto["recommended_carbs_g"], expected_carb_g, delta=1.0)


class TestPhase4NutritionAPIAndDatabase(unittest.TestCase):
    """Integration tests for FastAPI endpoints, database persistence, and user isolation."""

    @classmethod
    def setUpClass(cls):
        with SessionLocal() as db:
            # Clean old test users
            for email in ("phase4_alice@example.com", "phase4_bob@example.com"):
                old = db.execute(select(User).where(User.email == email)).scalars().first()
                if old:
                    db.delete(old)
            db.commit()

            # Create User A (Alice)
            u_a = User(name="Alice Athlete", email="phase4_alice@example.com", password_hash="test_hash")
            db.add(u_a)
            db.commit()
            db.refresh(u_a)
            cls.user_a_id = u_a.id

            # Alice's Profile
            p_a = Profile(
                user_id=u_a.id,
                height_cm=175.0,
                weight_kg=70.0,
                fitness_goal="fat_loss",
                activity_level="moderate",
                dietary_preference="standard",
                gender="female",
            )
            db.add(p_a)

            # Create User B (Bob)
            u_b = User(name="Bob Builder", email="phase4_bob@example.com", password_hash="test_hash")
            db.add(u_b)
            db.commit()
            db.refresh(u_b)
            cls.user_b_id = u_b.id

            # Bob's Profile
            p_b = Profile(
                user_id=u_b.id,
                height_cm=185.0,
                weight_kg=90.0,
                fitness_goal="muscle_gain",
                activity_level="very_active",
                dietary_preference="high_protein",
                gender="male",
            )
            db.add(p_b)
            db.commit()

        cls.token_a = create_access_token(user_id=cls.user_a_id)
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        cls.token_b = create_access_token(user_id=cls.user_b_id)
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

    @classmethod
    def tearDownClass(cls):
        with SessionLocal() as db:
            for uid in (cls.user_a_id, cls.user_b_id):
                u = db.get(User, uid)
                if u:
                    db.delete(u)
            db.commit()

    def test_05_unauthenticated_requests_rejected(self):
        """Protected nutrition endpoints reject requests lacking JWT bearer tokens."""
        endpoints = [
            ("GET", "/diet/bmi"),
            ("GET", "/diet/target"),
            ("POST", "/diet/log"),
            ("GET", "/diet/summary"),
            ("POST", "/diet/plan"),
        ]
        for method, path in endpoints:
            status, _ = asyncio.run(asgi_request(method, path))
            self.assertEqual(status, 401, f"{method} {path} should return 401 when unauthenticated")

    def test_06_public_custom_bmi_api(self):
        """POST /diet/bmi calculates metrics without requiring user login."""
        payload = {
            "height_cm": 180.0,
            "weight_kg": 75.0,
            "age": 28,
            "gender": "male",
            "activity_level": "moderate",
            "fitness_goal": "fat_loss",
        }
        status, data = asyncio.run(asgi_request("POST", "/diet/bmi", body=payload))
        self.assertEqual(status, 200)
        self.assertEqual(data["bmi"], 23.1)
        self.assertEqual(data["category"], "Normal weight")
        self.assertGreater(data["tdee"], 1800.0)

    def test_07_food_catalogue_search_api(self):
        """GET /diet/foods retrieves verified food items and supports keyword filtering."""
        # 1. Fetch all
        status, all_foods = asyncio.run(asgi_request("GET", "/diet/foods"))
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(all_foods), 20)

        # 2. Search for chicken
        status, chicken_res = asyncio.run(asgi_request("GET", "/diet/foods?search=chicken"))
        self.assertEqual(status, 200)
        self.assertTrue(any("chicken" in f["name"].lower() for f in chicken_res))

    def test_08_nutrition_target_get_and_update(self):
        """GET /diet/target auto-initializes target; PUT /diet/target updates targets."""
        # 1. Auto-create from profile
        status, target_a = asyncio.run(asgi_request("GET", "/diet/target", headers=self.headers_a))
        self.assertEqual(status, 200)
        self.assertEqual(target_a["user_id"], self.user_a_id)
        self.assertGreater(target_a["calories_target"], 1200.0)

        # 2. Update target
        update_payload = {
            "calories_target": 2150.0,
            "protein_grams": 150.0,
            "water_liters": 3.5,
        }
        status_up, updated = asyncio.run(asgi_request("PUT", "/diet/target", body=update_payload, headers=self.headers_a))
        self.assertEqual(status_up, 200)
        self.assertEqual(updated["calories_target"], 2150.0)
        self.assertEqual(updated["protein_grams"], 150.0)
        self.assertEqual(updated["water_liters"], 3.5)

    def test_09_food_logging_and_daily_summary(self):
        """POST /diet/log persists foods; GET /diet/summary computes consumed vs remaining macros."""
        today_str = date.today().isoformat()

        # Log 1: Breakfast Eggs
        log1_body = {
            "food_name": "Whole Eggs",
            "quantity": 100.0,
            "unit": "g",
            "meal_type": "breakfast",
            "calories": 143.0,
            "protein": 12.6,
            "carbs": 0.7,
            "fat": 9.5,
        }
        status1, log1 = asyncio.run(asgi_request("POST", "/diet/log", body=log1_body, headers=self.headers_a))
        self.assertEqual(status1, 201)
        self.assertEqual(log1["food_name"], "Whole Eggs")
        log1_id = log1["id"]

        # Log 2: Lunch Chicken & Rice
        log2_body = {
            "food_name": "Grilled Chicken Breast",
            "quantity": 200.0,
            "unit": "g",
            "meal_type": "lunch",
            "calories": 330.0,
            "protein": 62.0,
            "carbs": 0.0,
            "fat": 7.2,
        }
        status2, log2 = asyncio.run(asgi_request("POST", "/diet/log", body=log2_body, headers=self.headers_a))
        self.assertEqual(status2, 201)
        log2_id = log2["id"]

        try:
            # Query Daily Summary
            status_sum, summary = asyncio.run(asgi_request("GET", "/diet/summary", headers=self.headers_a))
            self.assertEqual(status_sum, 200)
            self.assertEqual(summary["total_calories"], 473.0)  # 143 + 330
            self.assertEqual(summary["total_protein"], 74.6)   # 12.6 + 62.0
            self.assertIn("breakfast", summary["meal_breakdown"])
            self.assertIn("lunch", summary["meal_breakdown"])
            self.assertEqual(len(summary["meal_breakdown"]["breakfast"]), 1)

            # Clean up log 1 via DELETE
            del_status, _ = asyncio.run(asgi_request("DELETE", f"/diet/log/{log1_id}", headers=self.headers_a))
            self.assertEqual(del_status, 200)

            # Verify count dropped
            _, summary_after = asyncio.run(asgi_request("GET", "/diet/summary", headers=self.headers_a))
            self.assertEqual(summary_after["total_calories"], 330.0)

        finally:
            with SessionLocal() as db:
                for lid in (log1_id, log2_id):
                    entry = db.get(NutritionLog, lid)
                    if entry:
                        db.delete(entry)
                db.commit()

    def test_10_ai_dietician_plan_grocery_and_user_isolation(self):
        """
        POST /diet/plan generates structured meal plan and grocery list;
        verifies cross-user isolation between User A and User B.
        """
        plan_body = {
            "dietary_preference": "high_protein",
            "meals_per_day": 3,
            "target_calories": 2200.0,
        }
        status_plan, plan_a = asyncio.run(asgi_request("POST", "/diet/plan", body=plan_body, headers=self.headers_a))
        self.assertEqual(status_plan, 201)
        self.assertEqual(plan_a["user_id"], self.user_a_id)
        self.assertEqual(len(plan_a["meals"]), 3)
        self.assertGreater(plan_a["total_plan_calories"], 1800.0)
        self.assertIn("disclaimer", plan_a)
        self.assertIn("medical advice", plan_a["disclaimer"].lower())

        # Verify structured grocery categories
        grocery_cats = [g["category"] for g in plan_a["grocery_list"]]
        self.assertIn("Protein", grocery_cats)
        self.assertIn("Carbohydrates", grocery_cats)

        # Verify GET /diet/plan/latest for User A
        status_latest, latest_a = asyncio.run(asgi_request("GET", "/diet/plan/latest", headers=self.headers_a))
        self.assertEqual(status_latest, 200)
        self.assertEqual(latest_a["id"], plan_a["id"])

        # CROSS-USER ISOLATION:
        # User B queries latest plan: User B has no plan yet!
        # Must return 404 and NOT leak User A's plan.
        status_b, _ = asyncio.run(asgi_request("GET", "/diet/plan/latest", headers=self.headers_b))
        self.assertEqual(status_b, 404)

        # User B queries daily food summary: User B must see 0 calories, not User A's data!
        status_b_sum, sum_b = asyncio.run(asgi_request("GET", "/diet/summary", headers=self.headers_b))
        self.assertEqual(status_b_sum, 200)
        self.assertEqual(sum_b["total_calories"], 0.0)

    def test_11_weekly_nutrition_aggregation(self):
        """GET /diet/weekly computes longitudinal weekly averages, compliance %, and daily macro points."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)

        created_log_ids = []
        with SessionLocal() as db:
            # Add logs for User A across 3 different days
            l1 = NutritionLog(
                user_id=self.user_a_id,
                log_date=today,
                meal_type="breakfast",
                food_name="Oats",
                quantity=50.0,
                unit="g",
                calories=190.0,
                protein=8.0,
                carbs=33.0,
                fat=3.0,
            )
            l2 = NutritionLog(
                user_id=self.user_a_id,
                log_date=yesterday,
                meal_type="lunch",
                food_name="Chicken Salad",
                quantity=250.0,
                unit="g",
                calories=350.0,
                protein=40.0,
                carbs=10.0,
                fat=15.0,
            )
            l3 = NutritionLog(
                user_id=self.user_a_id,
                log_date=two_days_ago,
                meal_type="dinner",
                food_name="Salmon Fillet",
                quantity=150.0,
                unit="g",
                calories=310.0,
                protein=30.0,
                carbs=0.0,
                fat=19.5,
            )
            db.add_all([l1, l2, l3])
            db.commit()
            db.refresh(l1)
            db.refresh(l2)
            db.refresh(l3)
            created_log_ids.extend([l1.id, l2.id, l3.id])

        try:
            # Query GET /diet/weekly?days=7 for User A
            status_w, weekly_a = asyncio.run(asgi_request("GET", "/diet/weekly?days=7", headers=self.headers_a))
            self.assertEqual(status_w, 200)
            self.assertEqual(weekly_a["reporting_period"]["days"], 7)
            self.assertEqual(weekly_a["total_calories"], 850.0)  # 190 + 350 + 310
            self.assertEqual(weekly_a["days_logged"], 3)
            self.assertEqual(len(weekly_a["daily_history"]), 7)
            self.assertAlmostEqual(weekly_a["daily_average_calories"], round(850.0 / 7.0, 1), places=1)
            self.assertIn(weekly_a["compliance_status"], ("on_track", "under_target", "over_target"))

            # CROSS-USER ISOLATION: User B queries weekly summary
            status_wb, weekly_b = asyncio.run(asgi_request("GET", "/diet/weekly?days=7", headers=self.headers_b))
            self.assertEqual(status_wb, 200)
            self.assertEqual(weekly_b["total_calories"], 0.0)
            self.assertEqual(weekly_b["days_logged"], 0)
        finally:
            with SessionLocal() as db:
                for lid in created_log_ids:
                    e = db.get(NutritionLog, lid)
                    if e:
                        db.delete(e)
                db.commit()

    def test_12_food_log_input_validation_and_boundaries(self):
        """Validates rejection of negative or physically impossible nutrition quantities & calories."""
        # 1. Negative quantity
        bad_qty = {
            "food_name": "Apple",
            "quantity": -50.0,
            "unit": "g",
            "meal_type": "snack",
            "calories": 50.0,
        }
        status_q, _ = asyncio.run(asgi_request("POST", "/diet/log", body=bad_qty, headers=self.headers_a))
        self.assertEqual(status_q, 422)

        # 2. Zero quantity
        zero_qty = {
            "food_name": "Apple",
            "quantity": 0.0,
            "unit": "g",
            "meal_type": "snack",
            "calories": 50.0,
        }
        status_zq, _ = asyncio.run(asgi_request("POST", "/diet/log", body=zero_qty, headers=self.headers_a))
        self.assertEqual(status_zq, 422)

        # 3. Excessive calories (> 5000 kcal for single item)
        bad_cal = {
            "food_name": "Gigantic Feast",
            "quantity": 1000.0,
            "unit": "g",
            "meal_type": "dinner",
            "calories": 9999.0,
        }
        status_c, _ = asyncio.run(asgi_request("POST", "/diet/log", body=bad_cal, headers=self.headers_a))
        self.assertEqual(status_c, 422)

        # 4. Negative macros
        bad_macro = {
            "food_name": "Bad Protein",
            "quantity": 100.0,
            "unit": "g",
            "meal_type": "lunch",
            "calories": 100.0,
            "protein": -10.0,
        }
        status_m, _ = asyncio.run(asgi_request("POST", "/diet/log", body=bad_macro, headers=self.headers_a))
        self.assertEqual(status_m, 422)

        # 5. Invalid nutrition target updates (< 800 or > 8000 kcal)
        bad_target = {"calories_target": 400.0}
        status_t, _ = asyncio.run(asgi_request("PUT", "/diet/target", body=bad_target, headers=self.headers_a))
        self.assertEqual(status_t, 422)

        bad_target_high = {"calories_target": 12000.0}
        status_th, _ = asyncio.run(asgi_request("PUT", "/diet/target", body=bad_target_high, headers=self.headers_a))
        self.assertEqual(status_th, 422)

    def test_13_llm_safety_and_starvation_prevention(self):
        """
        Verifies LLM safety, starvation diet rejection (< 800 kcal),
        medical disclaimer presence, and graceful fallback on malformed/failing LLM responses.
        """
        # 1. Starvation diet requested: target_calories = 500 kcal rejected by API with HTTP 422
        starvation_payload = {
            "dietary_preference": "standard",
            "target_calories": 500.0,  # Below safe metabolic floor
        }
        status_starve, _ = asyncio.run(asgi_request("POST", "/diet/plan", body=starvation_payload, headers=self.headers_a))
        self.assertEqual(status_starve, 422)

        # 2. Programmatic safety check: DieticianService.generate_diet_plan floors any custom_calories < 800 to 800.0
        with SessionLocal() as db:
            safe_plan = DieticianService.generate_diet_plan(
                db,
                user_id=self.user_a_id,
                custom_calories=400.0,  # Attempt unsafe 400 kcal
            )
            self.assertGreaterEqual(safe_plan["calories_target"], 800.0)
            self.assertIn("disclaimer", safe_plan)
            self.assertIn("medical advice", safe_plan["disclaimer"].lower())

            # 3. Missing inputs fallback: Test with completely empty preference/allergies
            fallback_plan = DieticianService.generate_diet_plan(
                db,
                user_id=self.user_a_id,
                dietary_preference=None,
                allergies_restrictions=None,
                meals_per_day=None,
            )
            self.assertIsNotNone(fallback_plan["meals"])
            self.assertGreater(len(fallback_plan["meals"]), 0)

            # 4. Simulated LLM Failure / Malformed Response Fallback
            original_call_llm = DieticianService._call_llm_planner
            try:
                def mock_broken_llm(*args, **kwargs):
                    raise ValueError("Simulated LLM network timeout or invalid JSON output")
                DieticianService._call_llm_planner = mock_broken_llm

                # Trigger plan generation while LLM is simulated broken
                resilient_plan = DieticianService.generate_diet_plan(
                    db,
                    user_id=self.user_a_id,
                    dietary_preference="vegan",
                    meals_per_day=3,
                )
                self.assertEqual(resilient_plan["provider"], "deterministic_expert")
                self.assertEqual(len(resilient_plan["meals"]), 3)
                self.assertGreater(resilient_plan["total_plan_calories"], 0.0)
            finally:
                DieticianService._call_llm_planner = original_call_llm


def run_suite():
    print("=" * 70)
    print("PHASE 4 — NUTRITION & AI DIETICIAN COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("=" * 70)
    if result.wasSuccessful():
        print(f"[ALL {result.testsRun} PHASE 4 TESTS PASSED SUCCESSFULLY]")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(run_suite())
