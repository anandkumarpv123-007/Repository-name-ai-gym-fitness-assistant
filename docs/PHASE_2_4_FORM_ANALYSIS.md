# Phase 2.4 — Squat Form Analysis + Real-Time Feedback Guide

## Overview
Phase 2.4 introduces deterministic, rule-based biomechanical form analysis to the squat pipeline. It evaluates the user's posture in real-time, flags kinematic violations, generates clear actionable coaching cues, and compiles per-repetition summaries upon rep completion.

```
MediaPipe Landmarks (33 points)
                ↓
Landmark Reliability Gate (min_visibility >= 0.5)
                ↓
Joint Kinematics:
  - Knee Flexion Angle (HIP -> KNEE -> ANKLE)
  - Torso Inclination Angle (SHOULDER -> HIP vs Vertical)
  - Lateral Knee Alignment Corridor (KNEE vs HIP-ANKLE Axis)
                ↓
Rule-Based Form Evaluator (Depth, Torso Lean, Knee Valgus/Displacement)
                ↓
Real-Time Coaching Feedback & Rep-Level Summary
                ↓
Visualizer Telemetry HUD
```

---

## 1. Biomechanical Form Rules & Mathematical Formulations

### Rule A: Squat Depth
* **Landmarks:** `HIP`, `KNEE`, `ANKLE` (Knee angle $\theta_{\text{knee}}$).
* **Threshold:** Configurable `depth_threshold = 100.0^\circ`.
* **Biomechanical Logic:**
  * Adequate squat depth requires the knee angle to flex to at least $100^\circ$ (or lower) during the inflection zone (`BOTTOM`).
  * If the user reaches the bottom or completes a repetition where $\theta_{\min} > 100^\circ$, the depth is flagged:
    * **Violation Code:** `INSUFFICIENT_DEPTH`
    * **Actionable Feedback:** `"Go slightly deeper."`
    * **Status:** `INSUFFICIENT`
  * If $\theta_{\min} \le 100^\circ$:
    * **Status:** `ADEQUATE`

### Rule B: Torso Angle / Forward Lean
* **Landmarks:** `SHOULDER`, `HIP`.
* **Threshold:** Configurable `max_torso_lean = 45.0^\circ` (from vertical).
* **Mathematical Basis:**
  * Let displacement vector from `HIP` to `SHOULDER` be $(dx, dy)$ where $dx = |x_{\text{shoulder}} - x_{\text{hip}}|$ and $dy = y_{\text{hip}} - y_{\text{shoulder}}$ (image $y$-axis increases downwards).
  * Inclination angle relative to upward vertical:
    $$\theta_{\text{torso}} = \arctan2(dx, dy) \times \frac{180}{\pi}$$
  * Natural standing lean: $0^\circ \text{--} 15^\circ$ (`UPRIGHT`).
  * Acceptable squat lean: $15^\circ \text{--} 45^\circ$ (`ACCEPTABLE`).
  * If $\theta_{\text{torso}} > 45^\circ$:
    * **Violation Code:** `EXCESSIVE_TORSO_LEAN`
    * **Actionable Feedback:** `"Keep your chest more upright."`
    * **Status:** `EXCESSIVE_LEAN`

### Rule C: Knee Alignment & Lateral Displacement
* **Landmarks:** `HIP`, `KNEE`, `ANKLE`.
* **Threshold:** Configurable `knee_deviation_threshold = 0.35`.
* **Mathematical Basis:**
  * Evaluates lateral displacement of the knee joint relative to the foot/ankle plane:
    $$\text{deviation} = \frac{|x_{\text{knee}} - x_{\text{ankle}}|}{\max(|y_{\text{ankle}} - y_{\text{knee}}|, 1.0)}$$
  * If $\text{deviation} > 0.35$:
    * **Violation Code:** `KNEE_ALIGNMENT_ISSUE`
    * **Actionable Feedback:** `"Keep your knees aligned with your feet."`
    * **Status:** `MISALIGNED`
  * Otherwise:
    * **Status:** `ALIGNED`

### Rule D: Landmark Reliability Gate
* All form evaluations are strictly gated on confidence:
  $$\min(\text{visibility}, \text{presence}) \ge \text{min\_visibility} \quad (\text{default } 0.5)$$
* If any required joint (`SHOULDER`, `HIP`, `KNEE`, `ANKLE`) is occluded, out of frame, or low-confidence:
  * `valid = False`
  * Status: `UNKNOWN`
  * Feedback: `["Landmarks occluded or out of frame."]`
  * **Zero fabricated form judgments are produced.**

---

## 2. Real-Time Feedback & Coaching Cues

Feedback messages are deterministic, actionable, and non-diagnostic:

| Condition | Violation Code | Actionable User Feedback |
| :--- | :--- | :--- |
| $\theta_{\text{knee}} > 100^\circ$ at bottom | `INSUFFICIENT_DEPTH` | `"Go slightly deeper."` |
| $\theta_{\text{torso}} > 45^\circ$ | `EXCESSIVE_TORSO_LEAN` | `"Keep your chest more upright."` |
| $\text{deviation} > 0.35$ | `KNEE_ALIGNMENT_ISSUE` | `"Keep your knees aligned with your feet."` |
| No violations detected | `None` | `"Good posture maintained."` |
| Occluded / Low confidence | `None` | `"Landmarks occluded or out of frame."` |

---

## 3. Repetition-Level Form Summary (`RepFormSummary`)

When a repetition is completed (`rep_completed == True`), `SquatFormAnalyzer` compiles a structured report:
```json
{
  "rep_number": 1,
  "depth_status": "ADEQUATE",
  "knee_alignment_status": "ALIGNED",
  "torso_status": "ACCEPTABLE",
  "min_knee_angle": 92.4,
  "max_torso_lean": 34.2,
  "violations": [],
  "feedback": [
    "Rep completed with good form!"
  ],
  "passed": true
}
```

---

## 4. Visualization HUD Updates

The HUD card rendered by [`visualizer.py`](file:///C:/Users/anand/AI-Gym-Fitness-Assistant/ml/pose/visualizer.py) is extended to display real-time form diagnostics:
- **Line 1:** `Knee Angle: XX.X°`
- **Line 2:** `State: UP / DESCENDING / BOTTOM / ASCENDING`
- **Line 3:** `Reps: N`
- **Line 4:** `Form: GOOD` (Neon Green) or `VIOLATION` (Orange/Amber)
- **Line 5:** `> Actionable Coaching Cue` (e.g. `> Keep your chest more upright.`)

---

## 5. Running Tests and Demos

```powershell
# Run Phase 2.4 Form Analysis tests (11 tests):
python ..\ml\pose\test_form_analyzer.py

# Run Phase 2.3 Squat Pipeline tests (17 tests):
python ..\ml\pose\test_squat_pipeline.py

# Run Phase 2.2 Pose Detector tests (9 tests):
python ..\ml\pose\test_pose_detector.py

# Run interactive fixture demonstration:
python ..\ml\pose\demo.py --source fixture
```

---

## 6. Strict Scope & Non-Diagnostic Disclaimer

* **Non-Diagnostic:** All rules are simplified kinematic heuristics for athletic coaching. They do not diagnose musculoskeletal injury or pathological joint mechanics.
* **Out of Scope (Preserved for Future Phases):**
  * No ML/LLM form classification
  * No Performance Score calculation
  * No database persistence of form metrics
  * No historical analytics or frontend dashboards
