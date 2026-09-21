# AI GYM & FITNESS ASSISTANT — PHASE 2 MASTER IMPLEMENTATION GUIDE
## The Complete Pose-to-Performance System (Computer Vision, Biomechanics, FSM, Scoring, APIs, Database & Frontend)

---

### Document Overview
* **Project:** AI Gym & Fitness Assistant
* **Phase:** Phase 2 — AI Gym Trainer (Pose-to-Performance System)
* **Status:** Fully Implemented, Tested, Integrated, and Officially Accepted
* **Audience:** Developer 3 (Anand - Project Owner), Developer 4 (Future Teammates), Developer 1 (Architecture & Teaching)
* **Python Environment:** Python 3.14.2 (Virtual Environment at `backend/.venv`)
* **Node Environment:** Node.js v22.x / Next.js 16.3.5 / React 19.2.8
* **Database:** PostgreSQL 16 on `localhost:5432`, Database: `ai_gym`

---

## CHAPTER 1: Executive Overview & System Architecture

### 1.1 What Phase 2 Accomplishes
Phase 2 transforms the AI Gym & Fitness Assistant from a foundational user-profile application into an intelligent, computer-vision-powered fitness coach. It takes raw video or webcam frames, extracts human body joints in 3D space, calculates biomechanical joint kinematics, deterministically tracks exercise repetitions using a Finite State Machine (FSM), evaluates form correctness in real time, computes an explainable 7-factor Performance Score, persists detailed repetition telemetry into PostgreSQL, and presents interactive workout feedback on a modern web dashboard.

### 1.2 End-to-End Pipeline Architecture
The system functions as a strictly unidirectional, deterministic pipeline:

```
  ┌─────────────────────────┐
  │   Video / Camera Stream │ (30 FPS RGB Frames from Webcam or Video)
  └────────────┬────────────┘
               │
               ▼
  ┌─────────────────────────┐
  │ MediaPipe Pose Landmarker│ (ml/pose/pose_detector.py - Tasks API)
  │  33 3D Body Landmarks   │ (x, y, z normalized + visibility & presence)
  └────────────┬────────────┘
               │
               ▼
  ┌─────────────────────────┐
  │ Landmark Quality Gate   │ (min_visibility >= 0.5; occluded joints rejected)
  └────────────┬────────────┘
               │
               ▼
  ┌─────────────────────────┐
  │ 2D Joint Angle Geometry │ (ml/pose/angle_calculator.py)
  │ (HIP -> KNEE -> ANKLE)  │ (Planar vector cosine with numerical clipping)
  └────────────┬────────────┘
               │
               ▼
  ┌─────────────────────────┐
  │ Signal Smoothing (SMA)  │ (ml/pose/smoothing.py)
  │ 5-Frame Moving Average  │ (Attenuates camera micro-jitter; eliminates lag)
  └────────────┬────────────┘
               │
               ▼
  ┌─────────────────────────┐
  │ Squat State Machine     │ (ml/pose/squat_state_machine.py)
  │ UP ⇄ DESCEND ⇄ BOT ⇄ ASC│ (Deterministic transitions; rep counter increment)
  └────────────┬────────────┘
               │
               ▼
  ┌─────────────────────────┐
  │ Biomechanical Form Rules│ (ml/pose/form_analyzer.py)
  │ Depth, Torso, Valgus    │ (Real-time coaching cues & rep summaries)
  └────────────┬────────────┘
               │
               ▼
  ┌─────────────────────────┐
  │ Performance Scoring     │ (ml/pose/performance_analyzer.py)
  │ 7-Factor Model [0-100]  │ (ROM, tempo, stability, form, jerk smoothness, sym, comp)
  └────────────┬────────────┘
               │
               ▼
  ┌─────────────────────────┐
  │ FastAPI Backend & DB    │ (backend/routers/workouts.py + PostgreSQL)
  │ Sessions & Pose Metrics │ (Per-rep storage; strict cross-user authorization)
  └────────────┬────────────┘
               │
               ▼
  ┌─────────────────────────┐
  │ Next.js 16 Web Frontend │ (frontend/src/app/workout, history, dashboard)
  │ Live HUD, Modal, Trends │ (In-frame cues, telemetry overlay, score breakdown)
  └─────────────────────────┘
```

