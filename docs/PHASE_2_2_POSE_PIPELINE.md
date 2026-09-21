# Phase 2.2 — OpenCV + MediaPipe Pose Pipeline Guide

## Overview
Phase 2.2 establishes the foundational Computer Vision pipeline for the **AI Gym & Fitness Assistant**. Its single objective is acquiring accurate 3D skeletal body landmarks from camera streams or test imagery, serving as the input layer for future biomechanical angle analysis and rep tracking.

```
Camera / Video Stream / Static Image
                ↓
    OpenCV (Frame Acquisition & BGR)
                ↓
    Format Conversion (BGR → RGB, mp.Image)
                ↓
MediaPipe Tasks PoseLandmarker (BlazePose)
                ↓
   33 Anatomical Body Landmarks
                ↓
Pose Visualizer (Render Skeleton & Status)
```

---

## Architecture Components

### 1. Role of OpenCV
OpenCV (`cv2`) handles image I/O and graphics processing:
- **Frame Acquisition:** Interfacing with webcams (`cv2.VideoCapture`) or decoding static video/image files.
- **Color Space Normalization:** OpenCV loads images in **BGR** format, while MediaPipe requires **RGB**. OpenCV performs this conversion (`cv2.cvtColor`).
- **Annotation & Graphics:** Rendering high-contrast skeletal joints, limb connections, and status badges.
- **Display & Persistence:** Displaying real-time GUI preview windows (`cv2.imshow`) or encoding output snapshots to disk (`cv2.imwrite`).

### 2. Role of MediaPipe
Google MediaPipe provides lightweight, high-fidelity real-time body tracking:
- Powered by the **BlazePose** architecture, detecting **33 3D landmarks** covering the head, torso, arms, hands, legs, and feet.
- Implemented using the modern **MediaPipe Tasks Vision API** (`mediapipe.tasks.python.vision.PoseLandmarker`), running with CPU hardware acceleration (XNNPACK delegate) with a measured inference latency of 26.3 ms per frame on CPU (~38 FPS static frame throughput).

### 3. What is a Landmark?
A **landmark** represents a key anatomical joint or feature on the human body. MediaPipe defines 33 standard landmark points indexed 0 through 32:
- **Head:** Nose (0), Eyes (1–3, 4–6), Ears (7, 8), Mouth (9, 10).
- **Upper Body:** Shoulders (11, 12), Elbows (13, 14), Wrists (15, 16), Pinky/Index/Thumb (17–22).
- **Core:** Hips (23, 24).
- **Lower Body:** Knees (25, 26), Ankles (27, 28), Heels (29, 30), Foot Indices (31, 32).

---

## Detector Data Schema

Each call to `PoseDetector.detect(frame)` returns a structured `PoseDetectionResult` instance containing:

| Field | Type | Description |
| :--- | :--- | :--- |
| `detected` | `bool` | `True` if a person was detected; `False` if no person was present. |
| `landmarks` | `List[PoseLandmarkPoint]` | List of 33 landmarks in anatomical index order (0 to 32). |
| `landmark_dict` | `Dict[str, PoseLandmarkPoint]` | Fast lookup table by landmark name (e.g. `'LEFT_ELBOW'`). |
| `image_width` | `int` | Width of the evaluated image frame in pixels. |
| `image_height` | `int` | Height of the evaluated image frame in pixels. |

### Landmark Point Attributes (`PoseLandmarkPoint`):
- `id`: Integer landmark identifier (0 to 32).
- `name`: Human-readable name (e.g. `LEFT_KNEE`, `RIGHT_SHOULDER`).
- `x`: Normalized horizontal coordinate ($0.0 \le x \le 1.0$).
- `y`: Normalized vertical coordinate ($0.0 \le y \le 1.0$).
- `z`: Depth coordinate representing landmark depth relative to the mid-hip point.
- `visibility`: Confidence score ($0.0 \le v \le 1.0$) that the joint is not occluded.
- `presence`: Confidence score ($0.0 \le p \le 1.0$) that the joint is within the image frame.
- `pixel_x`: Absolute pixel coordinate on the X-axis ($0 \le px < \text{width}$).
- `pixel_y`: Absolute pixel coordinate on the Y-axis ($0 \le py < \text{height}$).

---

## Running the Pipeline & Demos

Activate the Python virtual environment:
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
```

### 1. Run Automated Unit Tests
Executes the comprehensive 9-test suite (media loading, blank frame safety, real human fixture detection, landmark bounds, visualizer):
```powershell
python ..\ml\pose\test_pose_detector.py
```

### 2. Run Interactive / Live Demos
```powershell
# Live webcam demo with GUI window (press Q to exit):
python ..\ml\pose\demo.py

# Headless webcam test (captures 10 frames and writes snapshot):
python ..\ml\pose\demo.py --headless --save ..\ml\fixtures\webcam_test.png

# Run on the deterministic test image fixture:
python ..\ml\pose\demo.py --source fixture --save ..\ml\fixtures\fixture_output.png

# Run on a custom static image:
python ..\ml\pose\demo.py --source image --path C:\path\to\photo.jpg --save output.png
```

---

## Hardware & Environment Support

- **Webcam Availability:** `demo.py` automatically checks if a webcam is accessible (`cv2.VideoCapture(0)`). If no webcam is attached or access is blocked, it logs an informational notice and **automatically falls back** to the built-in deterministic fixture image (`ml/fixtures/sample_person.png`).
- **Python Compatibility:** Tested and verified on **Python 3.14.2**, using `opencv-python==5.0.0.93` and `mediapipe==1.0.1`.
- **Model Asset:** The detector uses `ml/models/pose_landmarker_lite.task` (Float16, ~5.7 MB). If missing on a clean machine, `PoseDetector` automatically downloads it from Google's official model repository on first run.

---

## Known Limitations & Phase Boundaries

- **Single Person Focus:** BlazePose detects the primary foreground subject. Multi-person tracking is out of scope.
- **Lighting & Occlusion:** Extreme lighting or severe joint occlusion may lower landmark visibility scores below 0.3.
- **Strict Scope Separation (What is NOT in Phase 2.2):**
  - No exercise angle calculations (e.g. knee flex, elbow extension).
  - No rep counting or state machines.
  - No exercise classification or form scoring.
  - No database logging or frontend UI integration.
