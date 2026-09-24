from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnalyticsOverviewResponse(BaseModel):
    time_window: str = Field(..., description="Selected window: 7_days, 14_days, or 30_days")
    user_profile: Dict[str, Any]
    workout_summary: Dict[str, Any]
    nutrition_summary: Dict[str, Any]
    habit_summary: Dict[str, Any]
    iot_summary: Dict[str, Any]
    cross_domain_insights: List[Dict[str, str]]


class WorkoutAnalyticsResponse(BaseModel):
    time_window: str
    total_workouts: int
    total_duration_minutes: int
    total_reps: int
    avg_performance_score: Optional[float] = None
    performance_trend: str
    component_score_averages: Dict[str, Optional[float]]
    top_form_violations: List[Dict[str, Any]]
    session_history: List[Dict[str, Any]]
    has_data: bool


class NutritionAnalyticsResponse(BaseModel):
    time_window: str
    target: Dict[str, Any]
    average_daily_intake: Dict[str, Optional[float]]
    compliance: Dict[str, Optional[float]]
    daily_trends: List[Dict[str, Any]]
    has_data: bool


class HabitAnalyticsResponse(BaseModel):
    time_window: str
    current_status: Dict[str, Any]
    consistency: Dict[str, Any]
    daily_habit_history: List[Dict[str, Any]]
    has_data: bool


class IoTAnalyticsResponse(BaseModel):
    time_window: str
    device_counts: Dict[str, int]
    telemetry_averages: Dict[str, Optional[float]]
    device_breakdown: List[Dict[str, Any]]
    has_data: bool
