from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from routers.auth import get_current_user, get_db
from models.user import User
from schemas.planner import (
    GymItemResponse,
    GymRecommendationResponse,
    WorkoutPlanGenerateRequest,
    WorkoutPlanResponse,
    WorkoutPlanHistoryResponse,
)
from services.gym_recommender_service import GymRecommenderService
from services.workout_planner_service import WorkoutPlannerService


router = APIRouter(prefix="", tags=["Gym Recommender & Workout Planner"])


# ----------------------------------------------------------------------
# 1. Gym Catalogue & Personalized Recommendations
# ----------------------------------------------------------------------

@router.get("/gyms", response_model=List[GymItemResponse], status_code=status.HTTP_200_OK)
def get_gyms_catalogue(
    search: Optional[str] = Query(None, description="Search gyms by name, location, or equipment"),
    db: Session = Depends(get_db),
):
    """
    Retrieves synthetic/sample gym catalogue entries with optional search filtering.
    Publicly accessible endpoint.
    """
    gyms = GymRecommenderService.get_all_gyms(db, search=search)
    return gyms


@router.get("/gyms/recommendations", response_model=GymRecommendationResponse, status_code=status.HTTP_200_OK)
def get_gym_recommendations(
    limit: int = Query(5, ge=1, le=20, description="Maximum number of recommendations to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generates personalized ranked gym recommendations for the authenticated user,
    computing transparent suitability scores [0, 100%] and match explanations based on fitness goals.
    """
    recommendations = GymRecommenderService.recommend_gyms_for_user(db, current_user.id, limit=limit)
    return recommendations


# ----------------------------------------------------------------------
# 2. Personalized Weekly Workout Planner
# ----------------------------------------------------------------------

@router.post("/planner/generate", response_model=WorkoutPlanResponse, status_code=status.HTTP_201_CREATED)
def generate_workout_plan(
    payload: Optional[WorkoutPlanGenerateRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generates and persists a personalized 7-day weekly workout plan tailored to the user's
    fitness goal, adapting for Phase 3 form performance warnings and Phase 6 habit skip risks.
    """
    req_payload = payload or WorkoutPlanGenerateRequest()
    plan = WorkoutPlannerService.generate_workout_plan(
        db,
        user_id=current_user.id,
        custom_goal=req_payload.fitness_goal,
        custom_days=req_payload.preferred_days_per_week,
    )
    return plan


@router.get("/planner/latest", response_model=WorkoutPlanResponse, status_code=status.HTTP_200_OK)
def get_latest_workout_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves the authenticated user's most recently generated workout plan.
    Auto-generates an initial plan if no active plan exists.
    """
    plan = WorkoutPlannerService.get_latest_plan(db, current_user.id)
    if not plan:
        # Generate initial plan on the fly if none exists
        plan = WorkoutPlannerService.generate_workout_plan(db, current_user.id)
    return plan


@router.get("/planner/history", response_model=WorkoutPlanHistoryResponse, status_code=status.HTTP_200_OK)
def get_workout_plan_history(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of historical plans to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves historical generated workout plans for the authenticated user.
    """
    history = WorkoutPlannerService.get_plan_history(db, current_user.id, limit=limit)
    return history