---

## CHAPTER 2: Phase 2.1 — Exercise Catalogue & Workout Session Model

### 2.1 Overview & Goals
Phase 2.1 establishes the relational database models required to track workouts, sets, repetitions, and exercises without affecting existing Phase 1 user and profile data.

### 2.2 Relational Models & Integrity Rules
Located in `backend/models/`:

1. **`Exercise` (`backend/models/exercise.py`):**
   - Represents the canonical catalogue of physical exercises.
   - Fields: `id`, `name`, `category`, `target_muscles`, `instructions`, `created_at`.
   - Seeded with three exercises:
     - **Squat** (`Legs`): Lower-body compound exercise targeting quadriceps, hamstrings, and glutes.
     - **Push-up** (`Chest`): Upper-body bodyweight exercise targeting chest, shoulders, and triceps.
     - **Bicep Curl** (`Arms`): Isolation exercise targeting biceps brachii via elbow flexion.

2. **`WorkoutSession` (`backend/models/workout_session.py`):**
   - Represents a continuous workout training session belonging to a user.
   - Fields: `id`, `user_id` (FK to `users.id`), `started_at`, `ended_at`, `performance_score`, `calories`, `notes`.
   - Deletion rule: `ON DELETE CASCADE` from `users` (if a user is deleted, their workout sessions are cleaned up).

3. **`WorkoutExercise` (`backend/models/workout_exercise.py`):**
   - Junction model recording sets, reps, and exercise performed during a session.
   - Fields: `id`, `workout_session_id` (FK `workout_sessions.id` with `CASCADE`), `exercise_id` (FK `exercises.id` with `RESTRICT`), `sets`, `reps`, `notes`.
   - **Architectural Safeguard — `ON DELETE RESTRICT`:** Deleting an exercise from the catalogue is blocked if historical workout sessions reference it. This prevents historical data corruption.
   - **Check Constraints:** Non-negative constraints `ck_workout_exercises_sets_non_negative` (`sets >= 0`) and `ck_workout_exercises_reps_non_negative` (`reps >= 0`).

4. **`PoseMetric` (`backend/models/pose_metric.py`):**
   - Records granular biomechanical kinematics for individual repetitions.
   - Fields: `id`, `workout_session_id` (FK `workout_sessions.id` with `CASCADE`), `rep_number`, `min_knee_angle`, `max_torso_lean`, `duration_seconds`, `form_status`, `violations`, `metrics_json`, `created_at`.
   - **Storage Efficiency:** Stores scalar floats and compact JSON strings. Zero heavy video binaries or raw base64 frames are stored in relational tables.

---

## CHAPTER 3: Phase 2.2 — OpenCV + MediaPipe Tasks Vision Pipeline

### 3.1 Overview & MediaPipe Tasks Architecture
MediaPipe legacy solutions (`mp.solutions.pose`) have been deprecated by Google in modern Python distributions. AI Gym implements the modern **MediaPipe Tasks Vision API** (`mediapipe.tasks.python.vision.PoseLandmarker`).

### 3.2 Key Components
Located in `ml/pose/`:

1. **`PoseDetector` (`ml/pose/pose_detector.py`):**
   - Loads the pre-trained `pose_landmarker_heavy.task` bundle (stored in `ml/models/`).
   - Accepts BGR images from OpenCV, converts them to RGB `mp.Image`.
   - Extracts all 33 standard body landmarks:
     - Head: `NOSE`, `LEFT_EYE`, `RIGHT_EYE`, `LEFT_EAR`, `RIGHT_EAR`.
     - Torso: `LEFT_SHOULDER`, `RIGHT_SHOULDER`, `LEFT_HIP`, `RIGHT_HIP`.
     - Arms: `LEFT_ELBOW`, `RIGHT_ELBOW`, `LEFT_WRIST`, `RIGHT_WRIST`.
     - Legs: `LEFT_KNEE`, `RIGHT_KNEE`, `LEFT_ANKLE`, `RIGHT_ANKLE`, `LEFT_HEEL`, `RIGHT_HEEL`, `LEFT_FOOT_INDEX`, `RIGHT_FOOT_INDEX`.
   - Returns structured `PoseDetectionResult` containing:
     - Normalized coordinates `(x, y, z)` in $[0.0, 1.0]$.
     - Pixel coordinates `(pixel_x, pixel_y)` scaled to the camera frame dimensions.
     - Confidence metrics `(visibility, presence)`.
   - Measured latency: ~26 ms on modern CPU.

