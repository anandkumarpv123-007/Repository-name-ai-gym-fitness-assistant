# AI GYM & FITNESS ASSISTANT
## PHASE 4 MASTER IMPLEMENTATION & LEARNING GUIDE
### Nutrition Engine, Food Tracking & AI Dietician Intelligence

---

## 1. Phase 4 Purpose

The purpose of **Phase 4 — Nutrition + AI Dietician** is to provide the nutritional foundation for the AI Gym & Fitness Assistant. 

In fitness, physical training in the gym represents only a fraction of an athlete's physical adaptation. Resistance training breaks down muscle fibers and expends energy; nutrition provides the raw biological building blocks (amino acids, fatty acids, glucose, micronutrients, and water) needed for muscle protein synthesis, glycogen replenishment, hormonal regulation, and systemic recovery.

Phase 4 bridges the gap between biomechanical workout tracking (Phases 2 and 3) and metabolic energy management. It enables users to:
1. Compute their scientific metabolic baseline (BMI, BMR, TDEE) deterministically.
2. Establish customized daily caloric, macronutrient, and hydration targets aligned with their specific fitness goals.
3. Log daily food items from an authoritative USDA-backed food catalogue or custom entries.
4. Monitor intra-day caloric balances and longitudinal 7-day adherence.
5. Generate structured, goal-aligned daily meal plans and categorized grocery lists powered by an AI Dietician with resilient deterministic fallbacks.

---

## 2. What Problem This Module Solves

### The Problem in Modern Fitness Apps
Most commercial fitness apps suffer from three fatal flaws:
1. **The Black-Box Arithmetic Problem:** Apps often use arbitrary, unexplained numbers for calorie targets without disclosing the underlying formulas.
2. **The LLM Hallucination Trap:** Many modern "AI nutrition apps" ask a Large Language Model (LLM) to calculate macronutrients. LLMs are probabilistic token predictors, not mathematical calculation engines. They frequently output impossible arithmetic (e.g., claiming 100g of protein and 50g of fat equals 400 calories, when it actually equals $100 \times 4 + 50 \times 9 = 850$ calories).
3. **The Unsafe Advice Problem:** Naive AI apps can recommend dangerous starvation diets (e.g., 500 kcal/day) or hazardous supplements to users without medical disclaimers or caloric safety floors.

### The Solution in AI Gym & Fitness Assistant
Our system solves these issues through a **Hybrid Deterministic-Generative Architecture**:
- **Deterministic Mathematics (100% Reliable):** All metabolic math (BMI, BMR via Mifflin-St Jeor, TDEE, caloric targets, macro distributions, and water needs) is computed using rigorous, reproducible formulas in Python. The LLM is never allowed to do math.
- **Generative Composition (Creative & Contextual):** The LLM is used strictly for what it excels at: culinary meal composition, flavour pairing, recipe ideas, and natural language instructions that fit within pre-calculated mathematical macro budgets.
- **Fail-Safe Fallback:** If the LLM times out, fails, or produces malformed JSON, a built-in deterministic expert dietician engine immediately takes over without user disruption.
- **Safety Floors:** Hard limits prevent dangerous crash diets (caloric targets below 800 kcal are strictly rejected or floored).

---

## 3. Complete Architecture

The architecture of Phase 4 spans five distinct tiers:

```
+-----------------------------------------------------------------------------------+
| 1. PRESENTATION LAYER (Next.js 16 + React 19 + Tailwind CSS)                       |
| - Route: /nutrition                                                               |
| - Dynamic KPI Cards: Calorie Progress Bar, Macro Rings, Hydration Gauge           |
| - Interactive Food Logging Form + Searchable USDA Catalogue Modal                 |
| - Longitudinal 7-Day Performance & Macro Sparkline View                          |
| - AI Dietician Plan Generator with Categorized Grocery Checklist                  |
+-----------------------------------------------------------------------------------+
                                         |
                                         | REST Calls (Bearer JWT in Authorization Header)
                                         v
+-----------------------------------------------------------------------------------+
| 2. API ROUTER LAYER (backend/routers/nutrition.py)                                 |
| - Prefix: /diet                                                                   |
| - Endpoints: /bmi, /target, /foods, /log, /logs, /summary, /weekly, /plan         |
| - Pydantic Request Validation & HTTP 422 Strict Boundary Enforcement              |
| - JWT Extraction & Strict Cross-User Data Isolation Check                         |
+-----------------------------------------------------------------------------------+
                                         |
                    +--------------------+--------------------+
                    |                                         |
                    v                                         v
+---------------------------------------+ +-----------------------------------------+
| 3A. NUTRITION ENGINE SERVICE          | | 3B. AI DIETICIAN SERVICE                |
| (backend/services/nutrition_service)  | | (backend/services/dietician_service)    |
| - Deterministic Math: BMI, BMR, TDEE  | | - Structured LLM Prompt Engineering     |
| - Macro Split Logic (Keto/High-Prot)  | | - External LLM Call (Gemini / OpenAI)   |
| - USDA Food Catalogue (22 items)      | | - Pydantic Schema Output Validation     |
| - Daily & Weekly Aggregation Engines  | | - Deterministic Expert Fallback Engine  |
| - Safe Metabolic Bounds (>=800 kcal)  | | - Categorized Grocery List Generator    |
+---------------------------------------+ +-----------------------------------------+
                    |                                         |
                    +--------------------+--------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| 4. PERSISTENCE LAYER (PostgreSQL + SQLAlchemy 2.0 ORM)                            |
| - Table: nutrition_targets (User caloric/macro/water targets + preferences)       |
| - Table: nutrition_logs (Granular per-meal food items, grams, and macros)         |
| - Table: diet_plans (Generated daily meal plans and grocery lists stored as JSON) |
+-----------------------------------------------------------------------------------+
```

---

## 4. End-to-End Data Flow

Let us trace what happens when an athlete interacts with the nutrition module:

```
[User Profile / Custom Input]
          |
          v
[1. Metabolic Formulas] ---> BMR (Mifflin-St Jeor) ---> TDEE (Activity Multiplier)
                                                                 |
                                                                 v
                                                      [Goal & Deficit/Surplus]
                                                                 |
                                                                 v
                                                     [2. Calorie & Macro Targets]
                                                                 |
               +-------------------------------------------------+-----------------------------------+
               |                                                                                     |
               v                                                                                     v
     [Daily Food Logging]                                                                  [AI Dietician Planning]
               |                                                                                     |
               v                                                                                     v
  [Search USDA Catalogue or Custom]                                                       [LLM Prompt with Fixed Targets]
               |                                                                                     |
               v                                                                                     v
  [Persist to nutrition_logs]                                                            [JSON Schema Response or Fallback]
               |                                                                                     |
               v                                                                                     v
  [Compute Daily & Weekly Summaries]                                                      [Persist Plan to diet_plans]
               |                                                                                     |
               v                                                                                     v
  [GET /diet/summary & /diet/weekly]                                                      [Categorized Grocery Checklist]
               |                                                                                     |
               +-------------------------------------------------+-----------------------------------+
                                                                 |
                                                                 v
                                                [Render on /nutrition Frontend UI]
```

---

## 5. Nutrition Profile and Inputs

A user's nutritional baseline is derived from their biological and lifestyle attributes stored in their `Profile` record:

