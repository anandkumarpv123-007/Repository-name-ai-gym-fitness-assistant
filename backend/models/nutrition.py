from datetime import datetime, date
from typing import TYPE_CHECKING
from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base

if TYPE_CHECKING:
    from models.user import User


class NutritionTarget(Base):
    """
    Stores calculated or custom daily caloric and macronutrient targets for a user.
    """
    __tablename__ = "nutrition_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    calories_target: Mapped[float] = mapped_column(Float, nullable=False)
    protein_grams: Mapped[float] = mapped_column(Float, nullable=False)
    carbs_grams: Mapped[float] = mapped_column(Float, nullable=False)
    fat_grams: Mapped[float] = mapped_column(Float, nullable=False)
    water_liters: Mapped[float] = mapped_column(Float, default=2.5)

    dietary_preference: Mapped[str] = mapped_column(String(100), default="standard")
    allergies_restrictions: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meals_per_day: Mapped[int] = mapped_column(Integer, default=3)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="nutrition_target")


class NutritionLog(Base):
    """
    Stores individual food entries logged by the user for daily macro tracking.
    """
    __tablename__ = "nutrition_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    log_date: Mapped[date] = mapped_column(Date, default=date.today, index=True, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(50), default="lunch")  # breakfast, lunch, dinner, snack
    food_name: Mapped[str] = mapped_column(String(150), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), default="g")  # g, ml, serving, piece

    calories: Mapped[float] = mapped_column(Float, nullable=False)
    protein: Mapped[float] = mapped_column(Float, default=0.0)
    carbs: Mapped[float] = mapped_column(Float, default=0.0)
    fat: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="nutrition_logs")


class DietPlan(Base):
    """
    Stores structured meal plans and generated grocery lists created by the AI Dietician.
    """
    __tablename__ = "diet_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    calories_target: Mapped[float] = mapped_column(Float, nullable=False)
    dietary_preference: Mapped[str] = mapped_column(String(100), default="standard")
    goal: Mapped[str] = mapped_column(String(100), default="maintenance")

    # Structured JSON for meals: [{meal_type, meal_name, items, calories, protein, carbs, fat, instructions}]
    plan_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Structured JSON for grocery items: [{category, items: [{name, quantity}]}]
    grocery_list_json: Mapped[str] = mapped_column(Text, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String(50), default="deterministic_expert")  # llm_gemini, llm_openai, deterministic_expert

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship("User", back_populates="diet_plans")
