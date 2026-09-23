# Phase 8 — Smart Gym Assistant + IoT
## Master Implementation & Architecture Guide

---

### Executive Overview

Phase 8 introduces the **Smart Gym Assistant + IoT**, establishing the project's smart equipment intelligence layer. Rather than operating as a passive dashboard or raw device monitor, this module connects gym equipment devices (e.g., smart power racks, connected cable crossover stations, assault air bikes) via MQTT communication and REST APIs, ingests performance telemetry, tracks set intensity and heart rate, provides safe equipment resistance interfaces, and delivers grounded Smart Gym Assistant heuristics.

The module provides two integrated capabilities:
1. **IoT Communication & Equipment Abstraction Layer**: Manages equipment representation (`IoTDevice`, `IoTTelemetry`, `IoTCommandLog`), topic-based MQTT pub/sub streaming (`gym/{gym_id}/device/{device_uid}/telemetry`, `/state`, `/command`), Node-RED compatible JSON schemas, and transparent fallback to **Simulation Mode** ("Sample Demo Device / Simulation Mode") when physical MQTT brokers are inactive.
2. **Smart Gym Assistant Heuristic Engine**: Continuously evaluates telemetry streams to recommend optimal recovery rest intervals ($90\text{--}120\text{s}$), progressive overload load increases ($+2.5\text{ kg}$ to $+5.0\text{ kg}$), and elevated heart rate / fatigue warnings ($> 165\text{ BPM}$).

---

### Core Architectural Principles

1. **Structured Equipment Data Model & Relational Schema (`models/iot.py`)**:
   - `IoTDevice`: Equipment representation storing `device_uid`, `device_name`, `equipment_category`, `status`, `is_simulated`, `current_resistance_kg`, `target_resistance_kg`, `mac_address`, and `firmware_version`.
   - `IoTTelemetry`: Time-series performance logs storing `exercise_type`, `resistance_kg`, `repetition_count`, `session_duration_seconds`, `intensity_score`, `heart_rate_bpm`, and `operational_state`.
   - `IoTCommandLog`: Record of resistance & equipment commands storing `command_type`, `payload_json`, `status`, and creation timestamps.

2. **MQTT Broker Integration & Simulation Engine (`services/mqtt_service.py`)**:
   - Environment-driven broker configuration (`MQTT_BROKER_HOST`, `MQTT_BROKER_PORT`, `MQTT_TOPIC_PREFIX`, `MQTT_ENABLED`).
   - Standardized topic hierarchy:
     - Telemetry: `gym/{gym_id}/device/{device_uid}/telemetry`
     - Device State: `gym/{gym_id}/device/{device_uid}/state`
     - Commands: `gym/{gym_id}/device/{device_uid}/command`
   - Formats Node-RED compatible JSON payloads containing timestamps, device ID, load, rep count, intensity score, and heart rate.
   - If an MQTT broker is unreachable or disabled, seamlessly defaults to **Simulation Mode** without breaking system operations.

3. **Smart Gym Assistant Rules & Heuristics (`services/smart_gym_service.py`)**:
   - **Optimal Rest Interval Rule**: Triggered when set intensity $\ge 75.0\%$ or rep count $\ge 12$. Recommends a $90\text{--}120\text{s}$ recovery rest interval.
   - **Progressive Overload Rule**: Triggered when recent 3 sets maintain completion reps $\ge 10$ and intensity $\ge 70.0\%$. Recommends a $+2.5\text{ kg}$ load increase.
   - **Elevated Heart Rate Warning**: Triggered when heart rate telemetry $> 165\text{ BPM}$. Recommends extending rest to 3 minutes.
   - **Equipment Status Monitor**: Surface active/idle state of connected devices.

4. **Safe Equipment Resistance Interface**:
   - Validates resistance commands strictly within safe physical boundaries $[0.0\text{ kg}, 300.0\text{ kg}]$.
   - Supports commands: `set_resistance`, `increase_resistance`, `decrease_resistance`, and `emergency_stop`.

5. **Relational Database Persistence & User Isolation**:
   - Links `iot_devices.user_id` to `users.id` with `ON DELETE CASCADE`.
   - Links `iot_telemetry.user_id` and `iot_command_logs.user_id` to `users.id` with `ON DELETE CASCADE`.
   - Every service and router call filters strictly by `user_id == current_user.id`.

6. **FastAPI Endpoints Scoped to Authenticated User (`routers/iot.py`)**:
   - `GET /iot/devices`: List all user equipment (auto-seeds demo devices if empty).
   - `POST /iot/devices`: Register new equipment.
   - `GET /iot/devices/{id}`: Fetch single device state.
   - `POST /iot/devices/{id}/telemetry`: Ingest and validate telemetry event.
   - `GET /iot/devices/{id}/telemetry`: Fetch telemetry history.
   - `POST /iot/devices/{id}/command`: Safely issue resistance control command.
   - `GET /iot/assistant/recommendations`: Fetch Smart Gym Assistant recommendations.
   - `POST /iot/simulation/generate/{id}`: Trigger simulated set telemetry for testing.