| Input Parameter | Technical Meaning | Valid Range | Default Value | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `height_cm` | Stature in centimeters | $50.0 - 260.0$ cm | $175.0$ cm | Needed for BMI and BMR body surface area estimation |
| `weight_kg` | Total body mass in kilograms | $20.0 - 350.0$ kg | $70.0$ kg | Key determinant of energy expenditure and protein needs |
| `age` | Age in completed years | $10 - 120$ years | $25$ years | Accounts for age-related metabolic rate slowdown |
| `gender` | Biological sex | `male`, `female`, `neutral` | `neutral` | Selects sex-specific BMR constant ($+5$, $-161$, or $-78$) |
| `activity_level` | Physical activity factor | `sedentary`, `light`, `moderate`, `very_active`, `extra_active` | `moderate` | Multiplier for non-resting energy expenditure |
| `fitness_goal` | Target outcome | `fat_loss`, `muscle_gain`, `maintenance`, `endurance` | `maintenance` | Determines caloric surplus or deficit and protein ratio |
| `dietary_preference`| Dietary constraint | `standard`, `vegetarian`, `vegan`, `keto`, `high_protein` | `standard` | Governs macronutrient ratios and ingredient filters |

---

## 6. BMI (Body Mass Index) Calculation

### What It Is
Body Mass Index (BMI) is a standardized screening metric defined by the World Health Organization (WHO) that quantifies body mass relative to height squared.

### Why We Need It
It provides an immediate high-level assessment of whether an individual's weight poses health risks and establishes a healthy target weight range ($18.5 \le \text{BMI} < 25.0$).

### Mathematical Formula
$$\text{BMI} = \frac{\text{weight\_kg}}{(\text{height\_m})^2} = \frac{\text{weight\_kg}}{(\text{height\_cm} / 100)^2}$$

### WHO Category Classification
- **Underweight:** $\text{BMI} < 18.5$
- **Normal weight:** $18.5 \le \text{BMI} < 25.0$
- **Overweight:** $25.0 \le \text{BMI} < 30.0$
- **Obese:** $\text{BMI} \ge 30.0$

### Healthy Weight Boundary Formulas
$$\text{Healthy Weight Min (kg)} = 18.5 \times \left(\frac{\text{height\_cm}}{100}\right)^2$$
$$\text{Healthy Weight Max (kg)} = 24.9 \times \left(\frac{\text{height\_cm}}{100}\right)^2$$

### Concrete Example
- **User:** Anand (Height: $175\text{ cm}$, Weight: $70\text{ kg}$)
- **Calculation:**
  $$\text{Height in meters} = 1.75\text{ m}$$
  $$\text{BMI} = \frac{70}{1.75^2} = \frac{70}{3.0625} = 22.857 \rightarrow \mathbf{22.9}$$
- **Result:** Category: **"Normal weight"**; Healthy weight range: **$56.7\text{ kg} - 76.3\text{ kg}$**.

---

## 7. BMR (Basal Metabolic Rate) Calculation

### What It Is
Basal Metabolic Rate (BMR) is the minimum amount of energy (in kilocalories per day) expended by the human body at rest in a neutrally temperate environment while the digestive system is inactive. It powers vital autonomic functions: respiration, circulation, cellular repair, and brain activity.

### Why We Need It
BMR serves as the absolute baseline floor of human energy consumption. It is impossible to accurately formulate a diet plan without knowing this resting caloric expenditure.

### Formula: The Mifflin-St Jeor Equation
Clinical nutritional literature establishes the **Mifflin-St Jeor equation** as the most accurate predictive formula for healthy adults:

$$\text{BMR} = 10 \times \text{weight\_kg} + 6.25 \times \text{height\_cm} - 5 \times \text{age} + s$$

Where the sex offset factor $s$ is:
- **Male:** $s = +5$
- **Female:** $s = -161$
- **Neutral / Unspecified:** $s = -78$ (average of male and female constants)

### Concrete Example
- **User:** Male, Age: 25, Height: $175\text{ cm}$, Weight: $70\text{ kg}$
- **Step-by-Step Calculation:**
  $$10 \times 70 = 700$$
  $$6.25 \times 175 = 1093.75$$
  $$-5 \times 25 = -125$$
  $$+5 = 5$$
  $$\text{BMR} = 700 + 1093.75 - 125 + 5 = 1673.75 \rightarrow \mathbf{1673.8\text{ kcal/day}}$$

---

## 8. TDEE (Total Daily Energy Expenditure) Calculation

### What It Is
Total Daily Energy Expenditure (TDEE) is the total number of kilocalories burned in a 24-hour period, accounting for BMR plus the thermic effect of food (TEF), non-exercise activity thermogenesis (NEAT), and exercise activity thermogenesis (EAT).

### Why We Need It
TDEE defines **maintenance calories**—the exact energy intake where an individual neither gains nor loses body mass.

### Mathematical Formula
$$\text{TDEE} = \text{BMR} \times \text{Activity Multiplier}$$

### Activity Multipliers
| Activity Level | Multiplier | Physical Description |
| :--- | :---: | :--- |
| `sedentary` | $1.20$ | Desk job, little to no structured exercise |
| `light` | $1.375$ | Light exercise 1–3 days per week |
| `moderate` | $1.55$ | Moderate exercise 3–5 days per week |
| `very_active` | $1.725$ | Hard exercise 6–7 days per week |
| `extra_active` | $1.90$ | Very intense physical training, manual labour, or 2x daily workouts |

### Concrete Example
- **User:** BMR = $1673.8\text{ kcal}$, Activity Level: `moderate` ($1.55$)
- **Calculation:**
  $$\text{TDEE} = 1673.75 \times 1.55 = 2594.31 \rightarrow \mathbf{2594.3\text{ kcal/day}}$$

---

## 9. Calorie Target Calculation by Fitness Goal

### What It Is
The adjustment of maintenance calories (TDEE) into a targeted daily intake based on whether the athlete desires fat loss, muscle hypertrophy, athletic conditioning, or weight maintenance.

### Mathematical Rules & Energy Balances

1. **Fat Loss (`fat_loss`, `cutting`):**
   - Applies a scientific **20% caloric deficit**:
     $$\text{Calories Target} = \text{round}(\max(\text{TDEE} \times 0.80, \, \text{Floor}), 0)$$
   - **Safe Metabolic Floor:**
     - Female: $1200.0\text{ kcal}$
     - Male / Neutral: $1500.0\text{ kcal}$
   - *Why the floor exists:* Caloric intake below these thresholds triggers metabolic adaptation, endocrine suppression (thyroid and sex hormones), muscle catabolism, and severe micronutrient deficiencies.

2. **Muscle Gain (`muscle_gain`, `bulking`):**
   - Applies a **10% caloric surplus**:
     $$\text{Calories Target} = \text{round}(\text{TDEE} \times 1.10, 0)$$
   - *Why 10%:* A modest surplus provides adequate energy for muscle tissue synthesis while minimizing unwanted adipose tissue (fat) accumulation.

3. **Endurance / Athletic Conditioning (`endurance`):**
   - Applies a **5% caloric surplus**:
     $$\text{Calories Target} = \text{round}(\text{TDEE} \times 1.05, 0)$$

