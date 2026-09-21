from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class ExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str
    target_muscles: Optional[str] = None
    instructions: Optional[str] = None


class WorkoutStartRequest(BaseModel):
    exercise_id: Optional[int] = None
    notes: Optional[str] = None


class WorkoutStartResponse(BaseModel):
    session_id: int
    started_at: datetime
    message: str


class RepMetricItem(BaseModel):
    rep_number: int
    min_knee_angle: Optional[float] = None
    max_torso_lean: Optional[float] = None
    duration_seconds: Optional[float] = None
    form_status: Optional[str] = None
    violations: Optional[List[str]] = None
    metrics_json: Optional[Dict] = None


class WorkoutCompleteRequest(BaseModel):
    exercise_id: int
    sets: int = 1
    reps: int
    calories: Optional[float] = None
    performance_score: Optional[float] = None
    notes: Optional[str] = None
    rep_metrics: Optional[List[RepMetricItem]] = None


class WorkoutCompleteResponse(BaseModel):
    session_id: int
    reps: int
    performance_score: Optional[float]
    duration_seconds: Optional[float]
    message: str


class WorkoutHistoryItem(BaseModel):
    session_id: int
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    exercise_name: str
    sets: int
    reps: int
    performance_score: Optional[float] = None
    calories: Optional[float] = None


class PoseMetricDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rep_number: int
    min_knee_angle: Optional[float]
    max_torso_lean: Optional[float]
    duration_seconds: Optional[float]
    form_status: Optional[str]
    violations: Optional[str]


class WorkoutDetailResponse(BaseModel):
    session_id: int
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: Optional[float]
    exercise_name: str
    sets: int
    reps: int
    performance_score: Optional[float]
    calories: Optional[float]
    notes: Optional[str]
    pose_metrics: List[PoseMetricDetail]


class PerformanceSummaryResponse(BaseModel):
    total_sessions: int
    total_reps: int
    average_score: Optional[float]
    score_trend: str  # "IMPROVING", "STABLE", "DECLINING", "NEW"
    score_delta: Optional[float]  # delta between last session and previous average
    strongest_area: str
    recurring_issue: str
    next_week_focus: str
    recent_sessions: List[Dict]
