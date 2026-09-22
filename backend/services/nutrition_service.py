from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.nutrition import NutritionLog, NutritionTarget
from models.profile import Profile
from models.user import User


# Verified standard fitness food database (Nutrients per 100g)
# Source Authority: USDA FoodData Central (FDC) — https://fdc.nal.usda.gov/
STANDARD_FOOD_CATALOGUE: List[Dict[str, Any]] = [
    {"id": "egg_whole", "name": "Whole Egg (Large)", "category": "Protein", "serving_size_g": 50.0, "calories_per_100g": 143.0, "protein_per_100g": 12.6, "carbs_per_100g": 0.7, "fat_per_100g": 9.5, "source": "USDA FoodData Central", "fdc_id": "171287"},
    {"id": "egg_white", "name": "Egg Whites", "category": "Protein", "serving_size_g": 100.0, "calories_per_100g": 52.0, "protein_per_100g": 11.0, "carbs_per_100g": 0.7, "fat_per_100g": 0.2, "source": "USDA FoodData Central", "fdc_id": "172183"},
    {"id": "chicken_breast", "name": "Chicken Breast (Boneless/Skinless)", "category": "Protein", "serving_size_g": 150.0, "calories_per_100g": 165.0, "protein_per_100g": 31.0, "carbs_per_100g": 0.0, "fat_per_100g": 3.6, "source": "USDA FoodData Central", "fdc_id": "171077"},
    {"id": "salmon_fillet", "name": "Salmon Fillet", "category": "Protein", "serving_size_g": 150.0, "calories_per_100g": 208.0, "protein_per_100g": 20.0, "carbs_per_100g": 0.0, "fat_per_100g": 13.0, "source": "USDA FoodData Central", "fdc_id": "175167"},
    {"id": "paneer", "name": "Paneer (Cottage Cheese)", "category": "Dairy/Protein", "serving_size_g": 100.0, "calories_per_100g": 296.0, "protein_per_100g": 18.0, "carbs_per_100g": 4.5, "fat_per_100g": 22.0, "source": "USDA FoodData Central", "fdc_id": "2259685"},
    {"id": "tofu_firm", "name": "Firm Tofu", "category": "Plant Protein", "serving_size_g": 100.0, "calories_per_100g": 144.0, "protein_per_100g": 17.3, "carbs_per_100g": 2.8, "fat_per_100g": 8.7, "source": "USDA FoodData Central", "fdc_id": "172448"},
    {"id": "whey_protein", "name": "Whey Protein Isolate", "category": "Supplements", "serving_size_g": 30.0, "calories_per_100g": 370.0, "protein_per_100g": 80.0, "carbs_per_100g": 3.0, "fat_per_100g": 2.5, "source": "USDA FoodData Central", "fdc_id": "2115385"},
    {"id": "greek_yogurt", "name": "Greek Yogurt (Non-fat)", "category": "Dairy/Protein", "serving_size_g": 150.0, "calories_per_100g": 59.0, "protein_per_100g": 10.0, "carbs_per_100g": 3.6, "fat_per_100g": 0.4, "source": "USDA FoodData Central", "fdc_id": "170903"},
    {"id": "brown_rice", "name": "Cooked Brown Rice", "category": "Carbohydrates", "serving_size_g": 150.0, "calories_per_100g": 111.0, "protein_per_100g": 2.6, "carbs_per_100g": 23.0, "fat_per_100g": 0.9, "source": "USDA FoodData Central", "fdc_id": "169704"},
    {"id": "white_rice", "name": "Cooked White Rice", "category": "Carbohydrates", "serving_size_g": 150.0, "calories_per_100g": 130.0, "protein_per_100g": 2.7, "carbs_per_100g": 28.0, "fat_per_100g": 0.3, "source": "USDA FoodData Central", "fdc_id": "169756"},
    {"id": "oats_rolled", "name": "Rolled Oats (Raw)", "category": "Carbohydrates", "serving_size_g": 50.0, "calories_per_100g": 389.0, "protein_per_100g": 16.9, "carbs_per_100g": 66.3, "fat_per_100g": 6.9, "source": "USDA FoodData Central", "fdc_id": "169747"},
    {"id": "whole_wheat_bread", "name": "Whole Wheat Bread (1 slice)", "category": "Carbohydrates", "serving_size_g": 40.0, "calories_per_100g": 247.0, "protein_per_100g": 13.0, "carbs_per_100g": 41.0, "fat_per_100g": 3.4, "source": "USDA FoodData Central", "fdc_id": "172688"},
    {"id": "sweet_potato", "name": "Boiled Sweet Potato", "category": "Carbohydrates", "serving_size_g": 150.0, "calories_per_100g": 86.0, "protein_per_100g": 1.6, "carbs_per_100g": 20.1, "fat_per_100g": 0.1, "source": "USDA FoodData Central", "fdc_id": "168483"},
    {"id": "banana", "name": "Banana (Medium)", "category": "Fruit/Carbs", "serving_size_g": 118.0, "calories_per_100g": 89.0, "protein_per_100g": 1.1, "carbs_per_100g": 22.8, "fat_per_100g": 0.3, "source": "USDA FoodData Central", "fdc_id": "173944"},
    {"id": "apple", "name": "Apple", "category": "Fruit/Carbs", "serving_size_g": 150.0, "calories_per_100g": 52.0, "protein_per_100g": 0.3, "carbs_per_100g": 13.8, "fat_per_100g": 0.2, "source": "USDA FoodData Central", "fdc_id": "171688"},
    {"id": "peanut_butter", "name": "Natural Peanut Butter", "category": "Healthy Fats", "serving_size_g": 32.0, "calories_per_100g": 588.0, "protein_per_100g": 25.0, "carbs_per_100g": 20.0, "fat_per_100g": 50.0, "source": "USDA FoodData Central", "fdc_id": "2261427"},
    {"id": "almonds", "name": "Raw Almonds", "category": "Healthy Fats", "serving_size_g": 30.0, "calories_per_100g": 579.0, "protein_per_100g": 21.2, "carbs_per_100g": 21.6, "fat_per_100g": 49.9, "source": "USDA FoodData Central", "fdc_id": "170567"},
    {"id": "olive_oil", "name": "Extra Virgin Olive Oil", "category": "Healthy Fats", "serving_size_g": 15.0, "calories_per_100g": 884.0, "protein_per_100g": 0.0, "carbs_per_100g": 0.0, "fat_per_100g": 100.0, "source": "USDA FoodData Central", "fdc_id": "748608"},
    {"id": "broccoli", "name": "Steamed Broccoli", "category": "Vegetables", "serving_size_g": 100.0, "calories_per_100g": 34.0, "protein_per_100g": 2.8, "carbs_per_100g": 6.6, "fat_per_100g": 0.4, "source": "USDA FoodData Central", "fdc_id": "170379"},
    {"id": "spinach", "name": "Fresh / Cooked Spinach", "category": "Vegetables", "serving_size_g": 100.0, "calories_per_100g": 23.0, "protein_per_100g": 2.9, "carbs_per_100g": 3.6, "fat_per_100g": 0.4, "source": "USDA FoodData Central", "fdc_id": "170417"},
    {"id": "lentils_dal", "name": "Cooked Yellow / Brown Dal", "category": "Plant Protein", "serving_size_g": 150.0, "calories_per_100g": 116.0, "protein_per_100g": 9.0, "carbs_per_100g": 20.0, "fat_per_100g": 0.4, "source": "USDA FoodData Central", "fdc_id": "172421"},
    {"id": "chickpeas", "name": "Cooked Chickpeas (Garbanzo)", "category": "Plant Protein", "serving_size_g": 150.0, "calories_per_100g": 164.0, "protein_per_100g": 8.9, "carbs_per_100g": 27.4, "fat_per_100g": 2.6, "source": "USDA FoodData Central", "fdc_id": "173757"},
]