4. **Maintenance (`maintenance`):**
   - Exact TDEE energy balance:
     $$\text{Calories Target} = \text{round}(\text{TDEE}, 0)$$

### Concrete Example
- Anand with TDEE = $2594.3\text{ kcal}$ selecting `fat_loss`:
  $$\text{Target} = 2594.3 \times 0.80 = 2075.44 \rightarrow \mathbf{2075.0\text{ kcal/day}}$$

---

## 10. Macronutrient Calculation

Every single macronutrient has a specific caloric density:
- **Protein:** $4\text{ kcal per gram}$
- **Carbohydrates:** $4\text{ kcal per gram}$
- **Fat:** $9\text{ kcal per gram}$

Our project supports three distinct allocation strategies:

### Strategy 1: Keto Allocation (`dietary_preference == "keto"`)
- **Fat (70% of energy):** $\text{Fat (g)} = \text{round}\left(\frac{\text{Calories Target} \times 0.70}{9.0}, 1\right)$
- **Protein (25% of energy):** $\text{Protein (g)} = \text{round}\left(\frac{\text{Calories Target} \times 0.25}{4.0}, 1\right)$
- **Carbs (5% of energy):** $\text{Carbs (g)} = \text{round}\left(\frac{\text{Calories Target} \times 0.05}{4.0}, 1\right)$

### Strategy 2: High-Protein Allocation (`dietary_preference == "high_protein"`)
- **Protein (35% of energy):** $\text{Protein (g)} = \text{round}\left(\frac{\text{Calories Target} \times 0.35}{4.0}, 1\right)$
- **Carbs (40% of energy):** $\text{Carbs (g)} = \text{round}\left(\frac{\text{Calories Target} \times 0.40}{4.0}, 1\right)$
- **Fat (25% of energy):** $\text{Fat (g)} = \text{round}\left(\frac{\text{Calories Target} \times 0.25}{9.0}, 1\right)$

### Strategy 3: Standard Goal-Specific Allocation (Default)
1. **Protein Allocation (Based on Lean Mass Protection):**
   - Fat Loss: $2.0\text{ g/kg}$
   - Muscle Gain: $2.2\text{ g/kg}$
   - Endurance: $1.8\text{ g/kg}$
   - Maintenance: $1.6\text{ g/kg}$
   - Capped at maximum 35% of total caloric intake to prevent renal strain:
     $$\text{Target Protein Cals} = \min(\text{protein\_per\_kg} \times \text{weight\_kg} \times 4.0, \, \text{Calories Target} \times 0.35)$$
     $$\text{Protein (g)} = \text{round}\left(\frac{\text{Target Protein Cals}}{4.0}, 1\right)$$

2. **Fat Allocation (Essential Endocrine Floor):**
   - 25% of total energy is dedicated to healthy fats for cell membrane integrity and hormone production:
     $$\text{Fat (g)} = \text{round}\left(\frac{\text{Calories Target} \times 0.25}{9.0}, 1\right)$$

3. **Carbohydrate Allocation (Remaining Caloric Budget):**
   - Fills the remaining energetic budget to support glycogen replenishment and high-intensity workouts:
     $$\text{Remaining Cals} = \max(0.0, \, \text{Calories Target} - (\text{Protein (g)} \times 4.0 + \text{Fat (g)} \times 9.0))$$
     $$\text{Carbs (g)} = \text{round}\left(\frac{\text{Remaining Cals}}{4.0}, 1\right)$$

---

## 11. Hydration Calculation

### What It Is
The determination of optimal daily fluid intake (in liters).

### Formula
Based on clinical hydration heuristics ($35\text{ ml}$ per kilogram of body weight):
$$\text{Water (Liters)} = \text{round}(\text{clamp}(2.0, \, \text{weight\_kg} \times 0.035, \, 5.0), 1)$$

- Clamped with a safe minimum floor of $2.0\text{ L}$ (preventing dehydration) and an upper cap of $5.0\text{ L}$ (preventing water intoxication/hyponatremia).
- For a $70\text{ kg}$ individual: $70 \times 0.035 = 2.45 \rightarrow \mathbf{2.5\text{ Liters/day}}$.

---

## 12. Food Catalogue & USDA FoodData Central Integration

### What It Is
A built-in verified database of 22 staple fitness foods covering protein, carbohydrates, healthy fats, fruits, and vegetables.

### Authority Citation
Every entry in our catalogue is cited directly from **USDA FoodData Central (FDC)** (the authoritative United States Department of Agriculture nutritional reference). All nutritional metrics are normalized on a uniform **per-100g** basis.

### The Standard Catalogue
1. **Whole Egg (Large)** — FDC `171287` ($143\text{ kcal}$, $12.6\text{g P}$, $0.7\text{g C}$, $9.5\text{g F}$)
2. **Egg Whites** — FDC `172183` ($52\text{ kcal}$, $11.0\text{g P}$, $0.7\text{g C}$, $0.2\text{g F}$)
3. **Chicken Breast (Boneless/Skinless)** — FDC `171077` ($165\text{ kcal}$, $31.0\text{g P}$, $0.0\text{g C}$, $3.6\text{g F}$)
4. **Salmon Fillet** — FDC `175167` ($208\text{ kcal}$, $20.0\text{g P}$, $0.0\text{g C}$, $13.0\text{g F}$)
5. **Paneer (Cottage Cheese)** — FDC `2259685` ($296\text{ kcal}$, $18.0\text{g P}$, $4.5\text{g C}$, $22.0\text{g F}$)
6. **Firm Tofu** — FDC `172448` ($144\text{ kcal}$, $17.3\text{g P}$, $2.8\text{g C}$, $8.7\text{g F}$)
7. **Whey Protein Isolate** — FDC `2115385` ($370\text{ kcal}$, $80.0\text{g P}$, $3.0\text{g C}$, $2.5\text{g F}$)
8. **Greek Yogurt (Non-fat)** — FDC `170903` ($59\text{ kcal}$, $10.0\text{g P}$, $3.6\text{g C}$, $0.4\text{g F}$)
9. **Cooked Brown Rice** — FDC `169704` ($111\text{ kcal}$, $2.6\text{g P}$, $23.0\text{g C}$, $0.9\text{g F}$)
10. **Cooked White Rice** — FDC `169756` ($130\text{ kcal}$, $2.7\text{g P}$, $28.0\text{g C}$, $0.3\text{g F}$)
11. **Rolled Oats (Raw)** — FDC `169747` ($389\text{ kcal}$, $16.9\text{g P}$, $66.3\text{g C}$, $6.9\text{g F}$)
12. **Whole Wheat Bread** — FDC `172688` ($247\text{ kcal}$, $13.0\text{g P}$, $41.0\text{g C}$, $3.4\text{g F}$)
13. **Sweet Potato (Baked)** — FDC `168483` ($90\text{ kcal}$, $2.0\text{g P}$, $20.7\text{g C}$, $0.1\text{g F}$)
14. **Quinoa (Cooked)** — FDC `168917` ($120\text{ kcal}$, $4.4\text{g P}$, $21.3\text{g C}$, $1.9\text{g F}$)
15. **Broccoli (Raw/Steamed)** — FDC `170379` ($34\text{ kcal}$, $2.8\text{g P}$, $6.6\text{g C}$, $0.4\text{g F}$)
16. **Spinach (Raw)** — FDC `168462` ($23\text{ kcal}$, $2.9\text{g P}$, $3.6\text{g C}$, $0.4\text{g F}$)
17. **Banana (Raw)** — FDC `173944` ($89\text{ kcal}$, $1.1\text{g P}$, $22.8\text{g C}$, $0.3\text{g F}$)
18. **Apple (Raw with skin)** — FDC `171688` ($52\text{ kcal}$, $0.3\text{g P}$, $13.8\text{g C}$, $0.2\text{g F}$)
19. **Almonds (Raw)** — FDC `170567` ($579\text{ kcal}$, $21.2\text{g P}$, $21.6\text{g C}$, $49.9\text{g F}$)
20. **Peanut Butter (Natural)** — FDC `174266` ($588\text{ kcal}$, $25.1\text{g P}$, $20.0\text{g C}$, $50.4\text{g F}$)
21. **Olive Oil (Extra Virgin)** — FDC `171413` ($884\text{ kcal}$, $0.0\text{g P}$, $0.0\text{g C}$, $100.0\text{g F}$)
22. **Avocado (Fresh)** — FDC `171705` ($160\text{ kcal}$, $2.0\text{g P}$, $8.5\text{g C}$, $14.7\text{g F}$)

