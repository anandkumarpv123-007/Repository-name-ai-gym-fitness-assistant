import json
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from models.user import User


class IoTDevice(Base):
    """
    ORM Model representing a Smart Gym Equipment Device.
    Identifies device hardware, category, operational state, user assignment,
    and current/target resistance configurations.
    """
    __tablename__ = "iot_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    gym_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("gyms.id", ondelete="SET NULL"), nullable=True, default=1
    )
    device_uid: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    device_name: Mapped[str] = mapped_column(String(150), nullable=False)
    equipment_category: Mapped[str] = mapped_column(String(50), nullable=False, default="smart_rack")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="online")
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    current_resistance_kg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    target_resistance_kg: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    mac_address: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    firmware_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="v2.1.0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="iot_devices")
    telemetry_logs: Mapped[List["IoTTelemetry"]] = relationship(
        "IoTTelemetry", back_populates="device", cascade="all, delete-orphan"
    )
    command_logs: Mapped[List["IoTCommandLog"]] = relationship(
        "IoTCommandLog", back_populates="device", cascade="all, delete-orphan"
    )


class IoTTelemetry(Base):
    """
    ORM Model representing performance telemetry logs ingested from IoT devices.
    Stores exercise type, resistance load, rep counts, calculated intensity,
    optional heart rate, and operational status.
    """
    __tablename__ = "iot_telemetry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("iot_devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exercise_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resistance_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    repetition_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    session_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    intensity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    heart_rate_bpm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    operational_state: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    device: Mapped["IoTDevice"] = relationship("IoTDevice", back_populates="telemetry_logs")
    user: Mapped["User"] = relationship("User", back_populates="iot_telemetry")


class IoTCommandLog(Base):
    """
    ORM Model representing equipment & resistance control commands issued to devices.
    """
    __tablename__ = "iot_command_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("iot_devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    command_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="sent")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    device: Mapped["IoTDevice"] = relationship("IoTDevice", back_populates="command_logs")
    user: Mapped["User"] = relationship("User", back_populates="iot_commands")
