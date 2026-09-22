from datetime import date, datetime
from typing import Any, Dict, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.profile import Profile
from services.performance_service import PerformanceService
from services.nutrition_service import NutritionService
from services.dietician_service import DieticianService


class BuddyContextEngine:
    """
    Dedicated Context Engine for Virtual Gym Buddy.
    Gathers authenticated user profile, Phase 3 performance metrics,
    and Phase 4 nutrition context into a clean structured payload.
    
    Strictly scopes all database queries to current user_id.
    Handles missing or incomplete user data gracefully without failing.
    """

    @classmethod
    def gather_user_context(cls, db: Session, user_id: int) -> Dict[str, Any]:
        """
        Compiles complete, multi-domain user fitness context.
        """
        profile_data = cls._get_profile_context(db, user_id)
        workout_data = cls._get_workout_context(db, user_id)
        nutrition_data = cls._get_nutrition_context(db, user_id)

        return {
            "user_id": user_id,
            "profile": profile_data,
            "workout_performance": workout_data,
            "nutrition": nutrition_data,
            "context_timestamp": datetime.utcnow().isoformat(),
        }

    @classmethod
    def format_context_prompt_block(cls, context: Dict[str, Any]) -> str:
        """
        Formats user context into a structured, readable string for LLM system prompts.
        """
        prof = context.get("profile", {})
        work = context.get("workout_performance", {})
        nutr = context.get("nutrition", {})

        lines = [
            "=== AUTHENTICATED USER CONTEXT (USE EXCLUSIVELY FOR SPECIFIC DATA) ===",
            f"User Profile:",
            f"  - Fitness Goal: {prof.get('fitness_goal') or 'Not set'}",
            f"  - Activity Level: {prof.get('activity_level') or 'Not set'}",
            f"  - Height: {prof.get('height_cm') or 'N/A'} cm, Weight: {prof.get('weight_kg') or 'N/A'} kg",
            f"  - Gender: {prof.get('gender') or 'Not set'}, Dietary Pref: {prof.get('dietary_preference') or 'Standard'}",
            "",
            f"Weekly Workout & Performance (Last 7 Days):",
            f"  - Workouts Completed: {work.get('total_workouts', 0)}",
            f"  - Total Reps Logged: {work.get('total_reps', 0)}",
            f"  - Average Performance Score: {work.get('avg_performance_score', 'N/A')}/100",
            f"  - Top Exercise: {work.get('top_exercise') or 'None logged'}",
            f"  - Recurring Form Issues: {', '.join(work.get('recurring_form_issues', [])) or 'None detected'}",
            f"  - Strongest Area: {work.get('strongest_improvement_area') or 'Building baseline'}",
            f"  - Next Week Focus: {work.get('next_week_focus') or 'Maintain consistency'}",
            "",
            f"Nutrition Status:",
            f"  - Daily Calorie Target: {nutr.get('target_calories', 'N/A')} kcal",
            f"  - Consumed Today: {nutr.get('consumed_calories_today', 0)} kcal ({nutr.get('remaining_calories_today', 'N/A')} kcal remaining)",
            f"  - Target Protein: {nutr.get('target_protein', 'N/A')}g, Carbs: {nutr.get('target_carbs', 'N/A')}g, Fat: {nutr.get('target_fat', 'N/A')}g",
            f"  - Consumed Today Protein: {nutr.get('consumed_protein_today', 0)}g, Carbs: {nutr.get('consumed_carbs_today', 0)}g, Fat: {nutr.get('consumed_fat_today', 0)}g",
            f"  - Nutrition Log Count Today: {nutr.get('logs_count_today', 0)}",
            "=====================================================================",
        ]
        return "\n".join(lines)

    @classmethod
    def _get_profile_context(cls, db: Session, user_id: int) -> Dict[str, Any]:
        try:
            profile = db.execute(
                select(Profile).where(Profile.user_id == user_id)
            ).scalars().first()

            if not profile:
                return {
                    "has_profile": False,
                    "fitness_goal": None,
                    "activity_level": None,
                    "height_cm": None,
                    "weight_kg": None,
                    "gender": None,
                    "dietary_preference": None,
                }

            return {
                "has_profile": True,
                "fitness_goal": profile.fitness_goal,
                "activity_level": profile.activity_level,
                "height_cm": profile.height_cm,
                "weight_kg": profile.weight_kg,
                "gender": profile.gender,
                "dietary_preference": profile.dietary_preference,
            }
        except Exception:
            return {"has_profile": False}

    @classmethod
    def _get_workout_context(cls, db: Session, user_id: int) -> Dict[str, Any]:
        try:
            report = PerformanceService.get_weekly_performance_report(db, user_id, days=7)
            tot_w = report.get("total_sessions", report.get("summary", {}).get("total_workouts", 0))
            tot_r = report.get("total_reps", report.get("summary", {}).get("total_reps", 0))
            avg_score = report.get("average_score") or report.get("summary", {}).get("avg_performance_score") or 0.0

            issues = report.get("recurring_form_issues") or [report.get("recurring_form_issue")] if report.get("recurring_form_issue") else []
            improvement = report.get("strongest_improvement_area")
            focus = report.get("next_week_focus", {})
            ex_stats = report.get("exercise_stats", [])

            top_ex = ex_stats[0].get("exercise_name") if ex_stats and isinstance(ex_stats[0], dict) else None
            issue_names = [f.get("issue_name") if isinstance(f, dict) else str(f) for f in issues if f]

            focus_text = focus.get("title") if isinstance(focus, dict) else (str(focus) if focus else None)

            return {
                "total_workouts": tot_w,
                "total_reps": tot_r,
                "avg_performance_score": avg_score,
                "top_exercise": top_ex,
                "recurring_form_issues": issue_names,
                "strongest_improvement_area": improvement.get("component_display") if isinstance(improvement, dict) else (str(improvement) if improvement else None),
                "next_week_focus": focus_text,
            }
        except Exception as e:
            return {
                "total_workouts": 0,
                "total_reps": 0,
                "avg_performance_score": 0.0,
                "top_exercise": None,
                "recurring_form_issues": [],
                "strongest_improvement_area": None,
                "next_week_focus": None,
                "error": str(e),
            }

    @classmethod
    def _get_nutrition_context(cls, db: Session, user_id: int) -> Dict[str, Any]:
        try:
            target = NutritionService.get_or_create_user_target(db, user_id)
            today_summary = NutritionService.get_daily_summary(db, user_id, date.today())
            latest_plan = DieticianService.get_latest_plan(db, user_id)

            tot_cals = today_summary.get("total_calories", 0.0)
            tot_p = today_summary.get("total_protein", 0.0)
            tot_cb = today_summary.get("total_carbs", 0.0)
            tot_f = today_summary.get("total_fat", 0.0)
            rem_cals = today_summary.get("remaining_calories", target.calories_target)

            breakdown = today_summary.get("meal_breakdown", {})
            logs_count = sum(len(items) for items in breakdown.values()) if isinstance(breakdown, dict) else 0

            return {
                "target_calories": target.calories_target,
                "target_protein": target.protein_grams,
                "target_carbs": target.carbs_grams,
                "target_fat": target.fat_grams,
                "consumed_calories_today": tot_cals,
                "consumed_protein_today": tot_p,
                "consumed_carbs_today": tot_cb,
                "consumed_fat_today": tot_f,
                "remaining_calories_today": rem_cals,
                "logs_count_today": logs_count,
                "has_active_diet_plan": latest_plan is not None,
                "active_plan_goal": latest_plan.get("goal") if latest_plan else None,
            }
        except Exception as e:
            return {
                "target_calories": 2000.0,
                "target_protein": 150.0,
                "target_carbs": 200.0,
                "target_fat": 65.0,
                "consumed_calories_today": 0.0,
                "consumed_protein_today": 0.0,
                "consumed_carbs_today": 0.0,
                "consumed_fat_today": 0.0,
                "remaining_calories_today": 2000.0,
                "logs_count_today": 0,
                "has_active_diet_plan": False,
                "error": str(e),
            }
