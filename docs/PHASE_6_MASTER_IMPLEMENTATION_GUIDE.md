# Phase 6 — Fitness Habit Tracker & Behavioral AI
## Master Implementation & Architecture Guide

---

### Executive Overview

Phase 6 introduces the **Fitness Habit Tracker & Behavioral AI**, transforming historical workout data into actionable behavioral intelligence. Unlike simple streak counters, this module extracts an 8-dimensional behavioral feature vector from actual user sessions, trains a scikit-learn `LogisticRegression` model with temporal time-series split validation, predicts the probability of a user skipping their upcoming workout window, delivers grounded non-causal factor attributions, provides adaptive habit nudges, and recommends historically consistent workout schedule windows based on past completion frequency.

---

### Core Architectural Principles

1. **Deterministic Feature Engineering Layer (`HabitFeatureEngine`)**:
   Extracts 8 distinct behavioral features strictly from database records (`WorkoutSession` and `User` models) while enforcing temporal cutoff boundaries (`as_of_date`) to guarantee zero future data leakage.

2. **Strict Temporal Training Leakage Enforcement**:
   When constructing training samples across historical sliding 7-day observation windows $T_i$, every target observation window $[T_i+1, T_i+7]$ MUST strictly satisfy `target_end <= evaluation_cutoff`. The model is never trained on any sample whose target window extends beyond the evaluation timestamp.

3. **Disambiguation: Cold-Start vs ML Dataset Requirements**:
   - **Condition A (User Behavioral History):** Users with $< 3$ completed workout sessions return `status: "insufficient_data"`, `skip_probability: null`, `risk_level: "insufficient_data"`, and `model_info: {"model": "None (Cold Start)", "ml_trained": False}`.
   - **Condition B (ML Labeled Sample Size & Class Variance):** Users with $\ge 3$ sessions receive an active prediction (`status: "active_prediction"`). When labeled historical samples are sparse ($N < 6$) or lack class variance (single class), the system uses the `SparseDataFallbackModel` and explicitly sets `"ml_trained": False` in `model_info`. When $N \ge 6$ with positive and negative target variance, `scikit-learn` `LogisticRegression` fits and sets `"ml_trained": True`.

4. **Non-Causal Behavioral Factor Attribution**:
   Provides clear behavioral signal explanations (e.g., *"4 days elapsed since last session (signal associated with higher skip risk)"*) using non-causal language that educates without making diagnostic health claims.

5. **Actionable Adaptive Nudges & Evidence-Based Observational Schedule Intelligence**:
   Generates targeted, non-medical habit nudges based on risk tier (`low`, `moderate`, `high`) and displays historically frequent session times (e.g., *"Historically Most Frequent Session Time: Mondays at 08:00 AM"*) avoiding absolute claims of future optimality.

6. **Database Persistence (`HabitPrediction`)**:
   Stores all prediction telemetry snapshots linked to `users.id` with `ON DELETE CASCADE` support.

7. **FastAPI Endpoints Scoped to Authenticated User**:
   - `GET /habit/status`: Returns current habit intelligence snapshot.
   - `GET /habit/history`: Returns historical telemetry log.

---

### Database Schema (`habit_predictions`)

| Field Name | Type | Description |
| :--- | :--- | :--- |
| `id` | `INTEGER` | Primary key |
| `user_id` | `INTEGER` | Foreign key referencing `users.id` (`ON DELETE CASCADE`) |
| `prediction_date` | `TIMESTAMP` | Timestamp when prediction snapshot was generated |
| `skip_probability` | `FLOAT (NULL)` | Predicted probability of skipping next window `[0.00, 1.00]` |
| `risk_level` | `VARCHAR(30)` | Risk tier: `"low"`, `"moderate"`, `"high"`, or `"insufficient_data"` |
| `primary_factor` | `VARCHAR(255)` | Primary behavioral signal key associated with prediction |
| `nudge_text` | `TEXT` | Grounded behavioral nudge message |
| `recommended_schedule` | `VARCHAR(255)` | Evidence-based observational schedule recommendation text |
| `created_at` | `TIMESTAMP` | Record creation timestamp |

