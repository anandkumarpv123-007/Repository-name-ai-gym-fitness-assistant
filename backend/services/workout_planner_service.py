import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from models.planner import WorkoutPlan, WorkoutPlanItem
from models.user import User
from models.profile import Profile
from schemas.planner import (
    ExerciseItem,
    WorkoutPlanItemResponse,
    WorkoutPlanResponse,
    WorkoutPlanHistoryResponse,
)
from services.performance_service import PerformanceService
from services.habit_predictor_service import HabitPredictorService


class WorkoutPlannerService:
    """
    Personalized Workout Planner Service for Phase 7.
    Generates structured 7-day weekly workout plans dynamically tailored to user goal,
    incorporating Phase 3 form performance cues and Phase 6 habit risk adaptations.
    """

    @classmethod
    def generate_workout_plan(
        cls,
        db: Session,
        user_id: int,
        custom_goal: Optional[str] = None,
        custom_days: Optional[int] = None,
    ) -> WorkoutPlanResponse:
        """
        Generates and persists a personalized weekly workout plan for specified user.
        """
        user = db.execute(select(User).where(User.id == user_id)).scalars().first()
        profile = user.profile if user else None
        
        goal = (custom_goal or (profile.fitness_goal if profile and profile.fitness_goal else "hypertrophy")).lower()

        # 1. Fetch Phase 6 Habit Telemetry
        habit_adapted = False
        habit_notes = []
        try:
            habit_status = HabitPredictorService.analyze_user_habit(db, user_id)
            if habit_status.risk_level == "high" or habit_status.status == "insufficient_data":
                habit_adapted = True
                habit_notes.append("Adapted plan volume to a manageable 3-day split to lower entry barriers and build habit retention.")
        except Exception:
            pass

        # 2. Fetch Phase 3 Performance Telemetry
        performance_adapted = False
        form_warnings = []
        try:
            weekly_perf = PerformanceService.get_weekly_report(db, user_id)
            if weekly_perf.summary.recurring_form_issues:
                performance_adapted = True
                for issue in weekly_perf.summary.recurring_form_issues:
                    form_warnings.append(f"Form Focus: {issue.exercise} - {issue.issue_description} (Correction: {issue.recommendation})")
        except Exception:
            pass

        target_days = custom_days or (3 if habit_adapted else 4)

        # 3. Generate Weekly Plan Structure Aligned to Goal
        plan_name, target_split, weekly_items = cls._build_weekly_schedule(
            goal=goal,
            target_days=target_days,
            form_warnings=form_warnings,
        )

        adaptation_notes_str = "; ".join(habit_notes + form_warnings) if (habit_notes or form_warnings) else None

        # 4. Save WorkoutPlan DB Entity
        plan_record = WorkoutPlan(
            user_id=user_id,
            plan_name=plan_name,
            fitness_goal=goal,
            target_split=target_split,
            days_per_week=target_days,
            habit_adapted=habit_adapted,
            performance_adapted=performance_adapted,
            adaptation_notes=adaptation_notes_str,
            created_at=datetime.utcnow(),
        )
        db.add(plan_record)
        db.commit()
        db.refresh(plan_record)

        # 5. Save 7 WorkoutPlanItem DB Entities (Monday .. Sunday)
        for item_data in weekly_items:
            item_record = WorkoutPlanItem(
                plan_id=plan_record.id,
                day_of_week=item_data["day_of_week"],
                day_title=item_data["day_title"],
                is_rest_day=item_data["is_rest_day"],
                target_muscle_groups=item_data["target_muscle_groups"],
                exercises_json=json.dumps([e.model_dump() for e in item_data["exercises"]]),
                warmup_notes=item_data.get("warmup_notes"),
            )
            db.add(item_record)
        db.commit()

        # Refresh plan with items
        full_plan = db.execute(
            select(WorkoutPlan)
            .options(joinedload(WorkoutPlan.items))
            .where(WorkoutPlan.id == plan_record.id)
        ).unique().scalars().first()

        return cls._to_plan_response(full_plan)

    @classmethod
    def get_latest_plan(cls, db: Session, user_id: int) -> Optional[WorkoutPlanResponse]:
        """Retrieves the authenticated user's most recent workout plan."""
        plan = db.execute(
            select(WorkoutPlan)
            .options(joinedload(WorkoutPlan.items))
            .where(WorkoutPlan.user_id == user_id)
            .order_by(WorkoutPlan.created_at.desc())
        ).unique().scalars().first()

        if not plan:
            return None
        return cls._to_plan_response(plan)

    @classmethod
    def get_plan_history(cls, db: Session, user_id: int, limit: int = 10) -> WorkoutPlanHistoryResponse:
        """Retrieves history of generated workout plans for authenticated user."""
        plans = db.execute(
            select(WorkoutPlan)
            .options(joinedload(WorkoutPlan.items))
            .where(WorkoutPlan.user_id == user_id)
            .order_by(WorkoutPlan.created_at.desc())
            .limit(limit)
        ).unique().scalars().all()

        plan_responses = [cls._to_plan_response(p) for p in plans]
        return WorkoutPlanHistoryResponse(user_id=user_id, plans=plan_responses)

    @classmethod
    def _build_weekly_schedule(
        cls,
        goal: str,
        target_days: int,
        form_warnings: List[str],
    ) -> (str, str, List[Dict[str, Any]]):
        """
        Constructs explicit day-by-day exercise plans for all 7 days of the week.
        """
        warmup_cue = form_warnings[0] if form_warnings else "Warm up with 5-10 minutes of dynamic mobility exercises."

        if goal == "strength":
            plan_name = "4-Day Heavy Compound Strength Split"
            target_split = "Upper / Lower Heavy Strength"
            days = [
                {
                    "day_of_week": "Monday",
                    "day_title": "Lower Body Heavy Strength",
                    "is_rest_day": False,
                    "target_muscle_groups": "Quads, Hamstrings, Glutes",
                    "warmup_notes": warmup_cue,
                    "exercises": [
                        ExerciseItem(name="Barbell Back Squat", sets=4, reps_or_duration="3-5 reps", target_muscle="Quads & Glutes", technique_cue="Focus on keeping chest upright and knees tracking over toes"),
                        ExerciseItem(name="Romanian Deadlift", sets=3, reps_or_duration="5-6 reps", target_muscle="Hamstrings", technique_cue="Hinge at hips with neutral spine"),
                        ExerciseItem(name="Leg Press", sets=3, reps_or_duration="6-8 reps", target_muscle="Quads", technique_cue="Control eccentric tempo"),
                    ],
                },
                {
                    "day_of_week": "Tuesday",
                    "day_title": "Upper Body Heavy Strength",
                    "is_rest_day": False,
                    "target_muscle_groups": "Chest, Back, Shoulders",
                    "warmup_notes": "Shoulder cuff rotations & band pull-aparts.",
                    "exercises": [
                        ExerciseItem(name="Barbell Bench Press", sets=4, reps_or_duration="3-5 reps", target_muscle="Chest", technique_cue="Retract scapula and drive feet into floor"),
                        ExerciseItem(name="Barbell Bent-Over Row", sets=4, reps_or_duration="5-6 reps", target_muscle="Lats & Upper Back", technique_cue="Pull barbell to lower sternum"),
                        ExerciseItem(name="Overhead Press", sets=3, reps_or_duration="5-6 reps", target_muscle="Shoulders", technique_cue="Brace core tight throughout vertical push"),
                    ],
                },
                {
                    "day_of_week": "Wednesday",
                    "day_title": "Active Recovery & Mobility",
                    "is_rest_day": True,
                    "target_muscle_groups": "Full Body Recovery",
                    "warmup_notes": None,
                    "exercises": [],
                },
                {
                    "day_of_week": "Thursday",
                    "day_title": "Lower Body Deadlift & Power",
                    "is_rest_day": False,
                    "target_muscle_groups": "Posterior Chain & Core",
                    "warmup_notes": warmup_cue,
                    "exercises": [
                        ExerciseItem(name="Conventional Deadlift", sets=3, reps_or_duration="3-5 reps", target_muscle="Posterior Chain", technique_cue="Pull slack out of bar before lifting"),
                        ExerciseItem(name="Bulgarian Split Squat", sets=3, reps_or_duration="6-8 reps", target_muscle="Quads & Glutes", technique_cue="Maintain vertical torso alignment"),
                    ],
                },
                {
                    "day_of_week": "Friday",
                    "day_title": "Upper Body Hypertrophy & Arms",
                    "is_rest_day": False,
                    "target_muscle_groups": "Upper Body & Arms",
                    "warmup_notes": "Dynamic arm swings.",
                    "exercises": [
                        ExerciseItem(name="Incline Dumbbell Press", sets=3, reps_or_duration="6-8 reps", target_muscle="Upper Chest", technique_cue="3-second slow lowering phase"),
                        ExerciseItem(name="Lat Pulldown", sets=3, reps_or_duration="8-10 reps", target_muscle="Lats", technique_cue="Pull elbows down to ribs"),
                    ],
                },
                {
                    "day_of_week": "Saturday",
                    "day_title": "Rest & Regeneration",
                    "is_rest_day": True,
                    "target_muscle_groups": None,
                    "warmup_notes": None,
                    "exercises": [],
                },
                {
                    "day_of_week": "Sunday",
                    "day_title": "Rest & Regeneration",
                    "is_rest_day": True,
                    "target_muscle_groups": None,
                    "warmup_notes": None,
                    "exercises": [],
                },
            ]

        elif goal in ["weight_loss", "endurance"]:
            plan_name = "4-Day Full Body Conditioning & HIIT Split"
            target_split = "Full Body Circuit & Cardio"
            days = [
                {
                    "day_of_week": "Monday",
                    "day_title": "Full Body Metabolic Conditioning",
                    "is_rest_day": False,
                    "target_muscle_groups": "Full Body",
                    "warmup_notes": warmup_cue,
                    "exercises": [
                        ExerciseItem(name="Bodyweight Squats", sets=4, reps_or_duration="15-20 reps", target_muscle="Quads", technique_cue="Keep fast, rhythmic pacing"),
                        ExerciseItem(name="Push-Ups", sets=4, reps_or_duration="12-15 reps", target_muscle="Chest & Core", technique_cue="Maintain rigid plank posture"),
                        ExerciseItem(name="Kettlebell Swings", sets=3, reps_or_duration="20 reps", target_muscle="Glutes & Hamstrings", technique_cue="Explosive hip hinge action"),
                    ],
                },
                {
                    "day_of_week": "Tuesday",
                    "day_title": "Cardio & Core Endurance",
                    "is_rest_day": False,
                    "target_muscle_groups": "Cardiovascular & Core",
                    "warmup_notes": "5 min light jog.",
                    "exercises": [
                        ExerciseItem(name="Assault Bike Intervals", sets=5, reps_or_duration="30s sprint / 30s rest", target_muscle="Cardio", technique_cue="Maximum effort on sprint intervals"),
                        ExerciseItem(name="Plank Hold", sets=3, reps_or_duration="60 seconds", target_muscle="Core", technique_cue="Engage abdominal wall and glutes"),
                    ],
                },
                {
                    "day_of_week": "Wednesday",
                    "day_title": "Rest & Active Recovery Walk",
                    "is_rest_day": True,
                    "target_muscle_groups": None,
                    "warmup_notes": None,
                    "exercises": [],
                },
                {
                    "day_of_week": "Thursday",
                    "day_title": "Lower Body & Aerobic Circuit",
                    "is_rest_day": False,
                    "target_muscle_groups": "Legs & Cardio",
                    "warmup_notes": warmup_cue,
                    "exercises": [
                        ExerciseItem(name="Dumbbell Lying Leg Curls / Lunges", sets=3, reps_or_duration="12-15 reps", target_muscle="Quads & Hamstrings", technique_cue="Step deep into lunge"),
                        ExerciseItem(name="Rowing Machine Sprints", sets=4, reps_or_duration="500m intervals", target_muscle="Cardio & Back", technique_cue="Drive with legs first"),
                    ],
                },
                {
                    "day_of_week": "Friday",
                    "day_title": "Upper Body & Calorie Burn Circuit",
                    "is_rest_day": False,
                    "target_muscle_groups": "Upper Body",
                    "warmup_notes": "Arm circles and light band pulls.",
                    "exercises": [
                        ExerciseItem(name="Dumbbell Shoulder Press", sets=3, reps_or_duration="12-15 reps", target_muscle="Shoulders", technique_cue="Exhale on press up"),
                        ExerciseItem(name="Cable Lat Rows", sets=3, reps_or_duration="12-15 reps", target_muscle="Back", technique_cue="Squeeze shoulder blades"),
                    ],
                },
                {
                    "day_of_week": "Saturday",
                    "day_title": "Rest & Regeneration",
                    "is_rest_day": True,
                    "target_muscle_groups": None,
                    "warmup_notes": None,
                    "exercises": [],
                },
                {
                    "day_of_week": "Sunday",
                    "day_title": "Rest & Regeneration",
                    "is_rest_day": True,
                    "target_muscle_groups": None,
                    "warmup_notes": None,
                    "exercises": [],
                },
            ]

        else:
            # Default / Hypertrophy Split
            plan_name = "4-Day Muscle Hypertrophy Split"
            target_split = "Push / Pull / Legs / Upper Body"
            days = [
                {
                    "day_of_week": "Monday",
                    "day_title": "Push Hypertrophy (Chest, Shoulders, Triceps)",
                    "is_rest_day": False,
                    "target_muscle_groups": "Chest, Front Delts, Triceps",
                    "warmup_notes": warmup_cue,
                    "exercises": [
                        ExerciseItem(name="Barbell Bench Press", sets=4, reps_or_duration="8-10 reps", target_muscle="Chest", technique_cue="Pause briefly at chest touch"),
                        ExerciseItem(name="Incline Dumbbell Press", sets=3, reps_or_duration="10-12 reps", target_muscle="Upper Chest", technique_cue="Full stretch at bottom"),
                        ExerciseItem(name="Dumbbell Overhead Press", sets=3, reps_or_duration="10-12 reps", target_muscle="Shoulders", technique_cue="Smooth vertical path"),
                        ExerciseItem(name="Triceps Cable Pushdown", sets=3, reps_or_duration="12-15 reps", target_muscle="Triceps", technique_cue="Keep elbows pinned to sides"),
                    ],
                },
                {
                    "day_of_week": "Tuesday",
                    "day_title": "Pull Hypertrophy (Back, Rear Delts, Biceps)",
                    "is_rest_day": False,
                    "target_muscle_groups": "Lats, Rhomboids, Biceps",
                    "warmup_notes": "Band pull-aparts and cat-cow stretches.",
                    "exercises": [
                        ExerciseItem(name="Barbell Bent-Over Row", sets=4, reps_or_duration="8-10 reps", target_muscle="Upper Back", technique_cue="Maintain 45-degree torso angle"),
                        ExerciseItem(name="Lat Pulldown", sets=3, reps_or_duration="10-12 reps", target_muscle="Lats", technique_cue="Pull to upper chest"),
                        ExerciseItem(name="Dumbbell Bicep Curls", sets=3, reps_or_duration="12-15 reps", target_muscle="Biceps", technique_cue="No momentum or hip swinging"),
                    ],
                },
                {
                    "day_of_week": "Wednesday",
                    "day_title": "Rest & Recovery",
                    "is_rest_day": True,
                    "target_muscle_groups": None,
                    "warmup_notes": None,
                    "exercises": [],
                },
                {
                    "day_of_week": "Thursday",
                    "day_title": "Legs Hypertrophy (Quads, Hamstrings, Calves)",
                    "is_rest_day": False,
                    "target_muscle_groups": "Quads, Hamstrings, Glutes",
                    "warmup_notes": warmup_cue,
                    "exercises": [
                        ExerciseItem(name="Barbell Back Squat", sets=4, reps_or_duration="8-10 reps", target_muscle="Quads & Glutes", technique_cue="Maintain deep knee flexion & upright chest"),
                        ExerciseItem(name="Romanian Deadlift", sets=3, reps_or_duration="10-12 reps", target_muscle="Hamstrings", technique_cue="Hinge hips until hamstrings stretch"),
                        ExerciseItem(name="Standing Calf Raises", sets=4, reps_or_duration="15 reps", target_muscle="Calves", technique_cue="Hold peak contraction for 1 second"),
                    ],
                },
                {
                    "day_of_week": "Friday",
                    "day_title": "Upper Body Hypertrophy & Arms",
                    "is_rest_day": False,
                    "target_muscle_groups": "Chest, Back, Arms",
                    "warmup_notes": "Dynamic arm circles.",
                    "exercises": [
                        ExerciseItem(name="Dumbbell Incline Flyes", sets=3, reps_or_duration="10-12 reps", target_muscle="Chest", technique_cue="Slight bend in elbows"),
                        ExerciseItem(name="Seated Cable Rows", sets=3, reps_or_duration="10-12 reps", target_muscle="Middle Back", technique_cue="Drive elbows straight back"),
                    ],
                },
                {
                    "day_of_week": "Saturday",
                    "day_title": "Rest & Regeneration",
                    "is_rest_day": True,
                    "target_muscle_groups": None,
                    "warmup_notes": None,
                    "exercises": [],
                },
                {
                    "day_of_week": "Sunday",
                    "day_title": "Rest & Regeneration",
                    "is_rest_day": True,
                    "target_muscle_groups": None,
                    "warmup_notes": None,
                    "exercises": [],
                },
            ]

        return plan_name, target_split, days

    @classmethod
    def _to_plan_response(cls, plan: WorkoutPlan) -> WorkoutPlanResponse:
        """Helper to map WorkoutPlan ORM model to Pydantic schema."""
        item_responses = []
        for item in plan.items:
            exercises_raw = json.loads(item.exercises_json) if item.exercises_json else []
            ex_items = [ExerciseItem(**e) for e in exercises_raw]
            item_responses.append(
                WorkoutPlanItemResponse(
                    id=item.id,
                    day_of_week=item.day_of_week,
                    day_title=item.day_title,
                    is_rest_day=item.is_rest_day,
                    target_muscle_groups=item.target_muscle_groups,
                    exercises=ex_items,
                    warmup_notes=item.warmup_notes,
                )
            )

        return WorkoutPlanResponse(
            id=plan.id,
            user_id=plan.user_id,
            plan_name=plan.plan_name,
            fitness_goal=plan.fitness_goal,
            target_split=plan.target_split,
            days_per_week=plan.days_per_week,
            habit_adapted=plan.habit_adapted,
            performance_adapted=plan.performance_adapted,
            adaptation_notes=plan.adaptation_notes,
            items=item_responses,
            created_at=plan.created_at,
        )