2. **`PoseVisualizer` (`ml/pose/visualizer.py`):**
   - Renders 35 anatomical skeletal connections.
   - Filters out occluded landmarks (`visibility < 0.5`).
   - Renders a semi-transparent HUD overlay showing real-time joint angle, movement phase, rep counter, and coaching feedback.

---

## CHAPTER 4: Phase 2.3 — 2D Joint Angles & Squat Finite State Machine

### 4.1 2D Joint Angle Geometry (`ml/pose/angle_calculator.py`)
To compute the internal knee flexion angle at vertex $B$ formed by Hip ($A$), Knee ($B$), and Ankle ($C$):

1. **Displacement Vectors:**
   $$\vec{v}_1 = A - B = (a_x - b_x, a_y - b_y)$$
   $$\vec{v}_2 = C - B = (c_x - b_x, c_y - b_y)$$

2. **Euclidean Magnitudes:**
   $$\|\vec{v}_1\| = \sqrt{v_{1x}^2 + v_{1y}^2}, \quad \|\vec{v}_2\| = \sqrt{v_{2x}^2 + v_{2y}^2}$$

3. **Zero-Length Safeguard:** If $\|\vec{v}_1\| < 10^{-7}$ or $\|\vec{v}_2\| < 10^{-7}$, the geometry is degenerate and the function returns `None`.

4. **Normalized Dot Product & Clamping:**
   $$\cos(\theta) = \frac{\vec{v}_1 \cdot \vec{v}_2}{\|\vec{v}_1\| \|\vec{v}_2\|}$$
   $$\theta = \arccos\left(\text{clip}(\cos(\theta), -1.0, 1.0)\right) \times \frac{180^\circ}{\pi}$$

*Why 2D Pixel Coordinates?* 2D pixel coordinates preserve the camera sensor's physical aspect ratio and perspective projection without introducing depth estimation jitter from monocular depth heuristics.

### 4.2 Signal Smoothing Filter (`ml/pose/smoothing.py`)
Raw camera landmarks exhibit sub-pixel frame-to-frame jitter.
- **`MovingAverageFilter` (Simple Moving Average - SMA):**
  Sliding window of $N=5$ frames (~166 ms at 30 FPS).
  $$\bar{\theta}_t = \frac{1}{k}\sum_{i=0}^{k-1} \theta_{t-i}, \quad k = \min(t+1, N)$$
  Gracefully handles startup when fewer than $N$ samples exist, eliminating initial freeze.
- **`ExponentialMovingAverageFilter` (EMA):**
  Provided as an optional utility ($S_t = \alpha X_t + (1 - \alpha) S_{t-1}$ with $\alpha = 0.3$). The active squat pipeline uses SMA.

### 4.3 Squat Finite State Machine (`ml/pose/squat_state_machine.py`)
The `SquatStateMachine` enforces an unbroken, cyclical progression before incrementing the rep counter:

| State | Transition Trigger | Description |
| :--- | :--- | :--- |
| **`UP`** | Initial state or $\theta \ge 160^\circ$ | Athlete standing tall; knees and hips locked out. |
| **`DESCENDING`** | $\theta < 155^\circ$ ($160^\circ - 5^\circ$ hysteresis) | Hips and knees actively flexing downward. |
| **`BOTTOM`** | $\theta \le 100^\circ$ (`bottom_threshold`) | Parallel or deep squat inflection zone. Sets `_hit_bottom = True`. |
| **`ASCENDING`** | $\theta > 105^\circ$ ($100^\circ + 5^\circ$ hysteresis) | Athlete driving upward out of the squat hole. |
| **`UP` (Completion)** | $\theta \ge 160^\circ$ | Rep completed! If `_hit_bottom` was satisfied, $\text{Reps} \mathrel{+}= 1$. |

