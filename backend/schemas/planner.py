from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GymItemResponse(BaseModel):
    """Structured response for gym catalogue items."""
    id: int
    name: str
    address: str
    city: str
    price_category: str
    rating: float
    opening_hours: str
    facilities: List[str]
    equipment: List[str]
    supported_workout_types: List[str]
    is_verified_sample: bool
    created_at: datetime

    class Config:
        from_attributes = True


class GymRecommendationItem(BaseModel):
    """Recommendation snapshot for a specific gym with suitability scoring."""
    gym: GymItemResponse
    suitability_score: int = Field(..., description="Calculated suitability score [0, 100%]")
    match_category: str = Field(..., description="High Suitability Match, Moderate Suitability Match, Compatible")
    match_reasons: List[str] = Field(..., description="Observational match explanations explaining score")


class GymRecommendationResponse(BaseModel):
    """List of ranked personalized gym recommendations for current user."""
    user_id: int
    user_goal: str
    recommendations: List[GymRecommendationItem]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ExerciseItem(BaseModel):
    """Single exercise prescription within a daily workout plan item."""
    name: str
    sets: int
    reps_or_duration: str
    target_muscle: str
    technique_cue: Optional[str] = None


class WorkoutPlanItemResponse(BaseModel):
    """Single day schedule item in a weekly workout plan."""
    id: int
    day_of_week: str
    day_title: str
    is_rest_day: bool
    target_muscle_groups: Optional[str]
    exercises: List[ExerciseItem]
    warmup_notes: Optional[str]

    class Config:
        from_attributes = True


class WorkoutPlanGenerateRequest(BaseModel):
    """Request payload to trigger custom workout plan generation."""
    fitness_goal: Optional[str] = Field(None, description="Override fitness goal ('hypertrophy', 'strength', 'weight_loss', 'endurance', 'maintenance')")
    preferred_days_per_week: Optional[int] = Field(None, ge=2, le=7, description="Override target days per week")


class WorkoutPlanResponse(BaseModel):
    """Complete weekly workout plan returned by backend."""
    id: int
    user_id: int
    plan_name: str
    fitness_goal: str
    target_split: str
    days_per_week: int
    habit_adapted: bool
    performance_adapted: bool
    adaptation_notes: Optional[str]
    items: List[WorkoutPlanItemResponse]
    created_at: datetime

    class Config:
        from_attributes = True


class WorkoutPlanHistoryResponse(BaseModel):
    """List of historical generated workout plans for current user."""
    user_id: int
    plans: List[WorkoutPlanResponse]