---

## 13. Food Logging Mechanics

### What It Is
The creation of granular meal intake records for the authenticated user.

### How It Works
When a user eats a meal, they post a payload to `POST /diet/log`:
```json
{
  "food_name": "Grilled Chicken Breast",
  "quantity": 150.0,
  "unit": "g",
  "meal_type": "lunch",
  "calories": 247.5,
  "protein": 46.5,
  "carbs": 0.0,
  "fat": 5.4,
  "log_date": "2026-09-21"
}
```
1. **Validation:** Pydantic verifies that `quantity > 0` and $\le 5000\text{ g}$, `calories` $\le 5000\text{ kcal}$, and macros $\le 500\text{ g}$.
2. **Persistence:** SQLAlchemy inserts a new row into `nutrition_logs` bound strictly to `current_user.id`.
3. **Deletion:** Individual records can be deleted via `DELETE /diet/log/{log_id}` with strict verification that `log.user_id == current_user.id`.

---

## 14. Daily Nutrition Aggregation Engine

### What It Is
A calculation engine that sums all food logs for a specified calendar date (defaulting to today), compares them against the user's active `NutritionTarget`, and calculates adherence metrics.

### Computed Metrics
- **Totals:** $\sum \text{calories}$, $\sum \text{protein}$, $\sum \text{carbs}$, $\sum \text{fat}$
- **Percentages:** $\frac{\sum \text{calories}}{\text{target\_calories}} \times 100\%$
- **Remaining Budget:** $\text{target\_calories} - \sum \text{calories}$
- **Status Classification:**
  - `on_track`: Caloric consumption is between $85\%$ and $110\%$ of target.
  - `under_target`: Caloric consumption is $< 85\%$ of target.
  - `over_target`: Caloric consumption is $> 110\%$ of target.
- **Meal Breakdown:** Groups logged items into structured sub-lists: `breakfast`, `lunch`, `dinner`, and `snack`.

---

## 15. Weekly Nutrition Aggregation Engine

### What It Is
A longitudinal intelligence engine that evaluates 7 days (or any custom window up to 365 days) of dietary logs to monitor consistency and trend compliance.

### How It Works (`GET /diet/weekly?days=7`)
1. Filters `nutrition_logs` between `today - 6 days` and `today` for the authenticated user.
2. Groups logs by date.
3. Computes:
   - `total_calories`, `total_protein`, `total_carbs`, `total_fat` across the week.
   - `daily_average_calories`, `daily_average_protein`, `daily_average_carbs`, `daily_average_fat`.
   - `days_logged`: Count of unique days where the user recorded food.
   - `calorie_compliance_percentage`: $\frac{\text{daily\_average\_calories}}{\text{target\_calories}} \times 100\%$.
   - `daily_history`: An ordered list of 7 `DailyMacroPoint` points (date, calories, protein, carbs, fat, log count) suitable for plotting sparklines on the frontend.

---

## 16. PostgreSQL Database Tables & Relationships

Phase 4 introduces three dedicated relational tables in PostgreSQL:

```
                +------------------------+
                |         users          |
                +------------------------+
                | id (PK)                |
                +------------------------+
                  |         |          |
      1:1 (Cascade) |         | 1:N (Cascade)
                  |         |          |
                  v         |          v
+-----------------------+   |    +-----------------------+
|   nutrition_targets   |   |    |      diet_plans       |
+-----------------------+   |    +-----------------------+
| id (PK)               |   |    | id (PK)               |
| user_id (FK -> users) |   |    | user_id (FK -> users) |
| calories_target       |   |    | calories_target       |
| protein_grams         |   |    | dietary_preference    |
| carbs_grams           |   |    | goal                  |
| fat_grams             |   |    | plan_json (JSON TEXT) |
| water_liters          |   |    | grocery_list_json     |
| dietary_preference    |   |    | provider              |
| meals_per_day         |   |    | created_at            |
| updated_at            |   |    +-----------------------+
+-----------------------+   |
                            v 1:N (Cascade)
                +-----------------------+
                |    nutrition_logs     |
                +-----------------------+
                | id (PK)               |
                | user_id (FK -> users) |
                | log_date (DATE)       |
                | meal_type (VARCHAR)   |
                | food_name (VARCHAR)   |
                | quantity (FLOAT)      |
                | unit (VARCHAR)        |
                | calories (FLOAT)      |
                | protein (FLOAT)       |
                | carbs (FLOAT)         |
                | fat (FLOAT)           |
                | created_at            |
                +-----------------------+
```

### Table 1: `nutrition_targets`
- Primary Key: `id` (Integer).
- Foreign Key: `user_id` referencing `users.id` (`ondelete="CASCADE"`, `unique=True`).
- Stores the active nutritional blueprint for each user.

### Table 2: `nutrition_logs`
- Primary Key: `id` (Integer).
- Foreign Key: `user_id` referencing `users.id` (`ondelete="CASCADE"`, indexed).
- Index on `(user_id, log_date)` for high-speed chronological querying.

### Table 3: `diet_plans`
- Primary Key: `id` (Integer).
- Foreign Key: `user_id` referencing `users.id` (`ondelete="CASCADE"`).
- `plan_json`: Serialized JSON storing the complete meal structure.
- `grocery_list_json`: Serialized JSON storing categorized shopping items.
- `provider`: Records which engine generated the plan (`llm_gemini`, `llm_openai`, or `deterministic_expert`).

---

## 17. FastAPI Endpoints Reference