#### Anti-Cheat & Rep-Validation Guarantees:
1. **Shallow/Half Squats Never Increment Reps:** If an athlete descends only to $105^\circ$ and stands back up, the FSM transitions directly from `DESCENDING` back to `UP` with `_hit_bottom = False`. Zero repetitions are counted, and the cue alerts `"Squat not deep enough. Rep uncounted."`.
2. **No Duplicate Reps in the Hole:** Pausing at the bottom ($\le 100^\circ$) keeps the FSM in `BOTTOM`. No repetitions increment until the user ascends and achieves full lockout in `UP`.
3. **Incomplete Ascent Safeguard:** Reaching $85^\circ$ and ascending to $140^\circ$ leaves the FSM in `ASCENDING`. Reps remain 0 until full extension ($\ge 160^\circ$) is verified.

---

## CHAPTER 5: Phase 2.4 — Squat Form Analysis & Real-Time Coaching

### 5.1 Overview & Biomechanical Rules
Located in `ml/pose/form_analyzer.py`. Evaluates user posture against deterministic, rule-based kinesiological standards:

1. **Rule A — Squat Depth:**
   - Evaluates knee angle $\theta_{\text{knee}}$ at bottom phase.
   - Threshold: $\theta_{\text{knee}} \le 100.0^\circ$ (`depth_threshold`).
   - If $\theta > 100.0^\circ$: Violation `INSUFFICIENT_DEPTH`, Feedback: `"Go slightly deeper."`.
   - If $\theta \le 100.0^\circ$: Status `ADEQUATE`.

2. **Rule B — Torso Forward Lean:**
   - Vector from Hip to Shoulder relative to upward vertical axis:
     $$\theta_{\text{torso}} = \arctan2(|x_{\text{shoulder}} - x_{\text{hip}}|, y_{\text{hip}} - y_{\text{shoulder}}) \times \frac{180^\circ}{\pi}$$
   - Threshold: $\theta_{\text{torso}} \le 45.0^\circ$ (`max_torso_lean`).
   - If $\theta_{\text{torso}} > 45.0^\circ$: Violation `EXCESSIVE_TORSO_LEAN`, Feedback: `"Keep your chest more upright."`.

3. **Rule C — Lateral Knee Alignment (Valgus Detection):**
   - Measures normalized lateral deviation of the knee joint relative to the vertical ankle axis:
     $$\text{deviation} = \frac{|x_{\text{knee}} - x_{\text{ankle}}|}{\max(|y_{\text{ankle}} - y_{\text{knee}}|, 1.0)}$$
   - Threshold: $\text{deviation} \le 0.35$ (`knee_deviation_threshold`).
   - If $\text{deviation} > 0.35$: Violation `KNEE_ALIGNMENT_ISSUE`, Feedback: `"Keep your knees aligned with your feet."`.

4. **Rule D — Landmark Reliability Gate:**
   - Requires $\min(\text{visibility}, \text{presence}) \ge 0.5$ for all required joints.
   - If any landmark is occluded, status becomes `UNKNOWN`, zero feedback violations are fabricated, and the system reports `"Landmarks occluded or out of frame."`.

### 5.2 Repetition Form Summaries (`RepFormSummary`)
Upon rep completion (`rep_completed == True`), `SquatFormAnalyzer` aggregates minimum knee angle reached, maximum torso lean, worst knee deviation, and triggered violations into an immutable per-rep summary.

---

## CHAPTER 6: Phase 2.5 — Biomechanical Performance Scoring Engine

### 6.1 Deterministic Scoring Model (Version 1.0)
Located in `ml/pose/performance_analyzer.py`. Implements an explainable, transparent 7-factor scoring equation normalized strictly to $[0.0, 100.0]$:

