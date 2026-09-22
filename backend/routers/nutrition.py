from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from routers.auth import get_current_user, get_db
from models.profile import Profile
from models.user import User
from schemas.nutrition import (
    BMICalculateRequest,
    BMIResponse,
    DailyNutritionSummaryResponse,
    DietPlanCreateRequest,
    DietPlanResponse,
    FoodCatalogueItem,
    FoodLogCreateRequest,
    FoodLogResponse,
    NutritionTargetResponse,
    NutritionTargetUpdateRequest,
    WeeklyNutritionSummaryResponse,
)
from services.dietician_service import DieticianService
from services.nutrition_service import NutritionService


router = APIRouter(prefix="/diet", tags=["Nutrition & AI Dietician"])


# ----------------------------------------------------------------------
# 1. BMI & Metabolic Baseline Calculations
# ----------------------------------------------------------------------

@router.get("/bmi", response_model=BMIResponse)
def get_user_bmi(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Calculates BMI, BMR, TDEE, and recommended daily calorie/macro distribution
    using the authenticated user's profile.
    """
    profile = current_user.profile
    if not profile or not profile.height_cm or not profile.weight_kg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User profile must have valid height and weight set. Update your profile first.",
        )

    try:
        data = NutritionService.calculate_nutrition_targets(
            height_cm=profile.height_cm,
            weight_kg=profile.weight_kg,
            fitness_goal=profile.fitness_goal or "maintenance",
            activity_level=profile.activity_level or "moderate",
            dietary_preference=profile.dietary_preference or "standard",
            gender=profile.gender or "neutral",
        )
        return BMIResponse(
            height_cm=profile.height_cm,
            weight_kg=profile.weight_kg,
            **data,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/bmi", response_model=BMIResponse)
def calculate_custom_bmi(
    payload: BMICalculateRequest,
):
    """
    Calculates BMI, BMR, TDEE, and recommended targets from custom body metrics.
    Publicly accessible calculation endpoint.
    """
    try:
        data = NutritionService.calculate_nutrition_targets(
            height_cm=payload.height_cm,
            weight_kg=payload.weight_kg,
            fitness_goal=payload.fitness_goal or "maintenance",
            activity_level=payload.activity_level or "moderate",
            dietary_preference=payload.dietary_preference or "standard",
            age=payload.age or 25,
            gender=payload.gender or "neutral",
        )
        return BMIResponse(
            height_cm=payload.height_cm,
            weight_kg=payload.weight_kg,
            **data,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


# ----------------------------------------------------------------------
# 2. Nutrition Targets (Persistence & Customization)
# ----------------------------------------------------------------------

@router.get("/target", response_model=NutritionTargetResponse)
def get_nutrition_target(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves the current active daily nutrition target for the authenticated user.
    Auto-computes baseline target from user profile if not previously saved.
    """
    target = NutritionService.get_or_create_user_target(db, current_user.id)
    return target


@router.put("/target", response_model=NutritionTargetResponse)
def update_nutrition_target(
    payload: NutritionTargetUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates user daily caloric and macronutrient targets."""
    target = NutritionService.update_user_target(
        db,
        current_user.id,
        payload.model_dump(exclude_unset=True),
    )
    return target


# ----------------------------------------------------------------------
# 3. Verified Food Catalogue & Search
# ----------------------------------------------------------------------

@router.get("/foods", response_model=List[FoodCatalogueItem])
def get_foods_catalogue(
    search: Optional[str] = Query(None, description="Search by name or category"),
):
    """Returns verified common fitness foods with accurate calories and macronutrients per 100g."""
    foods = NutritionService.get_food_catalogue(search)
    return foods


# ----------------------------------------------------------------------
# 4. Food Logging & Tracking
# ----------------------------------------------------------------------

@router.post("/log", response_model=FoodLogResponse, status_code=status.HTTP_201_CREATED)
def create_food_log(
    payload: FoodLogCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Logs a food item entry with quantity, calories, and macronutrients."""
    try:
        log = NutritionService.log_food(
            db,
            user_id=current_user.id,
            log_data=payload.model_dump(),
        )
        return FoodLogResponse(
            id=log.id,
            user_id=log.user_id,
            log_date=log.log_date.isoformat(),
            meal_type=log.meal_type,
            food_name=log.food_name,
            quantity=log.quantity,
            unit=log.unit,
            calories=log.calories,
            protein=log.protein,
            carbs=log.carbs,
            fat=log.fat,
            created_at=log.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/logs", response_model=List[FoodLogResponse])
def get_food_logs(
    date_query: Optional[date] = Query(None, alias="date", description="Date YYYY-MM-DD (defaults to today)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves all food log entries for the authenticated user on a given date."""
    logs = NutritionService.get_daily_logs(db, current_user.id, target_date=date_query)
    return [
        FoodLogResponse(
            id=l.id,
            user_id=l.user_id,
            log_date=l.log_date.isoformat(),
            meal_type=l.meal_type,
            food_name=l.food_name,
            quantity=l.quantity,
            unit=l.unit,
            calories=l.calories,
            protein=l.protein,
            carbs=l.carbs,
            fat=l.fat,
            created_at=l.created_at,
        )
        for l in logs
    ]


@router.delete("/log/{log_id}", status_code=status.HTTP_200_OK)
def delete_food_log(
    log_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deletes a food log entry with strict ownership verification."""
    success = NutritionService.delete_food_log(db, current_user.id, log_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Food log entry not found or unauthorized.",
        )
    return {"message": f"Food log entry {log_id} deleted successfully."}


@router.get("/summary", response_model=DailyNutritionSummaryResponse)
def get_daily_nutrition_summary(
    date_query: Optional[date] = Query(None, alias="date", description="Date YYYY-MM-DD (defaults to today)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Computes daily aggregated caloric and macronutrient intake compared against user targets.
    Returns percentages, remaining budget, and breakdown per meal type.
    """
    summary = NutritionService.get_daily_summary(db, current_user.id, target_date=date_query)
    return summary


@router.get("/weekly", response_model=WeeklyNutritionSummaryResponse)
def get_weekly_nutrition_summary(
    days: int = Query(7, ge=1, le=365, description="Rolling window in days (default 7)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Longitudinal weekly nutrition intelligence aggregating caloric/macronutrient
    intake across a rolling window, computing daily averages, compliance %, and day-by-day points.
    """
    summary = NutritionService.get_weekly_summary(db, current_user.id, days=days)
    return summary


# ----------------------------------------------------------------------
# 5. AI Dietician & Grocery Planning
# ----------------------------------------------------------------------

@router.post("/plan", response_model=DietPlanResponse, status_code=status.HTTP_201_CREATED)
def generate_diet_plan(
    payload: DietPlanCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generates a personalized daily meal plan and categorized grocery list using
    deterministic nutritional targets combined with LLM or expert rule-based meal composition.
    """
    plan = DieticianService.generate_diet_plan(
        db,
        user_id=current_user.id,
        dietary_preference=payload.dietary_preference,
        allergies_restrictions=payload.allergies_restrictions,
        meals_per_day=payload.meals_per_day,
        custom_calories=payload.target_calories,
    )
    return plan


@router.get("/plan/latest", response_model=DietPlanResponse)
def get_latest_diet_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieves the user's most recent generated diet plan and grocery list."""
    plan = DieticianService.get_latest_plan(db, current_user.id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No diet plan found for this user. Generate one first using POST /diet/plan.",
        )
    return plan
