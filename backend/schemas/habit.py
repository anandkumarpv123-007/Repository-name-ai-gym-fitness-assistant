from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BehavioralFeatureSummary(BaseModel):
    """Extracted behavioral features for user."""
    days_since_last_workout: int = Field(..., description="Days elapsed since most recent completed session")
    workout_frequency_7d: int = Field(..., description="Count of completed sessions in past 7 days")
    workout_frequency_30d: int = Field(..., description="Count of completed sessions in past 30 days")
    avg_weekly_workouts: float = Field(..., description="Average weekly sessions across overall user history")
    consistency_score: float = Field(..., description="Ratio of active weeks to total registered weeks [0.0, 1.0]")
    preferred_weekday_ratio: float = Field(..., description="Proportion of sessions occurring on user's top weekday")
    max_gap_days_30d: int = Field(..., description="Longest consecutive gap in days between sessions in past 30 days")
    form_score_trend_delta: float = Field(..., description="Change in average form score between recent and prior sessions")


class BehavioralFactorItem(BaseModel):
    """Single non-causal behavioral signal associated with skip risk."""
    feature_name: str
    description: str
    impact_level: str  # "high", "moderate", "low"
    signal_direction: str  # "increases_risk", "decreases_risk"


class HabitStatusResponse(BaseModel):
    """Complete habit intelligence snapshot returned by backend."""
    user_id: int
    status: str  # "active_prediction", "insufficient_data"
    total_sessions_logged: int
    skip_probability: Optional[float] = Field(None, description="Predicted probability [0.00, 1.00] of skipping next expected window")
    risk_level: str  # "low", "moderate", "high", "insufficient_data"
    risk_explanation: str
    features: BehavioralFeatureSummary
    behavioral_factors: List[BehavioralFactorItem]
    adaptive_nudge: str
    recommended_schedule: str
    model_info: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HabitPredictionItem(BaseModel):
    """Historical habit snapshot record."""
    id: int
    user_id: int
    prediction_date: datetime
    skip_probability: Optional[float]
    risk_level: str
    primary_factor: Optional[str]
    nudge_text: Optional[str]
    recommended_schedule: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class HabitHistoryResponse(BaseModel):
    """List of historical habit predictions for current user."""
    user_id: int
    predictions: List[HabitPredictionItem]