$$S = 0.25 S_{\text{form}} + 0.20 S_{\text{comp}} + 0.15 S_{\text{stability}} + 0.15 S_{\text{ROM}} + 0.10 S_{\text{tempo}} + 0.10 S_{\text{smooth}} + 0.05 S_{\text{sym}}$$

All weights are implementation-defined defaults summing to $1.0$:

| Factor | Description | Mathematical Formulation | Weight | Range |
| :--- | :--- | :--- | :---: | :---: |
| **Form Accuracy ($S_{\text{form}}$)** | Absence of posture violations | $\max\left(0, 100 - \frac{\sum V}{\text{total\_reps}} \times 25\right)$ | 0.25 | $[0, 100]$ |
| **Completion Quality ($S_{\text{comp}}$)** | Parallel depth fulfillment | $\frac{\text{full\_reps}}{\text{total\_reps}} \times 100$ | 0.20 | $[0, 100]$ |
| **Joint Stability ($S_{\text{stability}}$)** | Lateral knee consistency | $\max\left(0, 100 - \sigma_{\text{knee}} \times 200\right)$ | 0.15 | $[0, 100]$ |
| **ROM Consistency ($S_{\text{ROM}}$)** | Uniformity of depth across reps | $\max\left(0, 100 - \|\bar{\theta}_{\min} - 90^\circ\| \times 2.0 - \sigma_{\theta} \times 3.0\right)$ | 0.15 | $[0, 100]$ |
| **Tempo & Pacing ($S_{\text{tempo}}$)** | Cadence control (ideal 3.0s) | $\max\left(0, 100 - \|\bar{t} - 3.0\| \times 20 - \sigma_t \times 20\right)$ | 0.10 | $[0, 100]$ |
| **Motion Smoothness ($S_{\text{smooth}}$)** | Minimum angular jerk | $\max\left(0, 100 - \frac{\bar{J}}{1500} \times 100\right)$ where $\bar{J} = \frac{1}{T}\int \|\alpha'''(t)\|dt$ | 0.10 | $[0, 100]$ |
| **Bilateral Symmetry ($S_{\text{sym}}$)** | Left vs right knee agreement | $\max\left(0, 100 - \overline{\|\Delta\theta\|} \times 4.0\right)$ (default 90.0 if single-side) | 0.05 | $[0, 100]$ |

### 6.2 Qualitative Score Ratings
- $S \ge 85.0$: **EXCELLENT**
- $70.0 \le S < 85.0$: **GOOD**
- $55.0 \le S < 70.0$: **SATISFACTORY**
- $S < 55.0$: **NEEDS IMPROVEMENT**

---

## CHAPTER 7: Backend API Layer & Security Architecture

### 7.1 Routers & Endpoints
Implemented in `backend/routers/workouts.py`:

| Method | Endpoint | Auth | Purpose |
| :--- | :--- | :---: | :--- |
| `GET` | `/exercises` | Public | Returns available exercise catalogue. |
| `POST` | `/workouts/start` | JWT Bearer | Initializes new active workout session for user. |
| `POST` | `/workouts/{session_id}/complete` | JWT Bearer | Finalizes workout, records reps, duration, calories, score, and per-rep pose metrics. |
| `GET` | `/workouts/history` | JWT Bearer | Retrieves user's past workout sessions. |
| `GET` | `/workouts/{session_id}` | JWT Bearer | Inspects detailed breakdown and pose metrics of a specific session. |
| `GET` | `/performance/summary` | JWT Bearer | Longitudinal progress: average score, trend (`IMPROVING`, `STABLE`, `DECLINING`), and focus areas. |

### 7.2 Strict Cross-User Authorization Isolation
- Every database query for workouts and summaries explicitly enforces `WorkoutSession.user_id == current_user.id`.
- If User A attempts to `GET` or `POST` to `/workouts/{session_id}` belonging to User B, the endpoint returns **`403 Forbidden`** with detail: `"You do not have permission to access this workout session"`.
- User B's workout sessions never leak into User A's `/workouts/history` or `/performance/summary`.

---

## CHAPTER 8: Database Schema & Live PostgreSQL Migrations

### 8.1 Schema Summary
Live PostgreSQL schema in database `ai_gym`:

```sql
-- Exercises Catalogue
CREATE TABLE exercises (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL,
    target_muscles VARCHAR(255),
    instructions TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL
);

-- Workout Sessions
CREATE TABLE workout_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    started_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL,
    ended_at TIMESTAMP WITHOUT TIME ZONE,
    performance_score FLOAT,
    calories FLOAT,
    notes TEXT
);

-- Workout Exercises Junction
CREATE TABLE workout_exercises (
    id SERIAL PRIMARY KEY,
    workout_session_id INTEGER NOT NULL REFERENCES workout_sessions(id) ON DELETE CASCADE,
    exercise_id INTEGER NOT NULL REFERENCES exercises(id) ON DELETE RESTRICT,
    sets INTEGER DEFAULT 1 NOT NULL CHECK (sets >= 0),
    reps INTEGER DEFAULT 0 NOT NULL CHECK (reps >= 0),
    notes VARCHAR(255)
);

-- Granular Repetition Biomechanics
CREATE TABLE pose_metrics (
    id SERIAL PRIMARY KEY,
    workout_session_id INTEGER NOT NULL REFERENCES workout_sessions(id) ON DELETE CASCADE,
    rep_number INTEGER NOT NULL,
    min_knee_angle FLOAT,
    max_torso_lean FLOAT,
    duration_seconds FLOAT,
    form_status VARCHAR(50),
    violations VARCHAR(255),
    metrics_json TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW() NOT NULL
);
```

---

## CHAPTER 9: Frontend Architecture (Next.js 16 + React 19)

### 9.1 Overview & Pages
Located in `frontend/src/app/`:

1. **`workout/page.tsx` (`/workout`):**
   - **Interactive Live Workout Studio:** Integrates camera feed with `navigator.mediaDevices.getUserMedia`.
   - **Graceful Fallback:** If camera access is denied or unavailable, runs in simulation visualizer mode.
   - **In-Frame HUD:** Displays real-time reps, current knee angle, state badge (`UP`, `DESCENDING`, `BOTTOM`, `ASCENDING`), and real-time coaching cue banner.
   - **Post-Workout Modal:** Displays total score, qualitative rating, 5-factor progress bars, half-squat depth alerts, and coaching advice.

2. **`history/page.tsx` (`/history`):**
   - **Longitudinal Analytics Dashboard:** Average performance score, total reps, workouts logged, and dynamic trend badge (`▲ Improving`, `● Stable`, `▼ Declining`).
   - **Session Log Table:** Date, exercise name, sets $\times$ reps, color-coded score badge, calories burned, and notes.

3. **`dashboard/page.tsx` (`/dashboard`):**
   - Added Phase 2 Quick Launch Banner and navigation buttons (`+ Start Workout`, `History`, `Edit Profile`, `Logout`).

---

## CHAPTER 10: Complete Verification & Test Suite Reference

All 82 automated test checks across the entire system pass with 100% success:

| Suite | Component | Test Command | Checks | Status |
| :--- | :--- | :--- | :---: | :---: |
| **Phase 1 Regression** | Auth & User Profile CRUD | `python verify_step_2d.py` | 12 | **PASS (12/12)** |
| **Phase 2.1 Regression** | DB Models, Constraints & Seed | `python verify_phase_2_1.py` | 9 | **PASS (9/9)** |
| **Phase 2.2 Vision** | MediaPipe Tasks & Landmarks | `python test_pose_detector.py` | 9 | **PASS (9/9)** |
| **Phase 2.3 FSM & Angles** | 2D Geometry, SMA, Rep Validation | `python test_squat_pipeline.py` | 22 | **PASS (22/22)** |
| **Phase 2.4 Form Analysis** | Depth, Torso, Valgus, Visibility | `python test_form_analyzer.py` | 11 | **PASS (11/11)** |
| **Phase 2.5 Performance** | 7-Factor Scoring & Jerk | `python test_performance_analyzer.py` | 8 | **PASS (8/8)** |
| **Phase 2 API** | Workout Lifecycle & Security | `python test_phase_2_api.py` | 4 | **PASS (4/4)** |
| **E2E Smoke Test** | Full User Journey (Dash $\to$ Summary) | `python smoke_test_e2e.py` | 7 | **PASS (7/7)** |
| **Frontend Compilation** | Next.js 16 Production Build | `npm.cmd run build` | 9 routes | **PASS (0 errors)** |

**Total Verification Checks:** **82 / 82 Passed (100%).**

---

## CHAPTER 11: Beginner-Friendly Run Commands

### 11.1 Running the Backend API Server
```powershell
# Open terminal in project root
cd C:\Users\anand\AI-Gym-Fitness-Assistant\backend

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run FastAPI server with hot-reload on port 8000
uvicorn main:app --reload --port 8000
```
*API will be live at `http://127.0.0.1:8000` with interactive Swagger docs at `http://127.0.0.1:8000/docs`.*

### 11.2 Running the Next.js Frontend Server
```powershell
# Open terminal in frontend directory
cd C:\Users\anand\AI-Gym-Fitness-Assistant\frontend

# Run Next.js development server
npm.cmd run dev
```
*Web dashboard will be live at `http://localhost:3000`.*

### 11.3 Running Computer Vision Standalone Demos
```powershell
cd C:\Users\anand\AI-Gym-Fitness-Assistant\ml\pose

# Run live webcam squat tracker (press Q to exit)
..\..\backend\.venv\Scripts\python.exe demo.py --source webcam

# Run on deterministic athlete fixture image (offline/headless)
..\..\backend\.venv\Scripts\python.exe demo.py --source fixture --save ..\fixtures\output.png --headless
```

### 11.4 Running the Complete Test Suite
```powershell
# 1. Run all ML tests (Pose, Angles, FSM, Form, Performance Scoring):
cd C:\Users\anand\AI-Gym-Fitness-Assistant\ml
..\backend\.venv\Scripts\python.exe -m unittest discover -s pose -p "test_*.py"

# 2. Run Backend Workout & Security API tests:
cd C:\Users\anand\AI-Gym-Fitness-Assistant\backend
.\.venv\Scripts\python.exe test_phase_2_api.py

# 3. Run End-to-End Practical Smoke Test:
.\.venv\Scripts\python.exe smoke_test_e2e.py

# 4. Run Phase 2.1 Database Integrity Checks:
.\.venv\Scripts\python.exe verify_phase_2_1.py

# 5. Run Phase 1 Auth Regression Checks:
.\.venv\Scripts\python.exe verify_step_2d.py

# 6. Verify Frontend Production Build:
cd C:\Users\anand\AI-Gym-Fitness-Assistant\frontend
npm.cmd run build
```

---

## CHAPTER 12: Architectural Design Decisions, Trade-Offs & Limitations

1. **Deterministic Rule-Based Logic vs. Black-Box ML:**
   - *Decision:* Used explicit mathematical vector cosine and state machines rather than opaque deep neural networks for rep counting and form scoring.
   - *Rationale:* Rule-based systems provide explainable, deterministic feedback that users can trust. A user knows exactly why a rep was rejected (e.g. "knee angle $105^\circ > 100^\circ$").
2. **Camera Placement & 2D Projection:**
   - *Limitation:* 2D angles calculate planar projections. The system operates with highest precision when the camera is positioned at side profile (sagittal plane), approximately hip height, 6 to 9 feet away.
3. **Occlusion Handling:**
   - *Decision:* The landmark reliability gate ($0.5$ confidence threshold) safely aborts angle calculation when key joints leave the frame, avoiding fabricated reps and hallucinated form scores.
4. **Scope Boundary Maintained:**
   - Phase 3 components (Dietician/Nutrition modules, Virtual Gym Buddy multi-modal agents, Habit ML classifiers, IoT/MQTT sensor integrations) have been cleanly isolated and deferred to Phase 3.
