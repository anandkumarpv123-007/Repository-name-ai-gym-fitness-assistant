# Phase 2.3 — Joint Angles + Squat State Machine + Rep Counting Guide

## Overview
Phase 2.3 enhances the computer vision pipeline by deriving biomechanical joint kinematics from raw MediaPipe 3D body landmarks, attenuating high-frequency noise, and driving a deterministic Finite State Machine (FSM) to count repetitions for the **Squat**.

```
MediaPipe Landmarks (33 points)
                ↓
Landmark Visibility & Presence Validation
                ↓
2D Joint Angle Geometry (HIP -> KNEE -> ANKLE)
                ↓
Moving Average Smoothing Filter
                ↓
Squat Finite State Machine (UP -> DESCENDING -> BOTTOM -> ASCENDING -> UP)
                ↓
Repetition Counter Increment (Reps + 1)
                ↓
Movement Telemetry Overlay (Angle, State, Reps)
```

---

## 1. Joint-Angle Calculation (`angle_calculator.py`)

### 2D Vector Geometry
To compute the anatomical joint angle at vertex $B$ formed by segment $AB$ and segment $CB$:
1. Form displacement vectors:
   $$\vec{v}_1 = A - B = (a_x - b_x, a_y - b_y)$$
   $$\vec{v}_2 = C - B = (c_x - b_x, c_y - b_y)$$
2. Compute Euclidean vector lengths:
   $$\|\vec{v}_1\| = \sqrt{v_{1x}^2 + v_{1y}^2}, \quad \|\vec{v}_2\| = \sqrt{v_{2x}^2 + v_{2y}^2}$$
3. Zero-length safety check: if $\|\vec{v}_1\| < 10^{-7}$ or $\|\vec{v}_2\| < 10^{-7}$, the geometry is degenerate and the function returns `None`.
4. Calculate normalized dot product:
   $$\cos(\theta) = \frac{\vec{v}_1 \cdot \vec{v}_2}{\|\vec{v}_1\| \|\vec{v}_2\|}$$
5. Apply numerical clamping to strictly eliminate floating-point precision spillover ($[-1.0, 1.0]$) before taking the arc-cosine:
   $$\theta = \arccos(\text{clip}(\cos(\theta), -1.0, 1.0)) \times \frac{180}{\pi}$$

### Visibility Validation
Before computing angles, `calculate_landmark_angle` verifies that all three joints ($A$, $B$, and $C$) exhibit confidence scores $\ge \text{min\_visibility}$ (default $0.5$). If any key landmark is occluded or outside the camera frame, calculation is safely aborted and returns `None`.

---

## 2. Signal Smoothing Filter (`smoothing.py`)

Raw landmark tracking exhibits minor frame-to-frame jitter caused by camera compression artifacts and sub-pixel detection noise. Phase 2.3 provides `MovingAverageFilter`:
- **Window Size ($N$):** Default $5$ samples (~166 ms at 30 FPS).
- **Graceful Startup:** When fewer than $N$ samples are recorded, it averages whatever samples exist, preventing startup freezes.
- **Zero Phase Lag Distortion:** A short 5-frame moving average smoothly attenuates micro-jitter without noticeably lagging rapid squats.

---

## 3. Squat State Machine (`squat_state_machine.py`)

### State Machine Architecture
The `SquatStateMachine` requires a complete, unbroken biomechanical cycle before incrementing the repetition counter:

| State | Transition Trigger | Description |
| :--- | :--- | :--- |
| **`UP`** | Initial state or $\text{smoothed\_angle} \ge 160^\circ$ | Standing tall with hips and knees locked out. |
| **`DESCENDING`** | $\text{smoothed\_angle} < (160^\circ - 5^\circ) = 155^\circ$ | User is actively flexing knees and hips downward. |
| **`BOTTOM`** | $\text{smoothed\_angle} \le 100^\circ$ | Deep squat inflection zone meeting required depth. |
| **`ASCENDING`** | $\text{smoothed\_angle} > (100^\circ + 5^\circ) = 105^\circ$ | User drives upward out of the hole. |
| **`UP` (Cycle)** | $\text{smoothed\_angle} \ge 160^\circ$ | Repetition completed! $\text{Reps} \mathrel{+}= 1$. |

### Anti-Cheat & Robustness Guarantees:
1. **No Duplicate Reps at Bottom:** A user pausing or staying in a deep squat ($\le 100^\circ$) remains in `BOTTOM`. No additional repetitions can increment without rising up through `ASCENDING` to `UP`.
2. **Incomplete Squats Rejected:** If a user lowers to $120^\circ$ (never hitting the $100^\circ$ threshold) and stands back up, the FSM transitions directly from `DESCENDING` back to `UP`. Zero repetitions are counted.
3. **Hysteresis Buffering:** A configurable $\pm 5^\circ$ buffer prevents threshold oscillation chatter.

---

## 4. Telemetry Visualization HUD (`visualizer.py`)

The visualizer renders a non-intrusive, semi-transparent HUD card:
- **Knee Angle:** Displays smoothed numerical angle (e.g. `175.3°`).
- **State:** Displays dynamic state badge colored by phase:
  - `UP`: Neon Green
  - `DESCENDING`: Yellow / Gold
  - `BOTTOM`: Vibrant Orange
  - `ASCENDING`: Cyan / Blue
- **Reps Counter:** Displays bold green repetition count.

---

## 5. Running Tests and Demos

### Automated Test Suite:
```powershell
# Run Phase 2.3 Angle & Squat State Machine tests (17 tests):
python ..\ml\pose\test_squat_pipeline.py

# Run Phase 2.2 Pose Detector tests (9 tests):
python ..\ml\pose\test_pose_detector.py
```

### Live / Fixture Demonstration:
```powershell
# Run on sample athlete fixture:
python ..\ml\pose\demo.py --source fixture

# Run live webcam squat tracker (press Q to exit):
python ..\ml\pose\demo.py
```

---

## 6. Known Limitations & Phase Boundaries

- **Strict Single-Exercise Scope:** Only the Squat state machine is implemented. Push-ups, bicep curls, and other exercises are slated for Phase 2.4+.
- **2D Planar Projection:** Joint angles are computed on the 2D image projection. Extreme camera viewing angles (e.g., top-down ceiling view) can distort planar angles. Optimal tracking occurs with side or front-oblique camera placement.
- **Strict Scope Boundaries:** No form scoring, ML classifiers, frontend UI, or database persistence are introduced in this phase.
