import json
import os
from datetime import datetime
from typing import Any, Dict, Optional, Tuple


class MQTTService:
    """
    MQTT Communication & Node-RED Integration Service for Phase 8.
    Provides structured MQTT topic creation, telemetry formatting, and command publishing.
    Defaults to transparent Simulation Mode if MQTT broker is unavailable or disabled.
    """

    BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
    BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    TOPIC_PREFIX = os.getenv("MQTT_TOPIC_PREFIX", "gym/smart_gym")
    MQTT_ENABLED = os.getenv("MQTT_ENABLED", "false").lower() == "true"

    @classmethod
    def get_topics_for_device(cls, gym_id: int, device_uid: str) -> Dict[str, str]:
        """
        Generates standard MQTT topics for specified gym and device UID.
        Format:
        - telemetry: gym/{gym_id}/device/{device_uid}/telemetry
        - state:     gym/{gym_id}/device/{device_uid}/state
        - command:   gym/{gym_id}/device/{device_uid}/command
        """
        prefix = f"{cls.TOPIC_PREFIX}/gym_{gym_id}/device_{device_uid}"
        return {
            "telemetry": f"{prefix}/telemetry",
            "state": f"{prefix}/state",
            "command": f"{prefix}/command",
        }

    @classmethod
    def format_node_red_telemetry_payload(
        cls,
        device_uid: str,
        user_id: int,
        exercise_type: str,
        resistance_kg: float,
        repetition_count: int,
        intensity_score: float,
        heart_rate_bpm: Optional[int] = None,
        operational_state: str = "active",
    ) -> Dict[str, Any]:
        """
        Formats standardized JSON telemetry payload compatible with Node-RED MQTT dashboards.
        """
        return {
            "version": "1.0",
            "device_id": device_uid,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "exercise_type": exercise_type,
            "resistance_kg": round(float(resistance_kg), 2),
            "repetition_count": int(repetition_count),
            "intensity_score": round(float(intensity_score), 2),
            "heart_rate_bpm": heart_rate_bpm,
            "operational_state": operational_state,
            "simulation_mode": True,
            "mqtt_topic_target": f"{cls.TOPIC_PREFIX}/device_{device_uid}/telemetry",
        }

    @classmethod
    def publish_command(
        cls,
        gym_id: int,
        device_uid: str,
        command_type: str,
        target_resistance_kg: float,
        user_id: int,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Publishes an equipment control command via MQTT or executes via Simulation Mode.
        Returns: (success: bool, status_message: str, payload_json: dict)
        """
        topics = cls.get_topics_for_device(gym_id, device_uid)
        payload = {
            "command": command_type,
            "device_id": device_uid,
            "user_id": user_id,
            "target_resistance_kg": target_resistance_kg,
            "timestamp": datetime.utcnow().isoformat(),
            "sender": "FastAPI_Smart_Gym_Assistant",
        }

        if not cls.MQTT_ENABLED:
            # Fallback to Simulation Mode
            status_msg = (
                f"[Simulation Mode] MQTT Broker inactive. "
                f"Simulated command '{command_type}' ({target_resistance_kg}kg) queued on topic '{topics['command']}'."
            )
            return True, status_msg, payload

        # If MQTT_ENABLED is True, attempt to send via paho-mqtt if available
        try:
            import paho.mqtt.publish as publish
            publish.single(
                topics["command"],
                payload=json.dumps(payload),
                hostname=cls.BROKER_HOST,
                port=cls.BROKER_PORT,
            )
            return True, f"MQTT Command published to {topics['command']}", payload
        except Exception as e:
            # Graceful fallback on broker connection failure
            return True, f"[Simulation Mode Fallback] MQTT publish failed ({str(e)}). Command executed in simulation mode.", payload