class NutritionService:
    """
    Core deterministic service for BMI, metabolic rate calculations,
    food logging, and nutritional daily aggregation.
    """

    @staticmethod
    def calculate_bmi(height_cm: float, weight_kg: float) -> Dict[str, Any]:
        """
        Calculates Body Mass Index (BMI) and healthy weight bounds.
        Formula: weight_kg / (height_m)^2
        """
        if height_cm < 50.0 or height_cm > 260.0:
            raise ValueError(f"Height must be between 50 and 260 cm. Received: {height_cm}")
        if weight_kg < 20.0 or weight_kg > 350.0:
            raise ValueError(f"Weight must be between 20 and 350 kg. Received: {weight_kg}")

        height_m = height_cm / 100.0
        bmi = round(weight_kg / (height_m * height_m), 1)

        # WHO Standard BMI categories
        if bmi < 18.5:
            category = "Underweight"
        elif bmi < 25.0:
            category = "Normal weight"
        elif bmi < 30.0:
            category = "Overweight"
        else:
            category = "Obese"

        # Healthy weight range (BMI 18.5 - 24.9)
        healthy_min = round(18.5 * (height_m * height_m), 1)
        healthy_max = round(24.9 * (height_m * height_m), 1)

        return {
            "bmi": bmi,
            "category": category,
            "healthy_weight_min_kg": healthy_min,
            "healthy_weight_max_kg": healthy_max,
        }

    @staticmethod
    def calculate_bmr(
        height_cm: float,
        weight_kg: float,
        age: int = 25,
        gender: str = "neutral",
    ) -> float:
        """
        Calculates Basal Metabolic Rate (BMR) using the Mifflin-St Jeor Equation.
        Men:   10 * weight(kg) + 6.25 * height(cm) - 5 * age + 5
        Women: 10 * weight(kg) + 6.25 * height(cm) - 5 * age - 161
        Neutral: Average of men and women offset (-78)
        """
        clean_gender = (gender or "neutral").strip().lower()
        if clean_gender in ("male", "man", "m"):
            offset = 5.0
        elif clean_gender in ("female", "woman", "f"):
            offset = -161.0
        else:
            offset = -78.0

        bmr = 10.0 * weight_kg + 6.25 * height_cm - 5.0 * age + offset
        return round(max(bmr, 800.0), 1)

    @staticmethod
    def calculate_tdee(bmr: float, activity_level: str = "moderate") -> float:
        """
        Calculates Total Daily Energy Expenditure (TDEE).
        Multipliers:
          - sedentary: 1.2
          - light: 1.375
          - moderate: 1.55
          - very_active: 1.725
          - extra_active: 1.9
        """
        multipliers = {
            "sedentary": 1.2,
            "light": 1.375,
            "moderate": 1.55,
            "very_active": 1.725,
            "extra_active": 1.9,
        }
        level = (activity_level or "moderate").strip().lower()
        mult = multipliers.get(level, 1.4)
        return round(bmr * mult, 1)

    @classmethod
    def calculate_nutrition_targets(
        cls,
        height_cm: float,
        weight_kg: float,
        fitness_goal: str = "maintenance",
        activity_level: str = "moderate",
        dietary_preference: str = "standard",
        age: int = 25,
        gender: str = "neutral",
    ) -> Dict[str, Any]:
        """
        Determines target daily calories, macronutrient distribution, and hydration.
        Applies safe caloric floors and goal-specific macronutrient adjustments.
        """
        bmi_data = cls.calculate_bmi(height_cm, weight_kg)
        bmr = cls.calculate_bmr(height_cm, weight_kg, age=age, gender=gender)
        tdee = cls.calculate_tdee(bmr, activity_level=activity_level)

        goal = (fitness_goal or "maintenance").strip().lower()
        pref = (dietary_preference or "standard").strip().lower()

        # 1. Target Calories based on Goal
        if goal in ("fat_loss", "weight_loss", "cutting"):
            # 20% deficit, safe floor 1200 kcal for female, 1500 for others
            min_floor = 1200.0 if gender.lower() in ("female", "f") else 1500.0
            calories_target = max(tdee * 0.80, min_floor)
            protein_per_kg = 2.0  # Preserve muscle in deficit
        elif goal in ("muscle_gain", "hypertrophy", "bulking"):
            # 10% surplus
            calories_target = tdee * 1.10
            protein_per_kg = 2.2
        elif goal in ("endurance", "athletic"):
            calories_target = tdee * 1.05
            protein_per_kg = 1.8
        else:
            # Maintenance / General fitness
            calories_target = tdee
            protein_per_kg = 1.6

        calories_target = round(calories_target, 0)

        # 2. Macronutrient breakdown
        if pref == "keto":
            # Keto: 70% Fat, 25% Protein, 5% Carbs
            protein_g = round((calories_target * 0.25) / 4.0, 1)
            fat_g = round((calories_target * 0.70) / 9.0, 1)
            carbs_g = round((calories_target * 0.05) / 4.0, 1)
        elif pref == "high_protein":
            # High Protein: 35% Protein, 40% Carbs, 25% Fat
            protein_g = round((calories_target * 0.35) / 4.0, 1)
            fat_g = round((calories_target * 0.25) / 9.0, 1)
            carbs_g = round((calories_target * 0.40) / 4.0, 1)
        else:
            # Standard balanced distribution:
            # Protein by bodyweight (capped at 35% of calories)
            target_protein_cals = min(protein_per_kg * weight_kg * 4.0, calories_target * 0.35)
            protein_g = round(target_protein_cals / 4.0, 1)

            # Fat at 25% of calories (essential hormones & cell integrity)
            fat_g = round((calories_target * 0.25) / 9.0, 1)

            # Carbs fills remaining calories
            remaining_cals = max(0.0, calories_target - (protein_g * 4.0 + fat_g * 9.0))
            carbs_g = round(remaining_cals / 4.0, 1)

        # Hydration rule of thumb: ~35ml per kg bodyweight
        water_liters = round(max(2.0, min(5.0, (weight_kg * 0.035))), 1)

        return {
            "bmi": bmi_data["bmi"],
            "category": bmi_data["category"],
            "healthy_weight_min_kg": bmi_data["healthy_weight_min_kg"],
            "healthy_weight_max_kg": bmi_data["healthy_weight_max_kg"],
            "bmr": bmr,
            "tdee": tdee,
            "recommended_calories": calories_target,
            "recommended_protein_g": protein_g,
            "recommended_carbs_g": carbs_g,
            "recommended_fat_g": fat_g,
            "water_liters": water_liters,
        }

    @staticmethod
    def get_food_catalogue(search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns built-in verified food items, optionally filtered by keyword."""
        if not search:
            return STANDARD_FOOD_CATALOGUE
        q = search.strip().lower()
        return [
            f for f in STANDARD_FOOD_CATALOGUE
            if q in f["name"].lower() or q in f["category"].lower()
        ]

    @classmethod
    def get_or_create_user_target(cls, db: Session, user_id: int) -> NutritionTarget:
        """
        Retrieves active NutritionTarget for user, or computes and creates
        one automatically from their Profile.
        """
        target = db.execute(
            select(NutritionTarget).where(NutritionTarget.user_id == user_id)
        ).scalars().first()

        if target:
            return target

        # Retrieve user profile for baseline metrics
        profile = db.execute(
            select(Profile).where(Profile.user_id == user_id)
        ).scalars().first()

        h = profile.height_cm if (profile and profile.height_cm) else 175.0
        w = profile.weight_kg if (profile and profile.weight_kg) else 70.0
        goal = profile.fitness_goal if (profile and profile.fitness_goal) else "maintenance"
        act = profile.activity_level if (profile and profile.activity_level) else "moderate"
        pref = profile.dietary_preference if (profile and profile.dietary_preference) else "standard"
        gender = profile.gender if (profile and profile.gender) else "neutral"

        calc = cls.calculate_nutrition_targets(
            height_cm=h,
            weight_kg=w,
            fitness_goal=goal,
            activity_level=act,
            dietary_preference=pref,
            gender=gender,
        )

        new_target = NutritionTarget(
            user_id=user_id,
            calories_target=calc["recommended_calories"],
            protein_grams=calc["recommended_protein_g"],
            carbs_grams=calc["recommended_carbs_g"],
            fat_grams=calc["recommended_fat_g"],
            water_liters=calc["water_liters"],
            dietary_preference=pref,
            meals_per_day=3,
        )
        db.add(new_target)
        db.commit()
        db.refresh(new_target)
        return new_target

    @classmethod
    def update_user_target(cls, db: Session, user_id: int, update_data: Dict[str, Any]) -> NutritionTarget:
        """Updates user's customized daily nutrition targets."""
        target = cls.get_or_create_user_target(db, user_id)

        for field, value in update_data.items():
            if value is not None and hasattr(target, field):
                setattr(target, field, value)

        target.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(target)
        return target

    @staticmethod
    def log_food(db: Session, user_id: int, log_data: Dict[str, Any]) -> NutritionLog:
        """Creates and persists a food entry for the authenticated user."""
        quantity = float(log_data["quantity"])
        if quantity <= 0 or quantity > 5000:
            raise ValueError(f"Quantity must be positive and <= 5000, got {quantity}")
        calories = float(log_data["calories"])
        if calories < 0 or calories > 5000:
            raise ValueError(f"Calories must be between 0 and 5000, got {calories}")
        protein = float(log_data.get("protein", 0.0))
        if protein < 0 or protein > 500:
            raise ValueError(f"Protein must be between 0 and 500g, got {protein}")
        carbs = float(log_data.get("carbs", 0.0))
        if carbs < 0 or carbs > 500:
            raise ValueError(f"Carbs must be between 0 and 500g, got {carbs}")
        fat = float(log_data.get("fat", 0.0))
        if fat < 0 or fat > 500:
            raise ValueError(f"Fat must be between 0 and 500g, got {fat}")

        log_date = log_data.get("log_date") or date.today()
        new_log = NutritionLog(
            user_id=user_id,
            log_date=log_date,
            meal_type=log_data.get("meal_type", "lunch").lower(),
            food_name=log_data["food_name"],
            quantity=quantity,
            unit=log_data.get("unit", "g"),
            calories=calories,
            protein=protein,
            carbs=carbs,
            fat=fat,
        )
        db.add(new_log)
        db.commit()
        db.refresh(new_log)
        return new_log

    @staticmethod
    def get_daily_logs(db: Session, user_id: int, target_date: Optional[date] = None) -> List[NutritionLog]:
        """Retrieves all food logs for a user on a given date (defaults to today)."""
        d = target_date or date.today()
        logs = db.execute(
            select(NutritionLog)
            .where(NutritionLog.user_id == user_id, NutritionLog.log_date == d)
            .order_by(NutritionLog.created_at.asc())
        ).scalars().all()
        return list(logs)

    @staticmethod
    def delete_food_log(db: Session, user_id: int, log_id: int) -> bool:
        """Safely deletes a food log entry with strict ownership verification."""
        log = db.execute(
            select(NutritionLog).where(NutritionLog.id == log_id, NutritionLog.user_id == user_id)
        ).scalars().first()
        if not log:
            return False
        db.delete(log)
        db.commit()
        return True

    @classmethod
    def get_daily_summary(cls, db: Session, user_id: int, target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Aggregates food logs for the date, compares against NutritionTarget,
        and computes progress percentages and remaining macros.
        """
        d = target_date or date.today()
        logs = cls.get_daily_logs(db, user_id, d)
        target = cls.get_or_create_user_target(db, user_id)

        tot_cals = round(sum(log.calories for log in logs), 1)
        tot_protein = round(sum(log.protein for log in logs), 1)
        tot_carbs = round(sum(log.carbs for log in logs), 1)
        tot_fat = round(sum(log.fat for log in logs), 1)

        rem_cals = round(target.calories_target - tot_cals, 1)

        pct_cals = round((tot_cals / target.calories_target * 100.0) if target.calories_target > 0 else 0.0, 1)
        pct_protein = round((tot_protein / target.protein_grams * 100.0) if target.protein_grams > 0 else 0.0, 1)
        pct_carbs = round((tot_carbs / target.carbs_grams * 100.0) if target.carbs_grams > 0 else 0.0, 1)
        pct_fat = round((tot_fat / target.fat_grams * 100.0) if target.fat_grams > 0 else 0.0, 1)

        # Status: on_track (within 10%), under_target, or over_target
        if pct_cals > 110.0:
            status = "over_target"
        elif pct_cals < 85.0:
            status = "under_target"
        else:
            status = "on_track"

        # Organize logs by meal_type
        breakdown: Dict[str, List[Any]] = {
            "breakfast": [],
            "lunch": [],
            "dinner": [],
            "snack": [],
        }
        for log in logs:
            mt = log.meal_type.lower()
            if mt not in breakdown:
                breakdown[mt] = []
            breakdown[mt].append({
                "id": log.id,
                "user_id": log.user_id,
                "log_date": log.log_date.isoformat(),
                "meal_type": log.meal_type,
                "food_name": log.food_name,
                "quantity": log.quantity,
                "unit": log.unit,
                "calories": log.calories,
                "protein": log.protein,
                "carbs": log.carbs,
                "fat": log.fat,
                "created_at": log.created_at,
            })

        return {
            "date": d.isoformat(),
            "total_calories": tot_cals,
            "total_protein": tot_protein,
            "total_carbs": tot_carbs,
            "total_fat": tot_fat,
            "target_calories": target.calories_target,
            "target_protein": target.protein_grams,
            "target_carbs": target.carbs_grams,
            "target_fat": target.fat_grams,
            "water_liters": target.water_liters,
            "remaining_calories": rem_cals,
            "calories_percentage": pct_cals,
            "protein_percentage": pct_protein,
            "carbs_percentage": pct_carbs,
            "fat_percentage": pct_fat,
            "status": status,
            "meal_breakdown": breakdown,
        }

    @classmethod
    def get_weekly_summary(
        cls,
        db: Session,
        user_id: int,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        Aggregates food logs for the authenticated user over a rolling window (default 7 days).
        Calculates weekly totals, daily averages, compliance against NutritionTarget,
        and daily macro history points.
        """
        if days < 1 or days > 365:
            days = 7

        today = date.today()
        start_date = today - timedelta(days=days - 1)

        target = cls.get_or_create_user_target(db, user_id)

        logs = db.execute(
            select(NutritionLog)
            .where(
                NutritionLog.user_id == user_id,
                NutritionLog.log_date >= start_date,
                NutritionLog.log_date <= today,
            )
            .order_by(NutritionLog.log_date.asc(), NutritionLog.created_at.asc())
        ).scalars().all()

        # Group logs by date
        logs_by_date: Dict[date, List[NutritionLog]] = {}
        for l in logs:
            logs_by_date.setdefault(l.log_date, []).append(l)

        daily_history: List[Dict[str, Any]] = []
        curr = start_date
        total_cals = 0.0
        total_protein = 0.0
        total_carbs = 0.0
        total_fat = 0.0

        days_logged = len(logs_by_date)

        while curr <= today:
            day_logs = logs_by_date.get(curr, [])
            day_cals = round(sum(l.calories for l in day_logs), 1)
            day_prot = round(sum(l.protein for l in day_logs), 1)
            day_carbs = round(sum(l.carbs for l in day_logs), 1)
            day_fat = round(sum(l.fat for l in day_logs), 1)

            total_cals += day_cals
            total_protein += day_prot
            total_carbs += day_carbs
            total_fat += day_fat

            daily_history.append({
                "date": curr.isoformat(),
                "calories": day_cals,
                "protein": day_prot,
                "carbs": day_carbs,
                "fat": day_fat,
                "log_count": len(day_logs),
            })
            curr += timedelta(days=1)

        total_cals = round(total_cals, 1)
        total_protein = round(total_protein, 1)
        total_carbs = round(total_carbs, 1)
        total_fat = round(total_fat, 1)

        divisor = float(days)
        avg_cals = round(total_cals / divisor, 1)
        avg_protein = round(total_protein / divisor, 1)
        avg_carbs = round(total_carbs / divisor, 1)
        avg_fat = round(total_fat / divisor, 1)

        compliance_pct = round(
            (avg_cals / target.calories_target * 100.0) if target.calories_target > 0 else 0.0, 1
        )

        if compliance_pct > 110.0:
            compliance_status = "over_target"
        elif compliance_pct < 85.0:
            compliance_status = "under_target"
        else:
            compliance_status = "on_track"

        return {
            "reporting_period": {
                "start_date": start_date.isoformat(),
                "end_date": today.isoformat(),
                "days": days,
            },
            "total_calories": total_cals,
            "total_protein": total_protein,
            "total_carbs": total_carbs,
            "total_fat": total_fat,
            "daily_average_calories": avg_cals,
            "daily_average_protein": avg_protein,
            "daily_average_carbs": avg_carbs,
            "daily_average_fat": avg_fat,
            "target_calories": target.calories_target,
            "target_protein": target.protein_grams,
            "target_carbs": target.carbs_grams,
            "target_fat": target.fat_grams,
            "calorie_compliance_percentage": compliance_pct,
            "days_logged": days_logged,
            "compliance_status": compliance_status,
            "daily_history": daily_history,
        }

