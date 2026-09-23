import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from models.iot import IoTDevice, IoTTelemetry, IoTCommandLog
from models.user import User
from schemas.iot import (
    IoTDeviceCreate,
    IoTDeviceResponse,
    IoTTelemetryCreate,
    IoTTelemetryResponse,
    IoTCommandRequest,
    IoTCommandResponse,
    SmartAssistantRecommendationItem,
    SmartAssistantRecommendationResponse,
)
from services.mqtt_service import MQTTService


DEFAULT_DEMO_DEVICES = [
    {
        "device_uid": "smart_rack_alpha_01",
        "device_name": "Smart Power Rack #1 (Barbell)",
        "equipment_category": "smart_rack",
        "status": "online",
        "is_simulated": True,
        "current_resistance_kg": 75.0,
        "target_resistance_kg": 75.0,
        "mac_address": "AA:BB:CC:DD:EE:01",
        "firmware_version": "v2.4.0",
    },
    {
        "device_uid": "cable_station_beta_02",
        "device_name": "Connected Cable Crossover Station",
        "equipment_category": "cable_machine",
        "status": "active",
        "is_simulated": True,
        "current_resistance_kg": 27.5,
        "target_resistance_kg": 27.5,
        "mac_address": "AA:BB:CC:DD:EE:02",
        "firmware_version": "v2.1.2",
    },
    {
        "device_uid": "hiit_assault_bike_03",
        "device_name": "Assault Air Bike IoT",
        "equipment_category": "hiit_bike",
        "status": "idle",
        "is_simulated": True,
        "current_resistance_kg": 15.0,
        "target_resistance_kg": 15.0,
        "mac_address": "AA:BB:CC:DD:EE:03",
        "firmware_version": "v1.9.5",
    },
]