7. **Interactive Next.js Frontend (`/iot`)**:
   - Tab 1: **Connected Devices & Controls** (Device status badges, resistance sliders, emergency stop, sample demo badges).
   - Tab 2: **Telemetry Stream** (Live table displaying rep count, load, intensity gauge, heart rate).
   - Tab 3: **Smart Assistant Heuristics** (Rest interval recommendations, progressive overload suggestions, fatigue alerts).

---

### Database Schema

#### 1. `iot_devices` Table
| Field Name | Type | Description |
| :--- | :--- | :--- |
| `id` | `INTEGER` | Primary Key |
| `user_id` | `INTEGER` | Foreign Key -> `users.id` (`ON DELETE CASCADE`) |
| `device_uid` | `VARCHAR(100)` | Unique device identifier |
| `device_name` | `VARCHAR(150)` | Human-readable name |
| `equipment_category` | `VARCHAR(50)` | Category (`smart_rack`, `cable_machine`, `hiit_bike`) |
| `status` | `VARCHAR(30)` | Operational status (`online`, `active`, `idle`, `offline`) |
| `is_simulated` | `BOOLEAN` | Simulation mode flag (Default `True`) |
| `current_resistance_kg` | `FLOAT` | Current resistance set on equipment |
| `target_resistance_kg` | `FLOAT` | Target resistance requested |
| `mac_address` | `VARCHAR(50)` | Hardware MAC address |
| `firmware_version` | `VARCHAR(50)` | Firmware version string |
| `created_at` | `TIMESTAMP` | Record creation timestamp |
| `updated_at` | `TIMESTAMP` | Record update timestamp |

#### 2. `iot_telemetry` Table
| Field Name | Type | Description |
| :--- | :--- | :--- |
| `id` | `INTEGER` | Primary Key |
| `device_id` | `INTEGER` | Foreign Key -> `iot_devices.id` (`ON DELETE CASCADE`) |
| `user_id` | `INTEGER` | Foreign Key -> `users.id` (`ON DELETE CASCADE`) |
| `exercise_type` | `VARCHAR(100)` | Target exercise name |
| `resistance_kg` | `FLOAT` | Resistance load in kg `[0, 500]` |
| `repetition_count` | `INTEGER` | Repetitions completed `[0, 200]` |
| `session_duration_seconds`| `INTEGER` | Duration in seconds |
| `intensity_score` | `FLOAT` | Calculated set intensity `[0.0, 100.0]` |
| `heart_rate_bpm` | `INTEGER (NULL)`| Heart rate telemetry `[30, 250]` |
| `operational_state` | `VARCHAR(30)` | Device state (`active`, `resting`, `idle`) |
| `timestamp` | `TIMESTAMP` | Telemetry timestamp |

#### 3. `iot_command_logs` Table
| Field Name | Type | Description |
| :--- | :--- | :--- |
| `id` | `INTEGER` | Primary Key |
| `device_id` | `INTEGER` | Foreign Key -> `iot_devices.id` (`ON DELETE CASCADE`) |
| `user_id` | `INTEGER` | Foreign Key -> `users.id` (`ON DELETE CASCADE`) |
| `command_type` | `VARCHAR(50)` | Command (`set_resistance`, `increase_resistance`, etc.) |
| `payload_json` | `TEXT` | JSON payload of published command |
| `status` | `VARCHAR(30)` | Status (`sent`, `simulated_success`) |
| `created_at` | `TIMESTAMP` | Record creation timestamp |

---

### API Specifications

#### 1. `GET /iot/devices`
- **Auth**: Bearer JWT (`get_current_user`)
- **Response**:
```json
[
  {
    "id": 1,
    "user_id": 1,
    "device_uid": "smart_rack_alpha_01_u1",
    "device_name": "Smart Power Rack #1 (Barbell)",
    "equipment_category": "smart_rack",
    "status": "online",
    "is_simulated": true,
    "current_resistance_kg": 75.0,
    "target_resistance_kg": 75.0,
    "mac_address": "AA:BB:CC:DD:EE:01",
    "firmware_version": "v2.4.0",
    "created_at": "2026-09-23T22:50:00",
    "updated_at": "2026-09-23T22:50:00"
  }
]
```

#### 2. `POST /iot/devices/{device_id}/command`
- **Auth**: Bearer JWT (`get_current_user`)
- **Request Body**:
```json
{
  "command_type": "set_resistance",
  "target_resistance_kg": 85.0
}
```
- **Response**:
```json
{
  "id": 4,
  "device_id": 1,
  "user_id": 1,
  "command_type": "set_resistance",
  "payload": {
    "command": "set_resistance",
    "device_id": "smart_rack_alpha_01_u1",
    "user_id": 1,
    "target_resistance_kg": 85.0
  },
  "status": "simulated_success",
  "current_resistance_kg": 85.0,
  "target_resistance_kg": 85.0,
  "created_at": "2026-09-23T22:52:00"
}
```

---

### Automated Verification Results

- **Dedicated Phase 8 Test Suite (`backend/test_phase_8_iot.py`)**: 20/20 PASSED (`0.757s`).
- **Phase 1–7 Regression Suite**: 91/91 PASSED.
- **Total Suite Passing**: 111/111 PASSED.
- **Frontend Build Verification (`npm run build`)**: 15/15 static pages generated cleanly with 0 TypeScript compilation errors.
