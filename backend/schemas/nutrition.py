from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class BMICalculateRequest(BaseModel):
    """Input parameters for calculating BMI and metabolic rates."""
    height_cm: float = Field(..., ge=50.0, le=260.0, description="Height in centimeters")
    weight_kg: float = Field(..., ge=20.0, le=350.0, description="Weight in kilograms")
    age: Optional[int] = Field(default=25, ge=10, le=120, description="Age in years")
    gender: Optional[str] = Field(default="neutral", description="male, female, or neutral")
    activity_level: Optional[str] = Field(default="moderate", description="sedentary, light, moderate, very_active, extra_active")
    fitness_goal: Optional[str] = Field(default="maintenance", description="fat_loss, muscle_gain, maintenance, general_fitness, endurance")
    dietary_preference: Optional[str] = Field(default="standard", description="standard, vegetarian, vegan, keto, high_protein")


class BMIResponse(BaseModel):
    """Deterministic BMI and metabolic rate response."""
    height_cm: float
    weight_kg: float
    bmi: float
    category: str
    healthy_weight_min_kg: float
    healthy_weight_max_kg: float
    bmr: float
    tdee: float
    recommended_calories: float
    recommended_protein_g: float
    recommended_carbs_g: float
    recommended_fat_g: float
    water_liters: float


class NutritionTargetResponse(BaseModel):
    """User active daily nutrition targets."""
    id: int
    user_id: int
    calories_target: float
    protein_grams: float
    carbs_grams: float
    fat_grams: float
    water_liters: float
    dietary_preference: str
    allergies_restrictions: Optional[str] = None
    meals_per_day: int
    updated_at: datetime


class NutritionTargetUpdateRequest(BaseModel):
    """Payload to customize user daily nutrition targets."""
    calories_target: Optional[float] = Field(None, ge=800.0, le=8000.0)
    protein_grams: Optional[float] = Field(None, ge=20.0, le=500.0)
    carbs_grams: Optional[float] = Field(None, ge=10.0, le=1000.0)
    fat_grams: Optional[float] = Field(None, ge=10.0, le=400.0)
    water_liters: Optional[float] = Field(None, ge=1.0, le=10.0)
    dietary_preference: Optional[str] = Field(None, max_length=100)
    allergies_restrictions: Optional[str] = Field(None, max_length=255)
    meals_per_day: Optional[int] = Field(None, ge=1, le=8)


class FoodCatalogueItem(BaseModel):
    """Standard verified food item from USDA FoodData Central reference database."""
    id: str
    name: str
    category: str
    serving_size_g: float
    calories_per_100g: float
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float
    source: str = "USDA FoodData Central"
    fdc_id: Optional[str] = None


class FoodLogCreateRequest(BaseModel):
    """Payload to log a food entry with strict physical boundary validation."""
    food_name: str = Field(..., min_length=1, max_length=150)
    quantity: float = Field(..., gt=0.0, le=5000.0, description="Quantity consumed (> 0 and <= 5000)")
    unit: str = Field(default="g", max_length=50)
    meal_type: str = Field(default="lunch", description="breakfast, lunch, dinner, snack")
    calories: float = Field(..., ge=0.0, le=5000.0, description="Calories (0 to 5000 kcal)")
    protein: float = Field(default=0.0, ge=0.0, le=500.0, description="Protein (0 to 500g)")
    carbs: float = Field(default=0.0, ge=0.0, le=500.0, description="Carbohydrates (0 to 500g)")
    fat: float = Field(default=0.0, ge=0.0, le=500.0, description="Fat (0 to 500g)")
    log_date: Optional[date] = Field(default=None, description="Date of entry, defaults to today")

    @field_validator("meal_type")
    @classmethod
    def validate_meal_type(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in ("breakfast", "lunch", "dinner", "snack"):
            return "lunch"
        return clean


class FoodLogResponse(BaseModel):
    """Logged food item representation."""
    id: int
    user_id: int
    log_date: str
    meal_type: str
    food_name: str
    quantity: float
    unit: str
    calories: float
    protein: float
    carbs: float
    fat: float
    created_at: datetime


class DailyNutritionSummaryResponse(BaseModel):
    """Daily aggregated nutrition tracking summary compared against targets."""
    date: str
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    target_calories: float
    target_protein: float
    target_carbs: float
    target_fat: float
    water_liters: float
    remaining_calories: float
    calories_percentage: float
    protein_percentage: float
    carbs_percentage: float
    fat_percentage: float
    status: str  # on_track, under_target, over_target
    meal_breakdown: Dict[str, List[FoodLogResponse]]


class MealItem(BaseModel):
    """Single food item within a suggested meal."""
    name: str
    quantity: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


class MealPlanItem(BaseModel):
    """Single structured meal within a full daily plan."""
    meal_type: str  # breakfast, lunch, dinner, snack
    meal_name: str
    items: List[MealItem]
    total_calories: float
    total_protein_g: float
    total_carbs_g: float
    total_fat_g: float
    instructions: Optional[str] = None


class GroceryCategory(BaseModel):
    """Categorized grocery list section."""
    category: str  # Protein, Vegetables, Carbohydrates, Healthy Fats, Dairy/Alternatives, Pantry
    items: List[str]


class DietPlanCreateRequest(BaseModel):
    """Request payload to generate a personalized diet plan."""
    dietary_preference: Optional[str] = Field(None, description="standard, vegetarian, vegan, keto, high_protein")
    allergies_restrictions: Optional[str] = Field(None, description="allergies or exclusions (e.g. dairy, peanuts)")
    meals_per_day: Optional[int] = Field(default=3, ge=2, le=5)
    target_calories: Optional[float] = Field(default=None, ge=800.0, le=8000.0)


class DietPlanResponse(BaseModel):
    """Complete personalized diet plan and categorized grocery list."""
    id: int
    user_id: int
    calories_target: float
    dietary_preference: str
    goal: str
    meals: List[MealPlanItem]
    total_plan_calories: float
    total_plan_protein: float
    total_plan_carbs: float
    total_plan_fat: float
    grocery_list: List[GroceryCategory]
    notes: Optional[str] = None
    provider: str  # llm_gemini, llm_openai, deterministic_expert
    disclaimer: str
    created_at: datetime


class DailyMacroPoint(BaseModel):
    """Daily aggregated macro point in weekly longitudinal history."""
    date: str
    calories: float
    protein: float
    carbs: float
    fat: float
    log_count: int


class WeeklyNutritionSummaryResponse(BaseModel):
    """Weekly aggregated longitudinal nutrition intelligence."""
    reporting_period: Dict[str, Any]  # start_date, end_date, days
    total_calories: float
    total_protein: float
    total_carbs: float
    total_fat: float
    daily_average_calories: float
    daily_average_protein: float
    daily_average_carbs: float
    daily_average_fat: float
    target_calories: float
    target_protein: float
    target_carbs: float
    target_fat: float
    calorie_compliance_percentage: float
    days_logged: int
    compliance_status: str  # on_track, under_target, over_target
    daily_history: List[DailyMacroPoint]