class SmartGymService:
    """
    Smart Gym Assistant & IoT Service for Phase 8.
    Manages equipment devices, ingests & validates telemetry, executes safe resistance commands,
    and evaluates grounded Smart Gym Assistant rest/intensity heuristics.
    """

    @classmethod
    def seed_default_devices_for_user(cls, db: Session, user_id: int):
        """Seeds initial sample demo devices for a user if none exist."""
        existing = db.execute(
            select(IoTDevice).where(IoTDevice.user_id == user_id)
        ).scalars().all()

        if len(existing) > 0:
            return

        for demo in DEFAULT_DEMO_DEVICES:
            uid = f"{demo['device_uid']}_u{user_id}"
            device = IoTDevice(
                user_id=user_id,
                gym_id=demo.get("gym_id", 1),
                device_uid=uid,
                device_name=demo["device_name"],
                equipment_category=demo["equipment_category"],
                status=demo["status"],
                is_simulated=demo["is_simulated"],
                current_resistance_kg=demo["current_resistance_kg"],
                target_resistance_kg=demo["target_resistance_kg"],
                mac_address=demo["mac_address"],
                firmware_version=demo["firmware_version"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(device)
        db.commit()

    @classmethod
    def get_user_devices(cls, db: Session, user_id: int) -> List[IoTDeviceResponse]:
        """Retrieves all registered/demo IoT devices owned by specified user."""
        cls.seed_default_devices_for_user(db, user_id)

        devices = db.execute(
            select(IoTDevice)
            .where(IoTDevice.user_id == user_id)
            .order_by(IoTDevice.id.asc())
        ).scalars().all()

        return [IoTDeviceResponse.model_validate(d) for d in devices]

    @classmethod
    def register_device(cls, db: Session, user_id: int, payload: IoTDeviceCreate) -> IoTDeviceResponse:
        """Registers a new IoT device for specified user."""
        uid = payload.device_uid or f"{payload.equipment_category}_{int(datetime.utcnow().timestamp())}_u{user_id}"

        # Check UID collision
        existing = db.execute(
            select(IoTDevice).where(IoTDevice.device_uid == uid)
        ).scalars().first()
        if existing:
            uid = f"{uid}_{int(datetime.utcnow().timestamp())}"

        device = IoTDevice(
            user_id=user_id,
            gym_id=payload.gym_id or 1,
            device_uid=uid,
            device_name=payload.device_name,
            equipment_category=payload.equipment_category,
            status="online",
            is_simulated=True,
            current_resistance_kg=0.0,
            target_resistance_kg=0.0,
            mac_address=payload.mac_address,
            firmware_version=payload.firmware_version or "v2.1.0",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        return IoTDeviceResponse.model_validate(device)

    @classmethod
    def get_device_by_id(cls, db: Session, user_id: int, device_id: int) -> Optional[IoTDeviceResponse]:
        """Fetches single device by ID with user ownership check."""
        device = db.execute(
            select(IoTDevice).where(
                IoTDevice.id == device_id,
                IoTDevice.user_id == user_id,
            )
        ).scalars().first()

        if not device:
            return None
        return IoTDeviceResponse.model_validate(device)

    @classmethod
    def ingest_telemetry(
        cls, db: Session, user_id: int, device_id: int, payload: IoTTelemetryCreate
    ) -> IoTTelemetryResponse:
        """
        Validates and stores incoming telemetry from an IoT device.
        """
        device = db.execute(
            select(IoTDevice).where(
                IoTDevice.id == device_id,
                IoTDevice.user_id == user_id,
            )
        ).scalars().first()

        if not device:
            raise ValueError(f"IoT Device with ID {device_id} not found for current user.")

        # Calculated intensity score if not provided
        intensity = payload.intensity_score
        if intensity is None:
            # Intensity heuristic: (load / 100kg * 50) + (reps / 12 * 50), clamped [0, 100]
            intensity = min(100.0, max(10.0, (payload.resistance_kg / 100.0 * 50.0) + (payload.repetition_count / 12.0 * 50.0)))

        # Update device status and resistance state
        device.status = "active" if payload.operational_state == "active" else "online"
        device.current_resistance_kg = payload.resistance_kg
        device.updated_at = datetime.utcnow()

        telemetry = IoTTelemetry(
            device_id=device.id,
            user_id=user_id,
            exercise_type=payload.exercise_type,
            resistance_kg=payload.resistance_kg,
            repetition_count=payload.repetition_count,
            session_duration_seconds=payload.session_duration_seconds,
            intensity_score=intensity,
            heart_rate_bpm=payload.heart_rate_bpm,
            operational_state=payload.operational_state or "active",
            timestamp=datetime.utcnow(),
        )
        db.add(telemetry)
        db.commit()
        db.refresh(telemetry)
        return IoTTelemetryResponse.model_validate(telemetry)

    @classmethod
    def get_device_telemetry_history(
        cls, db: Session, user_id: int, device_id: int, limit: int = 20
    ) -> List[IoTTelemetryResponse]:
        """Retrieves telemetry history for a specific device."""
        device = db.execute(
            select(IoTDevice).where(
                IoTDevice.id == device_id,
                IoTDevice.user_id == user_id,
            )
        ).scalars().first()

        if not device:
            raise ValueError(f"IoT Device with ID {device_id} not found for current user.")

        logs = db.execute(
            select(IoTTelemetry)
            .where(IoTTelemetry.device_id == device_id)
            .order_by(IoTTelemetry.timestamp.desc())
            .limit(limit)
        ).scalars().all()

        return [IoTTelemetryResponse.model_validate(l) for l in logs]

    @classmethod
    def send_device_command(
        cls, db: Session, user_id: int, device_id: int, command: IoTCommandRequest
    ) -> IoTCommandResponse:
        """
        Validates and executes an equipment control command (setting resistance).
        Communicates with MQTT service and updates device state.
        """
        device = db.execute(
            select(IoTDevice).where(
                IoTDevice.id == device_id,
                IoTDevice.user_id == user_id,
            )
        ).scalars().first()

        if not device:
            raise ValueError(f"IoT Device with ID {device_id} not found for current user.")

        cmd_type = command.command_type.lower()
        new_target = device.target_resistance_kg

        if cmd_type == "set_resistance":
            if command.target_resistance_kg is None:
                raise ValueError("target_resistance_kg is required for set_resistance command.")
            new_target = command.target_resistance_kg
        elif cmd_type == "increase_resistance":
            step = command.step_increment_kg or 2.5
            new_target = min(300.0, device.target_resistance_kg + step)
        elif cmd_type == "decrease_resistance":
            step = command.step_increment_kg or 2.5
            new_target = max(0.0, device.target_resistance_kg - step)
        elif cmd_type == "emergency_stop":
            new_target = 0.0
            device.status = "idle"
        else:
            raise ValueError(f"Unsupported command_type '{command.command_type}'. Supported: set_resistance, increase_resistance, decrease_resistance, emergency_stop.")

        # Range check
        if new_target < 0.0 or new_target > 300.0:
            raise ValueError("Target resistance out of safe bounds [0.0kg, 300.0kg].")

        # Publish MQTT Command or execute in Simulation Mode
        success, status_msg, payload_dict = MQTTService.publish_command(
            gym_id=1,
            device_uid=device.device_uid,
            command_type=cmd_type,
            target_resistance_kg=new_target,
            user_id=user_id,
        )

        # Update Device state
        device.target_resistance_kg = new_target
        device.current_resistance_kg = new_target
        device.updated_at = datetime.utcnow()

        cmd_log = IoTCommandLog(
            device_id=device.id,
            user_id=user_id,
            command_type=cmd_type,
            payload_json=json.dumps(payload_dict),
            status="simulated_success" if device.is_simulated else "sent",
            created_at=datetime.utcnow(),
        )
        db.add(cmd_log)
        db.commit()
        db.refresh(cmd_log)

        return IoTCommandResponse(
            id=cmd_log.id,
            device_id=device.id,
            user_id=user_id,
            command_type=cmd_type,
            payload=payload_dict,
            status=cmd_log.status,
            current_resistance_kg=device.current_resistance_kg,
            target_resistance_kg=device.target_resistance_kg,
            created_at=cmd_log.created_at,
        )

    @classmethod
    def evaluate_assistant_recommendations(
        cls, db: Session, user_id: int
    ) -> SmartAssistantRecommendationResponse:
        """
        Evaluates Smart Gym Assistant heuristics across user's active devices and telemetry:
        1. Rest Interval Recommendation (High intensity / high rep accumulation -> 90-120s rest).
        2. Progressive Overload Suggestion (Strong performance consistency -> +2.5kg to +5.0kg load increase).
        3. Fatigue Alert (High HR or sharp intensity drop -> lower load or extend rest).
        """
        cls.seed_default_devices_for_user(db, user_id)

        devices = db.execute(
            select(IoTDevice).where(IoTDevice.user_id == user_id)
        ).scalars().all()

        recommendations: List[SmartAssistantRecommendationItem] = []

        for dev in devices:
            recent_telemetry = db.execute(
                select(IoTTelemetry)
                .where(IoTTelemetry.device_id == dev.id)
                .order_by(IoTTelemetry.timestamp.desc())
                .limit(5)
            ).scalars().all()

            if not recent_telemetry:
                # Idle equipment status
                recommendations.append(
                    SmartAssistantRecommendationItem(
                        recommendation_type="equipment_status",
                        title=f"{dev.device_name} Ready",
                        message=f"{dev.device_name} is online ({dev.current_resistance_kg:.1f} kg). Log a set or start a workout.",
                        action_suggested="Start Set",
                        target_device_uid=dev.device_uid,
                        suggested_value=dev.current_resistance_kg,
                        confidence_score=0.90,
                    )
                )
                continue

            latest = recent_telemetry[0]

            # 1. Fatigue Alert Check (HR > 165 OR Intensity Drop > 25%)
            has_high_hr = bool(latest.heart_rate_bpm and latest.heart_rate_bpm > 165)
            has_intensity_drop = False
            if len(recent_telemetry) >= 2:
                prev_intensity = recent_telemetry[1].intensity_score
                curr_intensity = latest.intensity_score
                if prev_intensity > 0:
                    drop_pct = ((prev_intensity - curr_intensity) / prev_intensity) * 100.0
                    if drop_pct > 25.0:
                        has_intensity_drop = True

            if has_high_hr or has_intensity_drop:
                reason_str = f"Elevated heart rate ({latest.heart_rate_bpm} BPM)" if has_high_hr else "Significant set intensity drop (>25%)"
                recommendations.append(
                    SmartAssistantRecommendationItem(
                        recommendation_type="fatigue_alert",
                        title="Fatigue & Intensity Drop Warning",
                        message=f"{reason_str} detected on {dev.device_name}. Extend recovery rest interval to 3 minutes or reduce load by 10%.",
                        action_suggested="Extend Rest / Lower Load",
                        target_device_uid=dev.device_uid,
                        suggested_value=180.0,
                        confidence_score=0.96,
                    )
                )

            # 2. Rest Interval Recommendation
            if latest.intensity_score >= 75.0 or latest.repetition_count >= 12:
                recommendations.append(
                    SmartAssistantRecommendationItem(
                        recommendation_type="rest_interval",
                        title="Optimal Recovery Rest Interval",
                        message=f"High set intensity ({latest.intensity_score:.1f}%) on {dev.device_name}. Take a 90–120 second recovery rest before your next set.",
                        action_suggested="Start 90s Rest Timer",
                        target_device_uid=dev.device_uid,
                        suggested_value=90.0,
                        confidence_score=0.94,
                    )
                )

            # 3. Progressive Overload Suggestion
            if len(recent_telemetry) >= 2:
                avg_reps = sum(t.repetition_count for t in recent_telemetry[:3]) / min(3, len(recent_telemetry))
                avg_intensity = sum(t.intensity_score for t in recent_telemetry[:3]) / min(3, len(recent_telemetry))

                if avg_reps >= 10 and avg_intensity >= 70.0:
                    suggested_increase = dev.current_resistance_kg + 2.5
                    recommendations.append(
                        SmartAssistantRecommendationItem(
                            recommendation_type="progressive_overload",
                            title="Progressive Overload Recommendation",
                            message=f"Strong completion history on {dev.device_name} (avg {avg_reps:.1f} reps). Consider increasing resistance to {suggested_increase:.1f} kg (+2.5 kg).",
                            action_suggested="Increase +2.5kg",
                            target_device_uid=dev.device_uid,
                            suggested_value=suggested_increase,
                            confidence_score=0.92,
                        )
                    )

        if not recommendations:
            recommendations.append(
                SmartAssistantRecommendationItem(
                    recommendation_type="equipment_status",
                    title="Smart Gym Equipment Synchronized",
                    message="All connected demo devices are online and ready for telemetry tracking.",
                    action_suggested=None,
                    target_device_uid=None,
                    suggested_value=None,
                    confidence_score=0.90,
                )
            )

        return SmartAssistantRecommendationResponse(
            user_id=user_id,
            total_active_devices=len(devices),
            recommendations=recommendations,
            timestamp=datetime.utcnow(),
        )

    @classmethod
    def generate_simulated_telemetry_event(
        cls, db: Session, user_id: int, device_id: int
    ) -> IoTTelemetryResponse:
        """
        Generates a controlled, deterministic simulated telemetry event for demo/testing purposes.
        """
        device = db.execute(
            select(IoTDevice).where(
                IoTDevice.id == device_id,
                IoTDevice.user_id == user_id,
            )
        ).scalars().first()

        if not device:
            raise ValueError(f"IoT Device with ID {device_id} not found for current user.")

        sim_payload = IoTTelemetryCreate(
            exercise_type="Barbell Back Squat" if "rack" in device.equipment_category else "Cable Chest Press",
            resistance_kg=device.current_resistance_kg if device.current_resistance_kg > 0 else 60.0,
            repetition_count=10,
            session_duration_seconds=45,
            intensity_score=78.5,
            heart_rate_bpm=142,
            operational_state="active",
        )

        return cls.ingest_telemetry(db, user_id, device.id, sim_payload)
