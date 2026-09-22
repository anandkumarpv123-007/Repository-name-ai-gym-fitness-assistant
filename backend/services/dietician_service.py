import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.nutrition import DietPlan, NutritionTarget
from models.profile import Profile
from models.user import User
from services.nutrition_service import NutritionService


DISCLAIMER_TEXT = (
    "Disclaimer: This nutrition guidance is for general fitness and wellness educational purposes only "
    "and does not constitute medical advice. Consult a healthcare professional before beginning any restrictive diet."
)


class DieticianService:
    """
    AI Dietician & Nutrition Planning service.
    Combines deterministic nutritional targets with LLM or expert rule-based meal generation,
    then automatically derives a structured, categorized grocery list.
    """

    @classmethod
    def generate_diet_plan(
        cls,
        db: Session,
        user_id: int,
        dietary_preference: Optional[str] = None,
        allergies_restrictions: Optional[str] = None,
        meals_per_day: Optional[int] = 3,
        custom_calories: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Generates a complete, structured meal plan matching daily calorie and macro targets.
        If an LLM API key is present, calls LLM with a structured schema prompt;
        otherwise runs the deterministic expert dietician engine.
        """
        # 1. Fetch user profile & targets
        profile = db.execute(
            select(Profile).where(Profile.user_id == user_id)
        ).scalars().first()

        user_target = NutritionService.get_or_create_user_target(db, user_id)

        target_cals = custom_calories if custom_calories is not None else user_target.calories_target
        # Safe metabolic floor to prevent starvation diets (<= 500 kcal is dangerous)
        if target_cals < 800.0:
            target_cals = 800.0
        elif target_cals > 8000.0:
            target_cals = 8000.0

        pref = (dietary_preference or user_target.dietary_preference or "standard").strip().lower()
        restrictions = allergies_restrictions or user_target.allergies_restrictions or ""
        goal = (profile.fitness_goal if profile and profile.fitness_goal else "maintenance").lower()
        num_meals = meals_per_day or user_target.meals_per_day or 3

        # 2. Attempt LLM generation if API key is set
        llm_key = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        plan_data = None
        provider = "deterministic_expert"

        if llm_key:
            try:
                plan_data, provider = cls._call_llm_planner(
                    target_calories=target_cals,
                    target_protein=user_target.protein_grams,
                    target_carbs=user_target.carbs_grams,
                    target_fat=user_target.fat_grams,
                    dietary_preference=pref,
                    allergies=restrictions,
                    goal=goal,
                    meals_count=num_meals,
                )
                # Strict structural verification of LLM output
                if not isinstance(plan_data, dict) or "meals" not in plan_data or not isinstance(plan_data["meals"], list) or len(plan_data["meals"]) == 0:
                    raise ValueError("LLM response did not provide a valid list of meals.")
                for m in plan_data["meals"]:
                    if not isinstance(m, dict) or "items" not in m or "meal_type" not in m:
                        raise ValueError("Malformed meal structure in LLM output.")
            except Exception as e:
                # Graceful fallback to deterministic engine on LLM error
                print(f"[AI Dietician] LLM call failed or unavailable ({e}). Falling back to deterministic expert engine.")
                plan_data = None

        # 3. Fallback to deterministic expert dietician engine if LLM was skipped or failed
        if not plan_data:
            plan_data = cls._generate_deterministic_meal_plan(
                target_calories=target_cals,
                target_protein=user_target.protein_grams,
                target_carbs=user_target.carbs_grams,
                target_fat=user_target.fat_grams,
                dietary_preference=pref,
                allergies=restrictions,
                goal=goal,
                meals_count=num_meals,
            )
            provider = "deterministic_expert"

        # 4. Generate structured grocery list from selected meals
        grocery_list = cls._generate_grocery_list_from_meals(plan_data["meals"])

        # 5. Persist to PostgreSQL database
        diet_plan_record = DietPlan(
            user_id=user_id,
            calories_target=target_cals,
            dietary_preference=pref,
            goal=goal,
            plan_json=json.dumps(plan_data["meals"]),
            grocery_list_json=json.dumps(grocery_list),
            notes=plan_data.get("notes", "Personalized fitness meal plan designed for your goals."),
            provider=provider,
        )
        db.add(diet_plan_record)
        db.commit()
        db.refresh(diet_plan_record)

        return {
            "id": diet_plan_record.id,
            "user_id": user_id,
            "calories_target": target_cals,
            "dietary_preference": pref,
            "goal": goal,
            "meals": plan_data["meals"],
            "total_plan_calories": plan_data["total_calories"],
            "total_plan_protein": plan_data["total_protein"],
            "total_plan_carbs": plan_data["total_carbs"],
            "total_plan_fat": plan_data["total_fat"],
            "grocery_list": grocery_list,
            "notes": diet_plan_record.notes,
            "provider": provider,
            "disclaimer": DISCLAIMER_TEXT,
            "created_at": diet_plan_record.created_at,
        }

    @classmethod
    def get_latest_plan(cls, db: Session, user_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves user's most recent generated diet plan and grocery list."""
        plan = db.execute(
            select(DietPlan)
            .where(DietPlan.user_id == user_id)
            .order_by(DietPlan.created_at.desc())
        ).scalars().first()

        if not plan:
            return None

        meals = json.loads(plan.plan_json)
        grocery_list = json.loads(plan.grocery_list_json)

        tot_cals = round(sum(m.get("total_calories", 0) for m in meals), 1)
        tot_protein = round(sum(m.get("total_protein_g", 0) for m in meals), 1)
        tot_carbs = round(sum(m.get("total_carbs_g", 0) for m in meals), 1)
        tot_fat = round(sum(m.get("total_fat_g", 0) for m in meals), 1)

        return {
            "id": plan.id,
            "user_id": plan.user_id,
            "calories_target": plan.calories_target,
            "dietary_preference": plan.dietary_preference,
            "goal": plan.goal,
            "meals": meals,
            "total_plan_calories": tot_cals,
            "total_plan_protein": tot_protein,
            "total_plan_carbs": tot_carbs,
            "total_plan_fat": tot_fat,
            "grocery_list": grocery_list,
            "notes": plan.notes,
            "provider": plan.provider,
            "disclaimer": DISCLAIMER_TEXT,
            "created_at": plan.created_at,
        }

    @classmethod
    def _generate_deterministic_meal_plan(
        cls,
        target_calories: float,
        target_protein: float,
        target_carbs: float,
        target_fat: float,
        dietary_preference: str,
        allergies: str,
        goal: str,
        meals_count: int = 3,
    ) -> Dict[str, Any]:
        """
        Deterministic expert nutrition rules engine.
        Constructs balanced, real-world meals partitioned to match the target calories and macros.
        """
        pref = (dietary_preference or "standard").lower()

        # Allocate caloric budget across meals
        if meals_count == 4:
            split = [0.25, 0.35, 0.25, 0.15]  # Breakfast, Lunch, Dinner, Snack
            meal_types = ["breakfast", "lunch", "dinner", "snack"]
        else:
            split = [0.30, 0.40, 0.30]  # Breakfast, Lunch, Dinner
            meal_types = ["breakfast", "lunch", "dinner"]

        meals = []
        cals_accum = 0.0
        prot_accum = 0.0
        carb_accum = 0.0
        fat_accum = 0.0

        for i, m_type in enumerate(meal_types):
            m_cal = round(target_calories * split[i], 0)
            m_prot = round(target_protein * split[i], 1)
            m_carb = round(target_carbs * split[i], 1)
            m_fat = round(target_fat * split[i], 1)

            items = cls._select_meal_items(m_type, pref, m_cal, m_prot, m_carb, m_fat)

            # Sum item macros
            m_tot_c = round(sum(it["calories"] for it in items), 1)
            m_tot_p = round(sum(it["protein_g"] for it in items), 1)
            m_tot_cb = round(sum(it["carbs_g"] for it in items), 1)
            m_tot_f = round(sum(it["fat_g"] for it in items), 1)

            cals_accum += m_tot_c
            prot_accum += m_tot_p
            carb_accum += m_tot_cb
            fat_accum += m_tot_f

            meal_name = f"{m_type.capitalize()} — Balanced {goal.replace('_', ' ').capitalize()} Option"

            meals.append({
                "meal_type": m_type,
                "meal_name": meal_name,
                "items": items,
                "total_calories": m_tot_c,
                "total_protein_g": m_tot_p,
                "total_carbs_g": m_tot_cb,
                "total_fat_g": m_tot_f,
                "instructions": f"Cook or prepare ingredients with minimal added sodium. Drink 500ml water with this meal.",
            })

        notes = (
            f"Rule-based plan configured for a {dietary_preference} diet targeting {target_calories} kcal "
            f"with {target_protein}g protein for {goal.replace('_', ' ')}."
        )

        return {
            "meals": meals,
            "total_calories": round(cals_accum, 1),
            "total_protein": round(prot_accum, 1),
            "total_carbs": round(carb_accum, 1),
            "total_fat": round(fat_accum, 1),
            "notes": notes,
        }

    @staticmethod
    def _select_meal_items(
        meal_type: str,
        preference: str,
        cal_budget: float,
        prot_budget: float,
        carb_budget: float,
        fat_budget: float,
    ) -> List[Dict[str, Any]]:
        """Selects realistic ingredients tailored to the meal type and dietary preference."""
        pref = preference.lower()

        if meal_type == "breakfast":
            if pref in ("vegan",):
                return [
                    {"name": "Rolled Oats cooked with Almond Milk", "quantity": "60g", "calories": round(cal_budget * 0.55, 1), "protein_g": 10.0, "carbs_g": 42.0, "fat_g": 5.0},
                    {"name": "Plant Protein Powder (Pea/Brown Rice)", "quantity": "30g", "calories": round(cal_budget * 0.30, 1), "protein_g": 24.0, "carbs_g": 2.0, "fat_g": 2.0},
                    {"name": "Chia Seeds / Sliced Banana", "quantity": "1 serving", "calories": round(cal_budget * 0.15, 1), "protein_g": 2.0, "carbs_g": 15.0, "fat_g": 3.0},
                ]
            elif pref in ("vegetarian",):
                return [
                    {"name": "Rolled Oats Porridge with Cinnamon", "quantity": "60g", "calories": round(cal_budget * 0.45, 1), "protein_g": 10.0, "carbs_g": 42.0, "fat_g": 5.0},
                    {"name": "Greek Yogurt (Non-fat) with Berries", "quantity": "150g", "calories": round(cal_budget * 0.35, 1), "protein_g": 15.0, "carbs_g": 8.0, "fat_g": 1.0},
                    {"name": "Crushed Almonds", "quantity": "15g", "calories": round(cal_budget * 0.20, 1), "protein_g": 3.2, "carbs_g": 3.0, "fat_g": 7.5},
                ]
            elif pref == "keto":
                return [
                    {"name": "Whole Eggs scrambled in Butter", "quantity": "3 large", "calories": round(cal_budget * 0.60, 1), "protein_g": 19.0, "carbs_g": 1.5, "fat_g": 18.0},
                    {"name": "Sliced Avocado", "quantity": "0.5 fruit", "calories": round(cal_budget * 0.25, 1), "protein_g": 1.5, "carbs_g": 2.0, "fat_g": 11.0},
                    {"name": "Sautéed Baby Spinach", "quantity": "80g", "calories": round(cal_budget * 0.15, 1), "protein_g": 2.3, "carbs_g": 2.0, "fat_g": 0.5},
                ]
            else:
                # Standard
                return [
                    {"name": "Scrambled Eggs (2 Whole + 2 Whites)", "quantity": "4 eggs", "calories": round(cal_budget * 0.50, 1), "protein_g": 24.0, "carbs_g": 1.5, "fat_g": 10.0},
                    {"name": "Toasted Whole Wheat Bread", "quantity": "2 slices (80g)", "calories": round(cal_budget * 0.35, 1), "protein_g": 8.0, "carbs_g": 26.0, "fat_g": 2.0},
                    {"name": "Sliced Apple or Orange", "quantity": "1 medium", "calories": round(cal_budget * 0.15, 1), "protein_g": 0.5, "carbs_g": 18.0, "fat_g": 0.2},
                ]

        elif meal_type == "lunch":
            if pref in ("vegan",):
                return [
                    {"name": "Firm Tofu stir-fry with Garlic", "quantity": "150g", "calories": round(cal_budget * 0.45, 1), "protein_g": 22.0, "carbs_g": 4.0, "fat_g": 12.0},
                    {"name": "Cooked Brown Rice or Quinoa", "quantity": "150g", "calories": round(cal_budget * 0.40, 1), "protein_g": 4.5, "carbs_g": 38.0, "fat_g": 1.5},
                    {"name": "Steamed Broccoli and Carrots", "quantity": "120g", "calories": round(cal_budget * 0.15, 1), "protein_g": 3.0, "carbs_g": 8.0, "fat_g": 0.5},
                ]
            elif pref in ("vegetarian",):
                return [
                    {"name": "Spiced Paneer Tikka / Cubes", "quantity": "120g", "calories": round(cal_budget * 0.50, 1), "protein_g": 21.0, "carbs_g": 5.0, "fat_g": 18.0},
                    {"name": "Yellow Dal (Cooked Lentils)", "quantity": "150g", "calories": round(cal_budget * 0.30, 1), "protein_g": 12.0, "carbs_g": 26.0, "fat_g": 1.0},
                    {"name": "Steamed Basmati Rice & Cucumber Salad", "quantity": "120g", "calories": round(cal_budget * 0.20, 1), "protein_g": 3.0, "carbs_g": 28.0, "fat_g": 0.5},
                ]
            else:
                # Standard
                return [
                    {"name": "Grilled Chicken Breast Fillet", "quantity": "160g", "calories": round(cal_budget * 0.45, 1), "protein_g": 42.0, "carbs_g": 0.0, "fat_g": 4.5},
                    {"name": "Steamed Brown Rice", "quantity": "150g", "calories": round(cal_budget * 0.35, 1), "protein_g": 4.0, "carbs_g": 35.0, "fat_g": 1.5},
                    {"name": "Mixed Green Salad with Olive Oil", "quantity": "150g", "calories": round(cal_budget * 0.20, 1), "protein_g": 2.0, "carbs_g": 6.0, "fat_g": 7.0},
                ]

        elif meal_type == "dinner":
            if pref in ("vegan",):
                return [
                    {"name": "Cooked Chickpeas & Lentil Stew", "quantity": "180g", "calories": round(cal_budget * 0.55, 1), "protein_g": 18.0, "carbs_g": 38.0, "fat_g": 3.5},
                    {"name": "Roasted Sweet Potato", "quantity": "140g", "calories": round(cal_budget * 0.30, 1), "protein_g": 2.0, "carbs_g": 28.0, "fat_g": 0.2},
                    {"name": "Sautéed Zucchini and Spinach", "quantity": "100g", "calories": round(cal_budget * 0.15, 1), "protein_g": 2.5, "carbs_g": 5.0, "fat_g": 0.5},
                ]
            elif pref in ("vegetarian",):
                return [
                    {"name": "Chana Masala (Chickpea Curry)", "quantity": "180g", "calories": round(cal_budget * 0.50, 1), "protein_g": 15.0, "carbs_g": 35.0, "fat_g": 5.0},
                    {"name": "Whole Wheat Roti / Chapati", "quantity": "2 pieces", "calories": round(cal_budget * 0.35, 1), "protein_g": 6.0, "carbs_g": 30.0, "fat_g": 2.0},
                    {"name": "Mixed Spiced Vegetable Medley", "quantity": "120g", "calories": round(cal_budget * 0.15, 1), "protein_g": 3.0, "carbs_g": 8.0, "fat_g": 1.0},
                ]
            else:
                # Standard
                return [
                    {"name": "Pan-Seared Salmon Fillet", "quantity": "150g", "calories": round(cal_budget * 0.55, 1), "protein_g": 30.0, "carbs_g": 0.0, "fat_g": 16.0},
                    {"name": "Roasted Sweet Potato Wedges", "quantity": "140g", "calories": round(cal_budget * 0.30, 1), "protein_g": 2.5, "carbs_g": 28.0, "fat_g": 0.5},
                    {"name": "Steamed Asparagus & Lemon", "quantity": "100g", "calories": round(cal_budget * 0.15, 1), "protein_g": 2.5, "carbs_g": 4.0, "fat_g": 0.2},
                ]

        else:
            # Snack
            return [
                {"name": "Greek Yogurt or Whey Shake", "quantity": "1 serving", "calories": round(cal_budget * 0.65, 1), "protein_g": 20.0, "carbs_g": 6.0, "fat_g": 1.0},
                {"name": "Raw Almonds or Mixed Nuts", "quantity": "20g", "calories": round(cal_budget * 0.35, 1), "protein_g": 4.5, "carbs_g": 4.0, "fat_g": 10.0},
            ]

    @classmethod
    def _generate_grocery_list_from_meals(cls, meals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Parses ingredients from all meals and categorizes them into a structured shopping list:
        Protein, Vegetables, Carbohydrates, Healthy Fats, Dairy/Alternatives, Pantry.
        """
        categories: Dict[str, List[str]] = {
            "Protein": [],
            "Vegetables": [],
            "Carbohydrates": [],
            "Healthy Fats": [],
            "Dairy & Plant Alternatives": [],
            "Pantry & Seasonings": [],
        }

        # Standard classification dictionary
        item_classifier = {
            "egg": ("Protein", "1 carton (12 eggs)"),
            "chicken": ("Protein", "500g fresh breast"),
            "salmon": ("Protein", "300g fresh fillet"),
            "tofu": ("Protein", "2 blocks (300g)"),
            "protein powder": ("Protein", "1 tub whey / plant protein"),
            "paneer": ("Dairy & Plant Alternatives", "250g block"),
            "greek yogurt": ("Dairy & Plant Alternatives", "500g tub"),
            "almond milk": ("Dairy & Plant Alternatives", "1 liter"),
            "oats": ("Carbohydrates", "1 pack (500g rolled oats)"),
            "rice": ("Carbohydrates", "1 kg brown / basmati rice"),
            "sweet potato": ("Carbohydrates", "1 kg sweet potatoes"),
            "bread": ("Carbohydrates", "1 loaf whole wheat bread"),
            "roti": ("Carbohydrates", "Whole wheat flour / chapati pack"),
            "chickpeas": ("Carbohydrates", "2 cans / 500g dry chickpeas"),
            "lentils": ("Carbohydrates", "500g yellow / brown lentils"),
            "dal": ("Carbohydrates", "500g yellow / brown lentils"),
            "spinach": ("Vegetables", "250g fresh baby spinach"),
            "broccoli": ("Vegetables", "2 heads fresh broccoli"),
            "carrots": ("Vegetables", "500g carrots"),
            "salad": ("Vegetables", "1 bag mixed greens"),
            "asparagus": ("Vegetables", "1 bunch asparagus"),
            "zucchini": ("Vegetables", "2 medium zucchini"),
            "cucumber": ("Vegetables", "2 fresh cucumbers"),
            "apple": ("Vegetables", "4 fresh apples"),
            "banana": ("Vegetables", "1 bunch bananas"),
            "almond": ("Healthy Fats", "200g raw almonds"),
            "avocado": ("Healthy Fats", "2 ripe avocados"),
            "peanut butter": ("Healthy Fats", "1 jar natural peanut butter"),
            "olive oil": ("Healthy Fats", "500ml extra virgin olive oil"),
            "chia": ("Healthy Fats", "1 pack chia seeds"),
        }

        seen_items = set()

        for meal in meals:
            for it in meal.get("items", []):
                name_lower = it.get("name", "").lower()
                matched = False

                for keyword, (cat, default_qty) in item_classifier.items():
                    if keyword in name_lower and keyword not in seen_items:
                        categories[cat].append(f"{it['name']} ({default_qty})")
                        seen_items.add(keyword)
                        matched = True
                        break

                if not matched and name_lower not in seen_items:
                    # Default assignment
                    categories["Pantry & Seasonings"].append(f"{it['name']}")
                    seen_items.add(name_lower)

        # Always add standard essentials to pantry
        if "Pantry & Seasonings" in categories:
            essentials = ["Sea salt & black pepper", "Cinnamon & garlic powder", "Extra virgin cooking oil"]
            for es in essentials:
                if es not in categories["Pantry & Seasonings"]:
                    categories["Pantry & Seasonings"].append(es)

        return [
            {"category": cat, "items": sorted(items)}
            for cat, items in categories.items()
            if items
        ]

    @classmethod
    def _call_llm_planner(
        cls,
        target_calories: float,
        target_protein: float,
        target_carbs: float,
        target_fat: float,
        dietary_preference: str,
        allergies: str,
        goal: str,
        meals_count: int,
    ) -> tuple[Dict[str, Any], str]:
        """
        Attempts to query external LLM (Gemini or OpenAI) with strict schema constraints.
        Raises exception if key is invalid, library not found, or response cannot be parsed.
        """
        prompt = (
            f"Generate a daily meal plan strictly for these nutritional targets:\n"
            f"- Daily Calories: {target_calories} kcal\n"
            f"- Protein: {target_protein}g\n"
            f"- Carbohydrates: {target_carbs}g\n"
            f"- Fat: {target_fat}g\n"
            f"- Dietary Preference: {dietary_preference}\n"
            f"- Allergies / Exclusions: {allergies or 'None'}\n"
            f"- Goal: {goal}\n"
            f"- Number of Meals: {meals_count}\n\n"
            f"Respond ONLY with valid raw JSON adhering to this exact schema without markdown wrap:\n"
            f'{{"meals": [{{"meal_type": "breakfast", "meal_name": "...", "items": [{{"name": "...", "quantity": "...", "calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}}], "total_calories": 0.0, "total_protein_g": 0.0, "total_carbs_g": 0.0, "total_fat_g": 0.0, "instructions": "..."}}], "notes": "..."}}'
        )

        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            import urllib.request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"response_mime_type": "application/json"},
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                text_content = result["candidates"][0]["content"]["parts"][0]["text"]
                data = json.loads(text_content)
                tot_c = sum(m.get("total_calories", 0) for m in data.get("meals", []))
                tot_p = sum(m.get("total_protein_g", 0) for m in data.get("meals", []))
                tot_cb = sum(m.get("total_carbs_g", 0) for m in data.get("meals", []))
                tot_f = sum(m.get("total_fat_g", 0) for m in data.get("meals", []))
                data["total_calories"] = tot_c
                data["total_protein"] = tot_p
                data["total_carbs"] = tot_cb
                data["total_fat"] = tot_f
                return data, "llm_gemini"

        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            import urllib.request
            url = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are an expert sports dietician. Always output pure valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {openai_key}"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                text_content = result["choices"][0]["message"]["content"]
                data = json.loads(text_content)
                tot_c = sum(m.get("total_calories", 0) for m in data.get("meals", []))
                tot_p = sum(m.get("total_protein_g", 0) for m in data.get("meals", []))
                tot_cb = sum(m.get("total_carbs_g", 0) for m in data.get("meals", []))
                tot_f = sum(m.get("total_fat_g", 0) for m in data.get("meals", []))
                data["total_calories"] = tot_c
                data["total_protein"] = tot_p
                data["total_carbs"] = tot_cb
                data["total_fat"] = tot_f
                return data, "llm_openai"

        raise ValueError("No LLM API keys configured.")