---

### The 8 Behavioral Features

1. **`days_since_last_workout`** (`int`): Days elapsed since most recent completed session.
2. **`workout_frequency_7d`** (`int`): Count of completed sessions in past 7 days.
3. **`workout_frequency_30d`** (`int`): Count of completed sessions in past 30 days.
4. **`avg_weekly_workouts`** (`float`): Average weekly sessions across overall user history.
5. **`consistency_score`** (`float`): Ratio of active calendar weeks to total registered weeks `[0.0, 1.0]`.
6. **`preferred_weekday_ratio`** (`float`): Ratio of sessions occurring on user's most frequent weekday.
7. **`max_gap_days_30d`** (`int`): Longest consecutive gap in days between sessions in past 30 days.
8. **`form_score_trend_delta`** (`float`): Change in average posture/form score between recent 2 and prior 2 sessions.

---

### API Specifications

#### 1. `GET /habit/status`
- **Auth**: Bearer JWT (`get_current_user`)
- **Status Code**: `200 OK`
- **Response**:
```json
{
  "user_id": 1,
  "status": "active_prediction",
  "total_sessions_logged": 5,
  "skip_probability": 0.22,
  "risk_level": "low",
  "risk_explanation": "Your workout consistency is strong. Low probability of skipping your upcoming workouts.",
  "features": {
    "days_since_last_workout": 2,
    "workout_frequency_7d": 2,
    "workout_frequency_30d": 5,
    "avg_weekly_workouts": 2.5,
    "consistency_score": 0.8,
    "preferred_weekday_ratio": 0.4,
    "max_gap_days_30d": 3,
    "form_score_trend_delta": 1.5
  },
  "behavioral_factors": [
    {
      "feature_name": "days_since_last_workout",
      "description": "Recent workout completed within the last 24–48 hours (signal associated with lower skip risk).",
      "impact_level": "high",
      "signal_direction": "decreases_risk"
    }
  ],
  "adaptive_nudge": "Great workout momentum! Keep up your current rhythm by sticking to your preferred training days.",
  "recommended_schedule": "Historically Most Frequent Session Time: Mondays at 08:00 AM (based on your highest historical completion frequency).",
  "model_info": {
    "model": "SparseDataFallbackModel",
    "ml_trained": false,
    "c_param": null,
    "training_samples": 3,
    "temporal_validation": "chronological_split",
    "fallback_reason": "insufficient_labeled_samples"
  },
  "timestamp": "2026-09-23T15:00:00Z"
}
```

#### 2. `GET /habit/history`
- **Auth**: Bearer JWT (`get_current_user`)
- **Query Params**: `limit` (`int`, default=10, min=1, max=100)
- **Status Code**: `200 OK`
- **Response**:
```json
{
  "user_id": 1,
  "predictions": [
    {
      "id": 12,
      "user_id": 1,
      "prediction_date": "2026-09-23T15:00:00Z",
      "skip_probability": 0.22,
      "risk_level": "low",
      "primary_factor": "days_since_last_workout",
      "nudge_text": "Great workout momentum!",
      "recommended_schedule": "Historically Most Frequent Session Time: Mondays at 08:00 AM",
      "created_at": "2026-09-23T15:00:00Z"
    }
  ]
}
```

---

### Automated Verification Results

- **Phase 6 Dedicated Test Suite (`backend/test_phase_6_habit.py`)**: 22/22 PASSED (`0.710s`).
- **Regression Suite (Phases 1–5)**:
  - `test_phase_1_users.py`: 9/9 PASSED (`1.486s`).
  - `test_phase_2_api.py`: 4/4 PASSED (`0.607s`).
  - `test_phase_3_performance.py`: 10/10 PASSED (`0.571s`).
  - `test_phase_4_nutrition.py`: 13/13 PASSED (`0.759s`).
  - `test_phase_5_buddy.py`: 13/13 PASSED (`1.299s`).
- **Next.js Production Build (`npm run build`)**: 0 errors, 13 static pages generated successfully.

---

*Phase 6 Implementation Complete — AI Gym & Fitness Assistant*
