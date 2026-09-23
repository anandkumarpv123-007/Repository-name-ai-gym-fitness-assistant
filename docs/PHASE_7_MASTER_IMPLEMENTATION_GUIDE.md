# Phase 7 — Gym Recommender & Workout Planner
## Master Implementation & Architecture Guide

---

### Executive Overview

Phase 7 introduces the **Gym Recommender & Workout Planner**, connecting fitness environment recommendations with personalized 7-day weekly workout scheduling. Rather than functioning as a static directory or generic chatbot, this module uses authenticated user context (profile goals, target muscle areas, equipment access, historical posture form warnings, and behavioral habit skip risk) to evaluate gym suitability and auto-generate adaptive weekly workout plans.

The phase provides two core integrated capabilities:
1. **Gym Recommender System**: Evaluates a catalog of synthetic facilities using transparent numerical suitability scoring ($[0, 100\%]$) and delivers observational, non-causal suitability match explanations (*"High Suitability Match: Offers heavy barbell equipment and specialized lifting zones aligned with your hypertrophy goal."*).
2. **Personalized 7-Day Workout Planner**: Generates goal-aligned weekly splits (`hypertrophy`, `strength`, `weight_loss`, `endurance`, `maintenance`) while dynamically adapting to Phase 3 posture form warnings (injecting targeted warmup notes and posture cues) and Phase 6 habit skip risks (capping volume to 3 training days for high-risk or cold-start users).

---

### Core Architectural Principles

1. **Structured Gym Catalogue & Recommendation Engine (`GymRecommenderService`)**:
   - Manages a seed catalog of synthetic gym facilities storing attributes such as equipment list, specialized amenities, distance (km), price tier, user rating, address, and operating hours.
   - Calculates transparent, deterministic numerical suitability scores ($[0, 100\%]$) based on user goal alignment, target muscle group equipment requirements, and proximity preferences.
   - Formulates non-causal observational match explanations that explain match rationale clearly without making false claims of absolute perfection.

2. **Goal-Aligned 7-Day Workout Split Generation (`WorkoutPlannerService`)**:
   - Auto-generates structured 7-day weekly plans with daily items specifying exercise names, sets, reps, target muscle groups, and rest day status.
   - Supports 5 distinct fitness goals: `hypertrophy` (Push/Pull/Legs 5-day split), `strength` (Upper/Lower 4-day heavy split), `weight_loss` (Full Body 4-day split with cardio), `endurance` (High-rep 5-day stamina split), and `maintenance` (Balanced 3-day split).

3. **Phase 3 Posture Performance Adaptation**:
   - Queries historical user performance records (`PerformanceLog`).
   - If frequent posture form errors or warnings are detected (e.g., knee valgus, forward lean, uneven hips, shallow depth), the planner marks `performance_adapted: true` and injects specific warmup notes and execution cues into relevant exercise items (e.g., *"Warmup & Technique Cue: Maintain knees aligned over toes to address prior knee valgus form warnings."*).

4. **Phase 6 Behavioral Habit Skip Risk Adaptation**:
   - Integrates with `HabitPredictionService` to evaluate user skip probability.
   - If habit skip risk tier is `"high"` or user is in a cold-start state (`"insufficient_data"`), the planner marks `habit_adapted: true`, caps weekly training volume to 3 manageable days, inserts additional rest/recovery days, and adds explicit adaptation notes to lower barrier to adherence.

5. **Relational Database Persistence & User Isolation**:
   - Persists gym records in `gyms`, active plans in `workout_plans`, and daily schedule items in `workout_plan_items`.
   - Links `workout_plans.user_id` to `users.id` with `ON DELETE CASCADE` and `workout_plan_items.plan_id` to `workout_plans.id` with `ON DELETE CASCADE`.

6. **FastAPI Endpoints Scoped to Authenticated User**:
   - `GET /gyms`: Returns full gym catalogue with optional search filtering.
   - `GET /gyms/recommendations`: Returns ranked list of gyms with numerical suitability scores and match explanations.
   - `POST /planner/generate`: Generates and persists a new 7-day adaptive workout plan.
   - `GET /planner/latest`: Fetches active user plan with nested 7-day items.
   - `GET /planner/history`: Returns historical workout plans for the user.

7. **Interactive Next.js Frontend (`/planner`)**:
   - Provides tabbed navigation between "Gym Recommender" (displaying suitability badges, rating stars, amenity tags, and match reasons) and "Weekly Workout Planner" (interactive 7-day schedule grid with exercise details, warmup badges, and adaptation alerts).

---

### Database Schema

#### 1. `gyms` Table
| Field Name | Type | Description |
| :--- | :--- | :--- |
| `id` | `INTEGER` | Primary Key |
| `name` | `VARCHAR(150)` | Gym name |
| `location` | `VARCHAR(255)` | Address / area location |
| `latitude` | `FLOAT` | Geolocation latitude |
| `longitude` | `FLOAT` | Geolocation longitude |
| `distance_km` | `FLOAT` | Distance from user in kilometers |
| `equipment_available`| `TEXT (JSON)` | JSON array of available equipment |
| `amenities` | `TEXT (JSON)` | JSON array of specialized amenities |
| `price_tier` | `VARCHAR(20)` | Price tier: `"$"` to `"$$$$"` |
| `rating` | `FLOAT` | User rating `[1.0, 5.0]` |
| `opening_hours` | `VARCHAR(100)` | Hours of operation |
| `description` | `TEXT` | Facility description |
| `created_at` | `TIMESTAMP` | Record creation timestamp |

