from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from routers.auth import get_current_user, get_db
from models.user import User
from schemas.analytics import (
    AnalyticsOverviewResponse,
    WorkoutAnalyticsResponse,
    NutritionAnalyticsResponse,
    HabitAnalyticsResponse,
    IoTAnalyticsResponse,
)
from services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics & Dashboards"])


@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_analytics_overview(
    time_window: str = Query("7_days", description="Time window: 7_days, 14_days, 30_days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns multi-domain fitness analytics overview for authenticated user.
    """
    try:
        data = AnalyticsService.get_overview(db, current_user.id, time_window)
        return data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.get("/workouts", response_model=WorkoutAnalyticsResponse)
def get_workout_analytics(
    time_window: str = Query("7_days", description="Time window: 7_days, 14_days, 30_days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns detailed workout performance analytics and trends for authenticated user.
    """
    try:
        data = AnalyticsService.get_workout_analytics(db, current_user.id, time_window)
        return data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.get("/nutrition", response_model=NutritionAnalyticsResponse)
def get_nutrition_analytics(
    time_window: str = Query("7_days", description="Time window: 7_days, 14_days, 30_days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns detailed nutrition intake and target compliance analytics for authenticated user.
    """
    try:
        data = AnalyticsService.get_nutrition_analytics(db, current_user.id, time_window)
        return data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.get("/habits", response_model=HabitAnalyticsResponse)
def get_habit_analytics(
    time_window: str = Query("7_days", description="Time window: 7_days, 14_days, 30_days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns behavioral habit tracking, consistency, and skip risk analytics for authenticated user.
    """
    try:
        data = AnalyticsService.get_habit_analytics(db, current_user.id, time_window)
        return data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.get("/iot", response_model=IoTAnalyticsResponse)
def get_iot_analytics(
    time_window: str = Query("7_days", description="Time window: 7_days, 14_days, 30_days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns Smart Gym IoT telemetry and equipment utilization analytics for authenticated user.
    """
    try:
        data = AnalyticsService.get_iot_analytics(db, current_user.id, time_window)
        return data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
