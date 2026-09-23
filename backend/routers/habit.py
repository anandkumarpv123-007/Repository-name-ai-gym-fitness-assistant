from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from routers.auth import get_current_user, get_db
from models.user import User
from schemas.habit import HabitStatusResponse, HabitHistoryResponse
from services.habit_predictor_service import HabitPredictorService


router = APIRouter(prefix="/habit", tags=["Fitness Habit Tracker & Behavioral AI"])


@router.get("/status", response_model=HabitStatusResponse, status_code=status.HTTP_200_OK)
def get_habit_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Analyzes user workout behavior to predict skip probability,
    extract top behavioral factor signals, generate adaptive nudges,
    and provide optimal schedule recommendations.
    Enforces cold-start handling for users with < 3 completed sessions.
    """
    habit_status = HabitPredictorService.analyze_user_habit(db, current_user.id)
    return habit_status


@router.get("/history", response_model=HabitHistoryResponse, status_code=status.HTTP_200_OK)
def get_habit_history(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of historical snapshot predictions to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves historical habit prediction snapshots for the authenticated user.
    """
    history = HabitPredictorService.get_user_history(db, current_user.id, limit=limit)
    return history