#### 2. `workout_plans` Table
| Field Name | Type | Description |
| :--- | :--- | :--- |
| `id` | `INTEGER` | Primary Key |
| `user_id` | `INTEGER` | Foreign key referencing `users.id` (`ON DELETE CASCADE`) |
| `plan_name` | `VARCHAR(150)` | Name of generated plan |
| `fitness_goal` | `VARCHAR(50)` | Fitness goal (`hypertrophy`, `strength`, etc.) |
| `target_split` | `VARCHAR(50)` | Split structure (e.g. `Push/Pull/Legs`) |
| `days_per_week` | `INTEGER` | Total active training days per week |
| `habit_adapted` | `BOOLEAN` | Flag indicating Phase 6 skip risk adaptation |
| `performance_adapted`| `BOOLEAN` | Flag indicating Phase 3 form warning adaptation |
| `adaptation_notes` | `TEXT` | Summary of applied cross-module adaptations |
| `created_at` | `TIMESTAMP` | Record creation timestamp |

#### 3. `workout_plan_items` Table
| Field Name | Type | Description |
| :--- | :--- | :--- |
| `id` | `INTEGER` | Primary Key |
| `plan_id` | `INTEGER` | Foreign key referencing `workout_plans.id` (`ON DELETE CASCADE`) |
| `day_number` | `INTEGER` | Day of week `[1, 7]` |
| `day_name` | `VARCHAR(30)` | Day label (`Monday` .. `Sunday`) |
| `is_rest_day` | `BOOLEAN` | Flag for rest/recovery day |
| `target_muscle_groups`| `VARCHAR(255)`| Targeted muscle groups for the day |
| `exercises` | `TEXT (JSON)` | JSON array of exercise items (name, sets, reps, notes) |
| `warmup_notes` | `TEXT` | Posture/warmup notes derived from Phase 3 form warnings |

---

### Numerical Suitability Scoring Algorithm

The `GymRecommenderService` computes suitability score $S \in [0, 100]$ using a weighted multi-factor formula:

$$S = S_{\text{goal}} + S_{\text{equipment}} + S_{\text{proximity}} + S_{\text{rating}}$$

1. **Goal Alignment Score ($S_{\text{goal}}$, max 40 pts)**:
   - Evaluates gym equipment/amenity overlap with user's `fitness_goal`. For example, `hypertrophy` awards max points for Barbells, Dumbbells, Cable Machines, and Squat Racks.
2. **Equipment & Amenity Score ($S_{\text{equipment}}$, max 30 pts)**:
   - Checks presence of heavy free weights, cardio decks, turf zones, pool/sauna, or group fitness rooms.
3. **Proximity Score ($S_{\text{proximity}}$, max 20 pts)**:
   - Proximity bonus: $20 - \min(20, \text{distance\_km} \times 2)$.
4. **Rating Bonus ($S_{\text{rating}}$, max 10 pts)**:
   - Score bonus based on rating: $(\text{rating} / 5.0) \times 10$.

The final calculated score is clamped between $0\%$ and $100\%$.

---

### API Specifications

#### 1. `GET /gyms/recommendations`
- **Auth**: Bearer JWT (`get_current_user`)
- **Response**:
```json
{
  "user_id": 1,
  "user_goal": "hypertrophy",
  "total_gyms_found": 8,
  "recommendations": [
    {
      "id": 1,
      "name": "Iron Vault Power Gym",
      "location": "104 Metro Blvd, Downtown",
      "distance_km": 1.8,
      "price_tier": "$$",
      "rating": 4.9,
      "suitability_score": 95.0,
      "suitability_tier": "High Suitability Match",
      "match_reasons": [
        "Equipped with heavy barbells, power racks, and specialized platforms for hypertrophy goals",
        "Convenient location 1.8 km from your preferred training zone"
      ],
      "equipment_available": ["Barbells", "Dumbbells", "Power Racks", "Cable Machines"],
      "amenities": ["Sauna", "Locker Rooms", "Personal Training"]
    }
  ]
}
```

#### 2. `POST /planner/generate`
- **Auth**: Bearer JWT (`get_current_user`)
- **Request Body (Optional)**:
```json
{
  "fitness_goal": "hypertrophy",
  "preferred_days": 5
}
```
- **Response**:
```json
{
  "id": 12,
  "user_id": 1,
  "plan_name": "7-Day Hypertrophy Plan",
  "fitness_goal": "hypertrophy",
  "target_split": "Push / Pull / Legs Split",
  "days_per_week": 5,
  "habit_adapted": false,
  "performance_adapted": true,
  "adaptation_notes": "Adapted for Phase 3 posture form warnings (injected posture cues & warmup notes).",
  "items": [
    {
      "id": 85,
      "day_number": 1,
      "day_name": "Monday",
      "is_rest_day": false,
      "target_muscle_groups": "Chest, Shoulders, Triceps",
      "exercises": [
        {"name": "Barbell Bench Press", "sets": 4, "reps": "8-10", "notes": "Focus on controlled eccentric phase"}
      ],
      "warmup_notes": "Warmup & Technique Cue: Maintain knees aligned over toes and keep chest upright to correct prior form warnings."
    }
  ],
  "created_at": "2026-09-23T22:00:00"
}
```

---

### Automated Verification Results

- **Dedicated Phase 7 Test Suite (`backend/test_phase_7_planner.py`)**: 20/20 PASSED (`0.46s`).
- **Phase 1–6 Regression Suite**: 91/91 PASSED.
- **Frontend Build Verification (`npm run build`)**: 14/14 static pages generated cleanly with 0 TypeScript compilation errors.
