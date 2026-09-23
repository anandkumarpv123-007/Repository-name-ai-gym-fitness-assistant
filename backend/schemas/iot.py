from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IoTDeviceCreate(BaseModel):
    device_name: str = Field(..., min_length=2, max_length=150, description="Device name")
    equipment_category: str = Field(..., description="Equipment category (e.g., smart_rack, cable_station, treadmill)")
    gym_id: Optional[int] = Field(1, description="Associated gym facility ID (defaults to 1 for home/personal smart devices)")
    device_uid: Optional[str] = Field(None, description="Optional custom device UID")
    mac_address: Optional[str] = None
    firmware_version: Optional[str] = "v2.1.0"


class IoTDeviceResponse(BaseModel):
    id: int
    user_id: int
    gym_id: Optional[int] = 1
    device_uid: str
    device_name: str
    equipment_category: str
    status: str
    is_simulated: bool
    current_resistance_kg: float
    target_resistance_kg: float
    mac_address: Optional[str] = None
    firmware_version: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IoTTelemetryCreate(BaseModel):
    exercise_type: str = Field(..., min_length=2, max_length=100)
    resistance_kg: float = Field(..., ge=0.0, le=500.0, description="Resistance load in kg [0, 500]")
    repetition_count: int = Field(..., ge=0, le=200, description="Repetition count [0, 200]")
    session_duration_seconds: int = Field(..., ge=0, le=86400)
    intensity_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    heart_rate_bpm: Optional[int] = Field(None, ge=30, le=250, description="Heart rate bpm [30, 250]")
    operational_state: Optional[str] = "active"


class IoTTelemetryResponse(BaseModel):
    id: int
    device_id: int
    user_id: int
    exercise_type: str
    resistance_kg: float
    repetition_count: int
    session_duration_seconds: int
    intensity_score: float
    heart_rate_bpm: Optional[int] = None
    operational_state: str
    timestamp: datetime

    class Config:
        from_attributes = True


class IoTCommandRequest(BaseModel):
    command_type: str = Field(..., description="Command (set_resistance, increase_resistance, decrease_resistance, emergency_stop)")
    target_resistance_kg: Optional[float] = Field(None, ge=0.0, le=300.0, description="Target resistance load in kg [0, 300]")
    step_increment_kg: Optional[float] = Field(2.5, ge=0.5, le=50.0)


class IoTCommandResponse(BaseModel):
    id: int
    device_id: int
    user_id: int
    command_type: str
    payload: Dict[str, Any]
    status: str
    current_resistance_kg: float
    target_resistance_kg: float
    created_at: datetime


class SmartAssistantRecommendationItem(BaseModel):
    recommendation_type: str  # rest_interval, progressive_overload, fatigue_alert, equipment_status
    title: str
    message: str
    action_suggested: Optional[str] = None
    target_device_uid: Optional[str] = None
    suggested_value: Optional[float] = None
    confidence_score: float = 0.95


class SmartAssistantRecommendationResponse(BaseModel):
    user_id: int
    total_active_devices: int
    recommendations: List[SmartAssistantRecommendationItem]
    timestamp: datetime