All endpoints reside under the `/diet` prefix in [`backend/routers/nutrition.py`](file:///C:/Users/anand/AI-Gym-Fitness-Assistant/backend/routers/nutrition.py):

| Method | Endpoint | Auth Required | Request Body / Query Params | Response Schema | Purpose |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `GET` | `/diet/bmi` | Yes | None | `BMIResponse` | Calculate BMI/BMR/TDEE from user profile |
| `POST`| `/diet/bmi` | No | `BMICalculateRequest` | `BMIResponse` | Public calculation endpoint for guest users |
| `GET` | `/diet/target` | Yes | None | `NutritionTargetResponse` | Fetch or auto-initialize user targets |
| `PUT` | `/diet/target` | Yes | `NutritionTargetUpdateRequest` | `NutritionTargetResponse` | Manually update calorie/macro targets |
| `GET` | `/diet/foods` | No | `?search=str` | `List[FoodCatalogueItem]` | Query USDA food catalogue |
| `POST`| `/diet/log` | Yes | `FoodLogCreateRequest` | `FoodLogResponse` | Log food item entry (HTTP 201) |
| `GET` | `/diet/logs` | Yes | `?date=YYYY-MM-DD` | `List[FoodLogResponse]` | Get all logs for a specific day |
| `DELETE`| `/diet/log/{id}` | Yes | None | `{"message": str}` | Delete a food log entry (ownership verified) |
| `GET` | `/diet/summary` | Yes | `?date=YYYY-MM-DD` | `DailyNutritionSummaryResponse`| Intra-day totals vs target percentages |
| `GET` | `/diet/weekly` | Yes | `?days=int` | `WeeklyNutritionSummaryResponse` | 7-day longitudinal compliance analytics |
| `POST`| `/diet/plan` | Yes | `DietPlanCreateRequest` | `DietPlanResponse` | Generate AI/expert meal plan & grocery list |
| `GET` | `/diet/plan/latest` | Yes | None | `DietPlanResponse` | Retrieve the latest active generated plan |

---

## 18. Pydantic Schemas Reference

All request and response models are strongly typed in [`backend/schemas/nutrition.py`](file:///C:/Users/anand/AI-Gym-Fitness-Assistant/backend/schemas/nutrition.py):
1. **`BMICalculateRequest` / `BMIResponse`**: Height, weight, age, sex, BMI, WHO category, BMR, TDEE, recommended macros.
2. **`NutritionTargetUpdateRequest` / `NutritionTargetResponse`**: User targets for calories, protein, carbs, fat, water, and meal count.
3. **`FoodCatalogueItem`**: Item name, category, serving size, calories, protein, carbs, fat, source authority (`USDA FoodData Central`), and `fdc_id`.
4. **`FoodLogCreateRequest` / `FoodLogResponse`**: Strict range validations (`quantity` $\le 5000$, `calories` $\le 5000$, `meal_type` validation).
5. **`DailyNutritionSummaryResponse`**: Consumed macros, remaining macros, percentage progress, meal breakdown dictionary.
6. **`WeeklyNutritionSummaryResponse`**: Start/end date, totals, daily averages, compliance status, and daily history points array.
7. **`DietPlanCreateRequest` / `DietPlanResponse`**: Structured meal plan, list of `MealPlanItem`, `GroceryCategory`, and mandatory medical disclaimer.

---

## 19. AI Dietician Architecture

The AI Dietician operates on the principle of **Guaranteed Architectural Boundary**:

```
+-----------------------------------------------------------------------------------+
|                        AI DIETICIAN INPUT BLUEPRINT                               |
| - Target Calories: 2150 kcal (Calculated by Python)                               |
| - Target Protein: 150g       (Calculated by Python)                               |
| - Target Carbs: 230g         (Calculated by Python)                               |
| - Target Fat: 65g            (Calculated by Python)                               |
| - Dietary Preference: High Protein                                                |
| - Allergies/Exclusions: Peanuts                                                   |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        STRICT JSON SCHEMA PROMPT                                  |
| Prompt explicitly specifies:                                                      |
| "Respond ONLY with valid raw JSON adhering to this exact schema without markdown: |
|  {"meals": [{"meal_type": "...", "items": [{"name": "...", ...}]}]}"               |
+-----------------------------------------------------------------------------------+
                                         |
                     +-------------------+-------------------+
                     |                                       |
                     v (API Key Present)                     v (No Key / Network Down)
+---------------------------------------+   +---------------------------------------+
|         EXTERNAL LLM CALL             |   |     DETERMINISTIC EXPERT ENGINE       |
| - Google Gemini (1.5 Flash)           |   | - Mathematical meal partitioning      |
| - or OpenAI (gpt-4o-mini)             |   | - Preference-specific food database   |
| - 10-second timeout                   |   | - Grams scaled to match calorie split |
+---------------------------------------+   +---------------------------------------+
                     |                                       |
                     | Response                              | Direct Output
                     v                                       v
+---------------------------------------+                    |
|      SCHEMA & SAFETY VALIDATION       |                    |
| - Is it valid JSON?                   |                    |
| - Does it contain 'meals' list?       |                    |
| - Does each meal have valid items?    |                    |
+---------------------------------------+                    |
          |                   |                              |
          | (Passed)          | (Failed / Malformed)         |
          v                   +----------------------------->+
+------------------------------------------------------------+
| Final Plan Assembly: Sum exact macros, generate grocery    |
| list, attach medical disclaimer, and persist to PostgreSQL |
+------------------------------------------------------------+
```

---

## 20. How the LLM Is Used

When an API key (`GEMINI_API_KEY` or `OPENAI_API_KEY`) is configured, the system engages the LLM:
1. **System Role:** Sets the context: *"You are an expert sports dietician. Always output pure valid JSON."*
2. **Context Injection:** Injects pre-calculated mathematical macro targets, user dietary preferences, allergies, and desired meal count.
3. **MIME Enforcement:** Gemini is called with `generationConfig: {"response_mime_type": "application/json"}`; OpenAI is called with `response_format: {"type": "json_object"}`.
4. **Task Scope:** The LLM's only job is to create creative, appetizing meal combinations, specify realistic portions, and write simple preparation instructions.

---

## 21. What the LLM Does NOT Do

In this system, the LLM is explicitly restricted:
1. **The LLM does NOT calculate BMR or TDEE:** Those are computed with 100% mathematical precision by Python using Mifflin-St Jeor.
2. **The LLM does NOT decide caloric deficits or surpluses:** Python determines the 20% deficit or 10% surplus deterministically.
3. **The LLM does NOT dictate macronutrient ratios:** Python determines the exact protein, carbohydrate, and fat grams.
4. **The LLM does NOT have authority over safety:** The backend enforces calorie floors ($800\text{ kcal}$) regardless of what prompt is submitted.
5. **The LLM does NOT control database persistence:** The backend validates and serializes the plan.

---

## 22. Deterministic Fallback Engine

### What It Is
An algorithmic dietician coded entirely in standard Python within [`DieticianService._generate_deterministic_meal_plan`](file:///C:/Users/anand/AI-Gym-Fitness-Assistant/backend/services/dietician_service.py).

### How It Works
If no LLM API key exists or an LLM call fails:
1. **Caloric Partitioning:** Splits daily calories and macros across meals based on count:
   - 3 meals: Breakfast ($30\%$), Lunch ($40\%$), Dinner ($30\%$).
   - 4 meals: Breakfast ($25\%$), Lunch ($35\%$), Dinner ($25\%$), Snack ($15\%$).
   - 5 meals: Breakfast ($20\%$), Snack 1 ($10\%$), Lunch ($35\%$), Snack 2 ($10\%$), Dinner ($25\%$).
2. **Curated Ingredient Selection:** Selects healthy, whole-food ingredients customized to the user's dietary preference (`vegan`, `vegetarian`, `keto`, `high_protein`, or `standard`).
3. **Proportional Macro Scaling:** Automatically scales ingredient portions to match the meal's exact caloric budget.

---

## 23. LLM Failure Handling & Resilience

The LLM call is wrapped in a strict `try ... except Exception` block in `DieticianService.generate_diet_plan`:
- Catches network timeouts (`urllib.error.URLError`, socket timeouts after 10s).
- Catches invalid HTTP responses (HTTP 401 unauthorized, HTTP 429 rate limit).
- Catches JSON decode errors (if the model outputs raw text or invalid JSON).
- Catches schema structural errors (if the returned JSON lacks a `"meals"` array).

When any of these errors occur:
- An informational log is recorded: `[AI Dietician] LLM call failed or unavailable. Falling back to deterministic expert engine.`
- The plan seamlessly switches to the deterministic expert engine (`provider = "deterministic_expert"`).
- The user experiences **zero downtime**, receiving their complete meal plan and grocery list instantly.

---

## 24. Structured LLM Output Validation

Raw LLM text is never trusted. The engine subjects LLM output to multi-stage verification:
1. **JSON Decoding:** `json.loads(text_content)` verifies valid syntax.
2. **Top-Level Type Check:** Asserts `isinstance(data, dict)` and `"meals" in data`.
3. **Array Validation:** Asserts `isinstance(data["meals"], list)` and `len(data["meals"]) > 0`.
4. **Meal Entity Integrity:** Loops through every meal dictionary, verifying that `"items" in meal`, `"meal_type" in meal`, and `"meal_name" in meal`.
5. **Macro Summation:** Rather than trusting the LLM's arithmetic, Python re-sums the individual item calories and macros to guarantee consistency.

---

## 25. Meal-Plan Generation Workflow

When `POST /diet/plan` is called:
1. Resolves the user's active targets from `NutritionTarget` or accepts custom override parameters.
2. Verifies that the calorie target is $\ge 800\text{ kcal}$ and $\le 8000\text{ kcal}$.
3. Calls the generative or deterministic meal planner.
4. Generates a categorized grocery list from the meals.
5. Injects the mandatory medical disclaimer.
6. Persists the complete plan to the `diet_plans` table in PostgreSQL.
7. Returns the `DietPlanResponse` object to the frontend.

---

## 26. Grocery-List Generation Engine

### What It Is
An automated classification algorithm that extracts every ingredient from the generated meal plan and organizes them into a categorized shopping checklist.

### Categories
1. **Protein:** Chicken, eggs, salmon, paneer, tofu, whey protein, turkey, tuna.
2. **Carbohydrates:** Brown rice, oats, whole wheat bread, quinoa, sweet potatoes.
3. **Vegetables:** Spinach, broccoli, cucumber, bell peppers, tomatoes, asparagus.
4. **Healthy Fats:** Almonds, walnuts, avocado, olive oil, chia seeds, peanut butter.
5. **Dairy & Alternatives:** Greek yogurt, milk, almond milk, soy milk.
6. **Pantry & Seasonings:** Sea salt, black pepper, cinnamon, garlic powder, cooking oil.

### De-duplication Logic
Uses a normalized lowercase dictionary and set-based tracking (`seen_items = set()`) to ensure the user does not see duplicate grocery items across multiple meals.

---

## 27. Authentication and User Isolation

As established in Phases 1 through 3, security and multi-tenant user isolation are enforced unconditionally:
1. **JWT Verification:** Protected endpoints declare `current_user: User = Depends(get_current_user)`.
2. **Database Isolation:** Every database query filters by `user_id == current_user.id`.
3. **Zero Cross-User Leakage:** A user cannot view or delete another user's food logs or diet plans. Attempting to access an unauthorized resource returns a `404 Not Found` or `401 Unauthorized`.
4. **Verified via Automated Tests:** Test `test_10` and `test_11` in `backend/test_phase_4_nutrition.py` verify that User B queries receive zero data from User A's logs or plans.

---

## 28. Frontend Nutrition Page (`/nutrition`)

The frontend is built using Next.js 16 (App Router), React 19, and Tailwind CSS at [`frontend/src/app/nutrition/page.tsx`](file:///C:/Users/anand/AI-Gym-Fitness-Assistant/frontend/src/app/nutrition/page.tsx):
- **Hero Dashboard:** Displays a dynamic caloric budget progress bar, remaining calorie badges, and status indicator (`On Track`, `Under Target`, `Over Target`).
- **Macronutrient Rings:** Visual progress bars for Protein, Carbohydrates, and Fat with exact gram counts and percentages.
- **Hydration Tracker:** Glassmorphic water tracking widget showing daily intake against target liters.
- **Searchable USDA Food Modal:** Allows the user to browse or search 22 verified staple foods with instant caloric previews.
- **Custom Food Logger:** Allows logging custom meals with automatic macro calculation.
- **Daily Food Log Accordion:** Groups consumed foods into Breakfast, Lunch, Dinner, and Snacks with one-click deletion.
- **Longitudinal 7-Day Chart:** Displays weekly consistency, average intake, and day-by-day macro bars.
- **AI Dietician Hub:** Allows generating personalized daily meal plans and reviewing interactive grocery checklists.

---

## 29. Frontend → API → Service → Database/LLM Request Lifecycle

Let us trace a single action: the user clicks **"Log 150g Chicken Breast"**:
1. **Frontend:** React executes an authenticated `fetch("http://localhost:8000/diet/log", { method: "POST", headers: { Authorization: "Bearer <token>" }, body: JSON.stringify(...) })`.
2. **FastAPI Router:** Receives HTTP request, executes `get_current_user` dependency (decoding JWT and validating user ID), and parses the body into `FoodLogCreateRequest`.
3. **Nutrition Service:** Calls `NutritionService.log_food(db, user_id, log_data)`.
4. **Validation:** Checks that `quantity > 0` and `calories >= 0`.
5. **PostgreSQL Database:** Executes `INSERT INTO nutrition_logs ... RETURNING id`.
6. **Response:** Returns `FoodLogResponse` (HTTP 201 Created).
7. **Frontend State:** React updates local state, recalculates progress rings, and updates remaining calories without requiring a page refresh.

---

## 30. Error Handling & Validation Matrix

| Layer | Potential Error | Handling Mechanism | HTTP Response |
| :--- | :--- | :--- | :---: |
| **Pydantic** | Negative quantity / calories | Field validation (`ge=0.0`, `gt=0.0`) | `422 Unprocessable Entity` |
| **Pydantic** | Unsafe starvation target ($< 800\text{ kcal}$) | Field validation (`ge=800.0`) | `422 Unprocessable Entity` |
| **Auth** | Missing or expired JWT token | `get_current_user` OAuth2 Bearer check | `401 Unauthorized` |
| **Service** | Deleting food log belonging to another user | Ownership filter (`user_id == current_user.id`) | `404 Not Found` |
| **External LLM**| Timeout / rate limit / bad JSON | `try ... except` fallback to deterministic engine | `200/201 OK` (Graceful fallback) |
| **Database** | User deletion | `ON DELETE CASCADE` cleans up all targets/logs | Database Integrity |

---

## 31. Safety Limitations & Medical Disclaimer

### Safety Guardrails
1. **Caloric Floors:** The system prevents crash diets by strictly rejecting calorie targets below $800\text{ kcal}$ at the schema layer and flooring programmatic inputs to $800\text{ kcal}$.
2. **Hydration Clamps:** Fluid intake targets are clamped between $2.0\text{ L}$ and $5.0\text{ L}$.
3. **Protein Ceilings:** Protein intake is capped at $35\%$ of total calories to prevent excessive nitrogenous burden on kidneys.

### Mandatory Medical Disclaimer
Every generated diet plan unconditionally contains:
> *"Disclaimer: This nutrition guidance is for general fitness and wellness educational purposes only and does not constitute medical advice. Consult a healthcare professional before beginning any restrictive diet."*

---

## 32. Testing & Regression Verification

Phase 4 features a dedicated 13-test automated suite in [`backend/test_phase_4_nutrition.py`](file:///C:/Users/anand/AI-Gym-Fitness-Assistant/backend/test_phase_4_nutrition.py):

| Test ID | Test Name | Target Area | Status |
| :--- | :--- | :--- | :---: |
| `test_01` | `test_01_bmi_calculation_and_categories` | WHO BMI thresholds & healthy weight ranges | **PASS** |
| `test_02` | `test_02_bmi_boundary_and_invalid_inputs` | Height/weight range boundary validation | **PASS** |
| `test_03` | `test_03_bmr_and_tdee_formulas` | Mifflin-St Jeor equation & activity multipliers | **PASS** |
| `test_04` | `test_04_caloric_and_macro_targets_by_goal` | Goal deficits/surpluses & keto/high-protein ratios | **PASS** |
| `test_05` | `test_05_unauthenticated_requests_rejected` | JWT bearer token security on protected routes | **PASS** |
| `test_06` | `test_06_public_custom_bmi_api` | Public `/diet/bmi` endpoint for guest users | **PASS** |
| `test_07` | `test_07_food_catalogue_search_api` | USDA catalogue retrieval & search filtering | **PASS** |
| `test_08` | `test_08_nutrition_target_get_and_update` | Target auto-initialization & manual update | **PASS** |
| `test_09` | `test_09_food_logging_and_daily_summary` | Logging, daily summation, and food deletion | **PASS** |
| `test_10` | `test_10_ai_dietician_plan_grocery_and_user_isolation`| Plan generation, grocery checklist, cross-user isolation | **PASS** |
| `test_11` | `test_11_weekly_nutrition_aggregation` | 7-day longitudinal aggregation & isolation | **PASS** |
| `test_12` | `test_12_food_log_input_validation_and_boundaries` | Rejection of negative/impossible quantities/cals | **PASS** |
| `test_13` | `test_13_llm_safety_and_starvation_prevention` | Starvation diet rejection, fallback, disclaimers | **PASS** |

### Complete Multi-Phase Regression Results
- **Phase 1 (User/Profile Foundation):** 12/12 passed (`backend/verify_step_2d.py`).
- **Phase 2.1 (Exercise Catalogue):** 9/9 passed (`backend/verify_phase_2_1.py`).
- **Phase 2.2 (Pose Pipeline):** 9/9 passed (`ml/pose/test_pose_detector.py`).
- **Phase 2.3 (Squat FSM & Rep Counting):** 22/22 passed (`ml/pose/test_squat_pipeline.py`).
- **Phase 2.4 (Squat Form Analyzer):** 11/11 passed (`ml/pose/test_form_analyzer.py`).
- **Phase 2.5 (Performance Score v1.0):** 8/8 passed (`ml/pose/test_performance_analyzer.py`).
- **Phase 2 API & E2E:** 11/11 passed (`backend/test_phase_2_api.py` & `backend/smoke_test_e2e.py`).
- **Phase 3 (Longitudinal Intelligence):** 10/10 passed (`backend/test_phase_3_performance.py`).
- **Phase 4 (Nutrition & AI Dietician):** 13/13 passed (`backend/test_phase_4_nutrition.py`).
- **Frontend Production Build:** `npm.cmd run build` compiled in 20.6s with exit code 0.
- **Total Suite:** **105 / 105 automated checks passing (100%)**.

---

## 33. Exact Important Files & What Each Does

1. [`backend/models/nutrition.py`](file:///C:/Users/anand/AI-Gym-Fitness-Assistant/backend/models/nutrition.py): SQLAlchemy ORM models for `NutritionTarget`, `NutritionLog`, and `DietPlan`.
2. [`backend/schemas/nutrition.py`](file:///C:/Users/anand/AI-Gym-Fitness-Assistant/backend/schemas/nutrition.py): Pydantic v2 schemas defining request/response structures with strict validation constraints.
3. [`backend/services/nutrition_service.py`](file:///C:/Users/anand/AI-Gym-Fitness-Assistant/backend/services/nutrition_service.py): Mathematical calculation service for BMI, BMR, TDEE, macro distribution, USDA catalogue, and daily/weekly aggregation.
4. [`backend/services/dietician_service.py`](file:///C:/Users/anand/AI-Gym-Fitness-Assistant/backend/services/dietician_service.py): AI Dietician service managing LLM prompt construction, API calls, response parsing, deterministic fallback, and grocery generation.
5. [`backend/routers/nutrition.py`](file:///C:/Users/anand/AI-Gym-Fitness-Assistant/backend/routers/nutrition.py): FastAPI router registering all 12 nutrition endpoints with JWT authentication.
6. [`backend/create_tables.py`](file:///C:/Users/anand/AI-Gym-Fitness-Assistant/backend/create_tables.py): Database migration script ensuring all Phase 4 tables are created idempotently in PostgreSQL.
7. [`backend/test_phase_4_nutrition.py`](file:///C:/Users/anand/AI-Gym-Fitness-Assistant/backend/test_phase_4_nutrition.py): Comprehensive 13-test automated regression suite.
8. [`frontend/src/app/nutrition/page.tsx`](file:///C:/Users/anand/AI-Gym-Fitness-Assistant/frontend/src/app/nutrition/page.tsx): Full-featured Next.js 16 user interface.

---

## 34. Beginner Glossary

- **BMR (Basal Metabolic Rate):** Calories burned at complete rest to keep organs functioning.
- **TDEE (Total Daily Energy Expenditure):** Total calories burned in a day including exercise and daily movement.
- **Mifflin-St Jeor:** The scientific mathematical formula used to calculate BMR.
- **Macronutrients (Macros):** Nutrients needed in large amounts: Protein ($4\text{ kcal/g}$), Carbohydrates ($4\text{ kcal/g}$), and Fat ($9\text{ kcal/g}$).
- **Micronutrients:** Vitamins and minerals needed in tiny amounts (zinc, iron, vitamin D).
- **Caloric Deficit:** Consuming fewer calories than you burn (causes weight loss).
- **Caloric Surplus:** Consuming more calories than you burn (causes weight gain).
- **USDA FoodData Central (FDC):** The official US government nutritional database.
- **Deterministic:** An algorithm where the same input always produces the exact same output (100% predictable math).
- **Probabilistic / Generative:** AI models (like LLMs) that predict the next token based on probabilities.
- **Pydantic:** A Python data-validation library that enforces strict types and ranges.
- **ORM (Object-Relational Mapping):** A library (SQLAlchemy) that allows Python code to talk to SQL database tables like regular Python classes.
- **JWT (JSON Web Token):** A secure cryptographic token passed in HTTP headers to prove the user's identity.

---

## 35. Simple Real-World Example: One User Through the Complete System

Let us follow **Anand**:
1. **Profile Setup:** Anand sets his profile: $175\text{ cm}$, $70\text{ kg}$, age 25, male, `moderate` activity, fitness goal: `fat_loss`, dietary preference: `high_protein`.
2. **Target Computation:**
   - BMI: $70 / (1.75^2) = 22.9$ (Normal weight).
   - BMR: $10(70) + 6.25(175) - 5(25) + 5 = 1673.8\text{ kcal}$.
   - TDEE: $1673.8 \times 1.55 = 2594.3\text{ kcal}$.
   - Target Calories (20% deficit): $2594.3 \times 0.80 = 2075\text{ kcal}$.
   - High-Protein Target: $35\%$ protein ($181.6\text{g}$), $40\%$ carbs ($207.5\text{g}$), $25\%$ fat ($57.6\text{g}$).
   - Hydration: $70 \times 0.035 = 2.5\text{ Liters}$.
3. **Breakfast:** Anand eats 4 Scrambled Eggs ($200\text{g}$) and 2 slices of Whole Wheat Bread ($80\text{g}$). He logs them via the frontend. Total logged: $483\text{ kcal}$, $38.2\text{g P}$.
4. **Daily Progress:** The dashboard immediately updates: Remaining budget is $1592\text{ kcal}$. Protein progress ring shows $21\%$.
5. **AI Dietician:** Anand clicks "Generate Diet Plan". The backend passes his $2075\text{ kcal}$ budget to the dietician engine. He receives a 3-meal plan plus a categorized grocery list (Eggs, Chicken, Brown Rice, Spinach, Olive Oil).
6. **Weekly Check-In:** At the end of the week, Anand checks `/nutrition`. The 7-day sparkline shows he averaged $2050\text{ kcal/day}$ with a $98.8\%$ compliance rate and status **"On Track"**.

---

## 36. Interview Questions & Answers for Phase 4

### Q1: Why did you separate metabolic calculation from the LLM?
**Answer:** *"LLMs are probabilistic token predictors, not calculators. Allowing an LLM to calculate BMR or macronutrients frequently leads to mathematical hallucinations where calories and macros do not add up. In our architecture, all metabolic math is 100% deterministic, implemented in Python using the clinical Mifflin-St Jeor formula. The LLM is used exclusively for creative meal composition within those strict pre-calculated macro boundaries."*

### Q2: How does your backend prevent crash/starvation diets?
**Answer:** *"We enforce multiple safety layers. First, at the API level, Pydantic rejects any calorie target under 800 kcal with an HTTP 422 error. Second, in our calculation engine, fat loss deficits are clamped with safe metabolic floors (1200 kcal for females, 1500 kcal for males). Third, programmatic calls to the dietician service floor custom calories to 800 kcal."*

### Q3: What happens if the external LLM service goes down?
**Answer:** *"Our architecture includes a built-in deterministic expert dietician engine. If the LLM times out, hits a rate limit, or returns malformed JSON, our service catches the exception and immediately generates a mathematically balanced meal plan and grocery list using our rule-based expert engine. The user experiences zero downtime."*

### Q4: How do you handle cross-user data isolation?
**Answer:** *"Every request requires a verified JWT bearer token. FastAPI extracts the authenticated user's ID via dependency injection. All database queries for nutrition targets, food logs, and diet plans filter strictly by `user_id == current_user.id`. Even if a malicious user guesses another user's food log ID, our delete endpoint verifies ownership and returns a 404."*

---

## 37. Common Misconceptions

- **Misconception 1:** *"The AI creates the nutrition numbers."*  
  **Reality:** Python creates the numbers with deterministic math. The AI creates the culinary meal names, food combinations, and preparation instructions.
- **Misconception 2:** *"A 1000-calorie deficit burns fat 5x faster safely."*  
  **Reality:** Extreme deficits trigger starvation adaptation, lowering BMR and causing lean muscle tissue loss. Our system limits deficits to a sustainable 20%.
- **Misconception 3:** *"Keto diets mean zero carbohydrates."*  
  **Reality:** Ketogenic diets allow approximately 5% of daily energy from carbohydrates (typically 20–30g) to accommodate trace carbs from fibrous vegetables and seeds.

---

## 38. What Is Genuinely AI vs Deterministic Software in Phase 4

| Component | Nature | Technology Used | Rationale |
| :--- | :--- | :--- | :--- |
| **BMI / BMR / TDEE** | Deterministic | Pure Python | Scientific formulas must be 100% exact and reproducible. |
| **Macro Splits** | Deterministic | Pure Python | Energy ratios ($4\text{ kcal/g}$, $9\text{ kcal/g}$) are immutable laws of physics. |
| **Input Validation** | Deterministic | Pydantic v2 | Boundary security requires strict deterministic typing. |
| **Meal Composition** | Generative AI | Gemini 1.5 Flash / GPT-4o-mini | Natural language creativity, culinary combinations, and recipe suggestions. |
| **Dietician Fallback** | Deterministic | Rule-based Python engine | Guarantees high availability when external AI APIs fail. |
| **Grocery Derivation**| Deterministic | Keyword & category matching | Categorizing shopping lists does not require an LLM. |

---

## 39. Known Limitations

1. **Micronutrient Tracking:** Phase 4 focuses strictly on calories and macronutrients (protein, carbohydrates, fat, water). It does not yet track individual micronutrients (sodium, iron, potassium, vitamin D).
2. **Barcode Scanning:** Food logging currently relies on catalogue searching and manual input; optical barcode scanning is planned for future mobile iterations.
3. **Static Food Catalogue:** The built-in verified catalogue has 22 staple foods. Expanding this to tens of thousands of branded supermarket items would require an external API subscription (e.g., Nutritionix or OpenFoodFacts).

---

## 40. Clear Boundary Between Phase 4 and Phase 5

| Feature / Capability | Phase 4 (Nutrition & AI Dietician) | Phase 5 (Virtual Gym Buddy) |
| :--- | :---: | :---: |
| **Metabolic Rates (BMI/BMR/TDEE)** | **Implemented** | Consumed as context |
| **Daily Food Logging & Summaries** | **Implemented** | Consumed as context |
| **Weekly Nutrition Aggregation** | **Implemented** | Consumed as context |
| **AI Dietician Meal Planning** | **Implemented** | Consumed as context |
| **Categorized Grocery Lists** | **Implemented** | Consumed as context |
| **Interactive Conversational AI Chat** | Out of Scope | **Primary Goal** |
| **Persona-Driven Gym Buddy Coaching**| Out of Scope | **Primary Goal** |
| **Cross-Phase Contextual Synthesis** | Out of Scope | **Primary Goal** |

In Phase 4, the nutrition intelligence is complete, tested, and stored in PostgreSQL. In **Phase 5**, the **Virtual Gym Buddy** will synthesize workout logs from Phases 2–3 and nutrition logs from Phase 4 into an empathetic, real-time conversational partner.

---
*End of Phase 4 Master Implementation & Learning Guide.*
