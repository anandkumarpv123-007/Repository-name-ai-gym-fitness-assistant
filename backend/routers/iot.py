from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from routers.auth import get_current_user, get_db
from models.user import User
from schemas.iot import (
    IoTDeviceCreate,
    IoTDeviceResponse,
    IoTTelemetryCreate,
    IoTTelemetryResponse,
    IoTCommandRequest,
    IoTCommandResponse,
    SmartAssistantRecommendationResponse,
)
from services.smart_gym_service import SmartGymService

router = APIRouter(prefix="/iot", tags=["Smart Gym & IoT"])


@router.get("/devices", response_model=List[IoTDeviceResponse])
def get_user_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves all registered/demo IoT equipment devices for authenticated user.
    Auto-seeds sample demo devices if user has no devices yet.
    """
    return SmartGymService.get_user_devices(db, current_user.id)


@router.post("/devices", response_model=IoTDeviceResponse, status_code=status.HTTP_201_CREATED)
def register_device(
    payload: IoTDeviceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Registers a new smart equipment device assigned to authenticated user.
    """
    return SmartGymService.register_device(db, current_user.id, payload)


@router.get("/devices/{device_id}", response_model=IoTDeviceResponse)
def get_device_details(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Fetches details for a single smart equipment device owned by authenticated user.
    """
    device = SmartGymService.get_device_by_id(db, current_user.id, device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"IoT Device with ID {device_id} not found.",
        )
    return device


@router.post("/devices/{device_id}/telemetry", response_model=IoTTelemetryResponse, status_code=status.HTTP_201_CREATED)
def ingest_telemetry(
    device_id: int,
    payload: IoTTelemetryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Ingests and validates performance telemetry from a smart equipment device.
    """
    try:
        return SmartGymService.ingest_telemetry(db, current_user.id, device_id, payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/devices/{device_id}/telemetry", response_model=List[IoTTelemetryResponse])
def get_device_telemetry_history(
    device_id: int,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves historical telemetry logs for a specified equipment device.
    """
    try:
        return SmartGymService.get_device_telemetry_history(db, current_user.id, device_id, limit)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post("/devices/{device_id}/command", response_model=IoTCommandResponse)
def send_device_command(
    device_id: int,
    payload: IoTCommandRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Issues an equipment control command (set, increase, or decrease resistance) via MQTT/Simulation.
    """
    try:
        return SmartGymService.send_device_command(db, current_user.id, device_id, payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/assistant/recommendations", response_model=SmartAssistantRecommendationResponse)
def get_smart_assistant_recommendations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves Smart Gym Assistant rest interval & intensity recommendations for user's active equipment.
    """
    return SmartGymService.evaluate_assistant_recommendations(db, current_user.id)


@router.post("/simulation/generate/{device_id}", response_model=IoTTelemetryResponse, status_code=status.HTTP_201_CREATED)
def trigger_simulated_telemetry(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generates a controlled, simulated telemetry event for demo testing and UI visualization.
    """
    try:
        return SmartGymService.generate_simulated_telemetry_event(db, current_user.id, device_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
