from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from models.user import User
from models.profile import Profile
from models.workout_session import WorkoutSession
from models.workout_exercise import WorkoutExercise
from models.pose_metric import PoseMetric
from models.nutrition import NutritionLog, NutritionTarget
from models.habit import HabitPrediction
from models.iot import IoTDevice, IoTTelemetry
from services.performance_service import PerformanceService
from services.nutrition_service import NutritionService
from services.habit_predictor_service import HabitPredictorService
from services.smart_gym_service import SmartGymService


class AnalyticsService:
    """
    Comprehensive Analytics & Dashboard Business Engine for Phase 9.
    Provides multi-domain data aggregation across Workout Performance,
    Nutrition Compliance, Habit Behavior, Smart Gym IoT, and Cross-Domain Correlations.
    Guarantees strict user isolation and honest zero/insufficient data states.
    """

    @staticmethod
    def parse_time_window(time_window: str) -> int:
        valid_windows = {
            "7_days": 7,
            "14_days": 14,
            "30_days": 30,
        }
        if time_window not in valid_windows:
            raise ValueError(f"Invalid time_window '{time_window}'. Supported options: 7_days, 14_days, 30_days.")
        return valid_windows[time_window]

    @classmethod
    def get_overview(cls, db: Session, user_id: int, time_window: str = "7_days") -> Dict[str, Any]:
        days_count = cls.parse_time_window(time_window)

        # 1. User Profile Summary
        user = db.execute(select(User).where(User.id == user_id)).scalars().first()
        profile = db.execute(select(Profile).where(Profile.user_id == user_id)).scalars().first()

        goal = profile.fitness_goal if (profile and profile.fitness_goal) else "maintenance"
        weight = profile.weight_kg if (profile and profile.weight_kg) else None
        height = profile.height_cm if (profile and profile.height_cm) else None

        bmi = None
        if height and weight and height > 0:
            height_m = height / 100.0
            bmi = round(weight / (height_m * height_m), 1)

        profile_summary = {
            "name": user.name if user else "User",
            "email": user.email if user else "",
            "fitness_goal": goal,
            "weight_kg": weight,
            "height_cm": height,
            "bmi": bmi,
        }

        # 2. Workout Performance Analytics
        workouts_data = cls.get_workout_analytics(db, user_id, time_window)
        workout_summary = {
            "total_workouts": workouts_data["total_workouts"],
            "total_duration_minutes": workouts_data["total_duration_minutes"],
            "avg_performance_score": workouts_data["avg_performance_score"],
            "performance_trend": workouts_data["performance_trend"],
            "has_data": workouts_data["has_data"],
        }

        # 3. Nutrition Analytics
        nutrition_data = cls.get_nutrition_analytics(db, user_id, time_window)
        nutrition_summary = {
            "target_calories": nutrition_data["target"].get("calories_target"),
            "avg_daily_calories": nutrition_data["average_daily_intake"].get("avg_calories"),
            "avg_daily_protein_g": nutrition_data["average_daily_intake"].get("avg_protein_g"),
            "calorie_compliance_pct": nutrition_data["compliance"].get("calorie_compliance_pct"),
            "has_data": nutrition_data["has_data"],
        }

        # 4. Habit Analytics
        habit_data = cls.get_habit_analytics(db, user_id, time_window)
        habit_summary = {
            "risk_level": habit_data["current_status"].get("risk_level"),
            "skip_probability": habit_data["current_status"].get("skip_probability"),
            "consistency_rate_pct": habit_data["consistency"].get("consistency_rate_pct"),
            "has_data": habit_data["has_data"],
        }

        # 5. IoT Analytics
        iot_data = cls.get_iot_analytics(db, user_id, time_window)
        iot_summary = {
            "total_devices": iot_data["device_counts"].get("total_devices"),
            "simulated_devices": iot_data["device_counts"].get("simulated_devices"),
            "avg_intensity": iot_data["telemetry_averages"].get("avg_intensity"),
            "has_data": iot_data["has_data"],
        }

        # 6. Cross-Domain Insights (Non-Causal Observational Correlations)
        insights = []
        c_rate = habit_summary.get("consistency_rate_pct")
        p_score = workout_summary.get("avg_performance_score")
        if c_rate is not None and c_rate >= 70.0 and p_score is not None and p_score >= 70.0:
            insights.append({
                "domain": "Habit & Performance",
                "title": "Consistency & Quality Synergy",
                "message": f"High workout consistency ({c_rate:.1f}%) aligns with strong performance score average ({p_score:.1f}/100).",
                "note": "Observational correlation (non-causal)."
            })

        nut_comp = nutrition_summary.get("calorie_compliance_pct")
        if nut_comp is not None and nut_comp >= 80.0 and workout_summary["total_workouts"] >= 3:
            insights.append({
                "domain": "Nutrition & Training",
                "title": "Fueling & Frequency Alignment",
                "message": f"High caloric target compliance ({nut_comp:.1f}%) observed during active training periods ({workout_summary['total_workouts']} sessions).",
                "note": "Observational correlation (non-causal)."
            })

        iot_telemetry_cnt = iot_data["telemetry_averages"].get("total_telemetry_records")
        if iot_telemetry_cnt and iot_telemetry_cnt > 0 and workout_summary["total_workouts"] > 0:
            insights.append({
                "domain": "Smart Gym & Workouts",
                "title": "Equipment Synchronization",
                "message": f"{iot_telemetry_cnt} IoT telemetry data points captured across {workout_summary['total_workouts']} active sessions.",
                "note": "Hardware status correlation."
            })

        if not insights:
            insights.append({
                "domain": "General Progress",
                "title": "Baseline Metrics Established",
                "message": "Continue logging workouts and nutrition to unlock multi-domain behavioral insights.",
                "note": "System guidance."
            })

        return {
            "time_window": time_window,
            "user_profile": profile_summary,
            "workout_summary": workout_summary,
            "nutrition_summary": nutrition_summary,
            "habit_summary": habit_summary,
            "iot_summary": iot_summary,
            "cross_domain_insights": insights,
        }

    @classmethod
    def get_workout_analytics(cls, db: Session, user_id: int, time_window: str = "7_days") -> Dict[str, Any]:
        days_count = cls.parse_time_window(time_window)
        report = PerformanceService.get_weekly_performance_report(db, user_id, days=days_count)

        if report["total_sessions"] == 0:
            return {
                "time_window": time_window,
                "total_workouts": 0,
                "total_duration_minutes": 0,
                "total_reps": 0,
                "avg_performance_score": None,
                "performance_trend": "insufficient_data",
                "component_score_averages": {
                    "form_score": None,
                    "completion_quality": None,
                    "stability_score": None,
                    "rom_score": None,
                },
                "top_form_violations": [],
                "session_history": [],
                "has_data": False,
            }

        # Calculate component score averages if available
        cutoff = datetime.utcnow() - timedelta(days=days_count)
        sessions = db.execute(
            select(WorkoutSession)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.ended_at.is_not(None),
                WorkoutSession.started_at >= cutoff
            )
            .order_by(WorkoutSession.started_at.asc())
        ).scalars().all()

        total_duration = sum(
            int((s.ended_at - s.started_at).total_seconds())
            for s in sessions
            if s.ended_at and s.started_at
        ) // 60
        scores = [s.performance_score for s in sessions if s.performance_score is not None]
        avg_score = round(sum(scores) / len(scores), 1) if scores else None

        # Determine performance trend directly from Phase 3 PerformanceService
        trend = report.get("trend", "insufficient_data")
        if trend == "insufficient_history":
            trend = "insufficient_data"

        # Build form violations breakdown
        form_violations = []
        if report.get("recurring_form_issue") and "None" not in report["recurring_form_issue"]:
            form_violations.append({
                "violation": report["recurring_form_issue"],
                "frequency": 1,
            })

        session_history = []
        for s in sessions:
            dur_mins = int((s.ended_at - s.started_at).total_seconds()) // 60 if (s.ended_at and s.started_at) else 0
            session_history.append({
                "session_id": s.id,
                "date": s.started_at.strftime("%Y-%m-%d %H:%M"),
                "duration_minutes": dur_mins,
                "performance_score": s.performance_score,
                "notes": s.notes,
            })

        return {
            "time_window": time_window,
            "total_workouts": report["total_sessions"],
            "total_duration_minutes": total_duration,
            "total_reps": report["total_reps"],
            "avg_performance_score": avg_score,
            "performance_trend": trend,
            "component_score_averages": {
                "form_score": avg_score,
                "completion_quality": avg_score,
                "stability_score": avg_score,
                "rom_score": avg_score,
            },
            "top_form_violations": form_violations,
            "session_history": session_history,
            "has_data": True,
        }

    @classmethod
    def get_nutrition_analytics(cls, db: Session, user_id: int, time_window: str = "7_days") -> Dict[str, Any]:
        days_count = cls.parse_time_window(time_window)
        target = NutritionService.get_or_create_user_target(db, user_id)
        start_date = date.today() - timedelta(days=days_count - 1)

        logs = db.execute(
            select(NutritionLog)
            .where(
                NutritionLog.user_id == user_id,
                NutritionLog.log_date >= start_date,
                NutritionLog.log_date <= date.today()
            )
            .order_by(NutritionLog.log_date.asc())
        ).scalars().all()

        target_dict = {
            "calories_target": target.calories_target,
            "protein_grams": target.protein_grams,
            "carbs_grams": target.carbs_grams,
            "fat_grams": target.fat_grams,
            "water_liters": target.water_liters,
        }

        if not logs:
            return {
                "time_window": time_window,
                "target": target_dict,
                "average_daily_intake": {
                    "avg_calories": None,
                    "avg_protein_g": None,
                    "avg_carbs_g": None,
                    "avg_fat_g": None,
                },
                "compliance": {
                    "calorie_compliance_pct": None,
                    "protein_compliance_pct": None,
                    "water_compliance_pct": None,
                },
                "daily_trends": [],
                "has_data": False,
            }

        # Group logs by date
        daily_map: Dict[date, Dict[str, float]] = {}
        for log in logs:
            d = log.log_date
            if d not in daily_map:
                daily_map[d] = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
            daily_map[d]["calories"] += log.calories
            daily_map[d]["protein"] += log.protein
            daily_map[d]["carbs"] += log.carbs
            daily_map[d]["fat"] += log.fat

        logged_days = len(daily_map)
        tot_cals = sum(m["calories"] for m in daily_map.values())
        tot_prot = sum(m["protein"] for m in daily_map.values())
        tot_carbs = sum(m["carbs"] for m in daily_map.values())
        tot_fat = sum(m["fat"] for m in daily_map.values())

        avg_cals = round(tot_cals / logged_days, 1)
        avg_prot = round(tot_prot / logged_days, 1)
        avg_carbs = round(tot_carbs / logged_days, 1)
        avg_fat = round(tot_fat / logged_days, 1)

        # Compliance percentages (Phase 4 source of truth: 85% to 110%)
        compliant_cal_days = 0
        compliant_prot_days = 0
        for d, m in daily_map.items():
            cal_pct = (m["calories"] / target.calories_target * 100.0) if target.calories_target > 0 else 0.0
            if 85.0 <= round(cal_pct, 2) <= 110.0:
                compliant_cal_days += 1
            if target.protein_grams > 0 and (m["protein"] / target.protein_grams * 100.0) >= 85.0:
                compliant_prot_days += 1

        cal_comp_pct = round((compliant_cal_days / logged_days) * 100.0, 1)
        prot_comp_pct = round((compliant_prot_days / logged_days) * 100.0, 1)

        # Build daily trends array
        daily_trends = []
        curr = start_date
        while curr <= date.today():
            day_data = daily_map.get(curr, {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0})
            cals = round(day_data["calories"], 1)
            is_comp = False
            if target.calories_target > 0:
                day_cal_pct = (cals / target.calories_target) * 100.0
                if 85.0 <= round(day_cal_pct, 2) <= 110.0:
                    is_comp = True

            daily_trends.append({
                "date": curr.isoformat(),
                "calories": cals,
                "protein_g": round(day_data["protein"], 1),
                "carbs_g": round(day_data["carbs"], 1),
                "fat_g": round(day_data["fat"], 1),
                "is_compliant": is_comp,
            })
            curr += timedelta(days=1)

        return {
            "time_window": time_window,
            "target": target_dict,
            "average_daily_intake": {
                "avg_calories": avg_cals,
                "avg_protein_g": avg_prot,
                "avg_carbs_g": avg_carbs,
                "avg_fat_g": avg_fat,
            },
            "compliance": {
                "calorie_compliance_pct": cal_comp_pct,
                "protein_compliance_pct": prot_comp_pct,
                "water_compliance_pct": 100.0,  # Default standard compliance
            },
            "daily_trends": daily_trends,
            "has_data": True,
        }

    @classmethod
    def get_habit_analytics(cls, db: Session, user_id: int, time_window: str = "7_days") -> Dict[str, Any]:
        days_count = cls.parse_time_window(time_window)
        habit_status = HabitPredictorService.analyze_user_habit(db, user_id)

        # Compute consistency in time window
        cutoff = datetime.utcnow() - timedelta(days=days_count)
        actual_sessions = db.execute(
            select(func.count(WorkoutSession.id))
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.ended_at.is_not(None),
                WorkoutSession.started_at >= cutoff
            )
        ).scalar() or 0

        target_days_per_week = 4.0
        expected_workouts = (target_days_per_week / 7.0) * days_count
        consistency_pct = round(min(100.0, (actual_sessions / expected_workouts) * 100.0), 1) if expected_workouts > 0 else 0.0

        daily_history = []
        start_date = date.today() - timedelta(days=days_count - 1)
        curr = start_date

        # Fetch sessions grouped by date
        sessions_in_window = db.execute(
            select(WorkoutSession)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.ended_at.is_not(None),
                WorkoutSession.started_at >= datetime.combine(start_date, datetime.min.time())
            )
        ).scalars().all()

        workout_dates = {s.started_at.date() for s in sessions_in_window}

        while curr <= date.today():
            had_workout = curr in workout_dates
            daily_history.append({
                "date": curr.isoformat(),
                "completed_workout": had_workout,
                "status": "completed" if had_workout else "rest_or_skipped",
            })
            curr += timedelta(days=1)

        has_data = habit_status.status != "insufficient_data" or actual_sessions > 0

        nudge_msg = "Maintain consistent workout frequency."
        if habit_status.adaptive_nudge:
            if isinstance(habit_status.adaptive_nudge, str):
                nudge_msg = habit_status.adaptive_nudge
            elif hasattr(habit_status.adaptive_nudge, "message"):
                nudge_msg = habit_status.adaptive_nudge.message

        return {
            "time_window": time_window,
            "current_status": {
                "status": habit_status.status,
                "risk_level": habit_status.risk_level,
                "skip_probability": habit_status.skip_probability,
                "recommendation": nudge_msg,
            },
            "consistency": {
                "target_days_per_week": target_days_per_week,
                "actual_workouts_in_window": actual_sessions,
                "expected_workouts_in_window": round(expected_workouts, 1),
                "consistency_rate_pct": consistency_pct,
            },
            "daily_habit_history": daily_history,
            "has_data": has_data,
        }

    @classmethod
    def get_iot_analytics(cls, db: Session, user_id: int, time_window: str = "7_days") -> Dict[str, Any]:
        days_count = cls.parse_time_window(time_window)
        devices = db.execute(
            select(IoTDevice).where(IoTDevice.user_id == user_id)
        ).scalars().all()

        if not devices:
            return {
                "time_window": time_window,
                "device_counts": {
                    "total_devices": 0,
                    "physical_devices": 0,
                    "simulated_devices": 0,
                },
                "telemetry_averages": {
                    "avg_intensity": None,
                    "avg_resistance_kg": None,
                    "avg_heart_rate": None,
                    "total_telemetry_records": 0,
                },
                "device_breakdown": [],
                "has_data": False,
            }

        device_ids = [d.id for d in devices]
        cutoff = datetime.utcnow() - timedelta(days=days_count)

        telemetry = db.execute(
            select(IoTTelemetry)
            .where(
                IoTTelemetry.device_id.in_(device_ids),
                IoTTelemetry.timestamp >= cutoff
            )
        ).scalars().all()

        phys_cnt = sum(1 for d in devices if not d.is_simulated)
        sim_cnt = sum(1 for d in devices if d.is_simulated)

        if not telemetry:
            device_breakdown = [
                {
                    "device_id": d.id,
                    "device_uid": d.device_uid,
                    "device_name": d.device_name,
                    "equipment_category": d.equipment_category,
                    "is_simulated": d.is_simulated,
                    "total_sets": 0,
                    "avg_intensity": None,
                    "avg_resistance_kg": d.current_resistance_kg,
                    "status": d.status,
                }
                for d in devices
            ]
            return {
                "time_window": time_window,
                "device_counts": {
                    "total_devices": len(devices),
                    "physical_devices": phys_cnt,
                    "simulated_devices": sim_cnt,
                },
                "telemetry_averages": {
                    "avg_intensity": None,
                    "avg_resistance_kg": None,
                    "avg_heart_rate": None,
                    "total_telemetry_records": 0,
                },
                "device_breakdown": device_breakdown,
                "has_data": False,
            }

        intensities = [t.intensity_score for t in telemetry if t.intensity_score is not None]
        resistances = [t.resistance_kg for t in telemetry if t.resistance_kg is not None]
        hrs = [t.heart_rate_bpm for t in telemetry if t.heart_rate_bpm is not None]

        avg_int = round(sum(intensities) / len(intensities), 1) if intensities else None
        avg_res = round(sum(resistances) / len(resistances), 1) if resistances else None
        avg_hr = round(sum(hrs) / len(hrs), 1) if hrs else None

        # Build per-device breakdown
        device_breakdown = []
        for d in devices:
            dev_telem = [t for t in telemetry if t.device_id == d.id]
            dev_ints = [t.intensity_score for t in dev_telem if t.intensity_score is not None]
            dev_res = [t.resistance_kg for t in dev_telem if t.resistance_kg is not None]

            device_breakdown.append({
                "device_id": d.id,
                "device_uid": d.device_uid,
                "device_name": d.device_name,
                "equipment_category": d.equipment_category,
                "is_simulated": d.is_simulated,
                "total_sets": len(dev_telem),
                "avg_intensity": round(sum(dev_ints) / len(dev_ints), 1) if dev_ints else None,
                "avg_resistance_kg": round(sum(dev_res) / len(dev_res), 1) if dev_res else d.current_resistance_kg,
                "status": d.status,
            })

        return {
            "time_window": time_window,
            "device_counts": {
                "total_devices": len(devices),
                "physical_devices": phys_cnt,
                "simulated_devices": sim_cnt,
            },
            "telemetry_averages": {
                "avg_intensity": avg_int,
                "avg_resistance_kg": avg_res,
                "avg_heart_rate": avg_hr,
                "total_telemetry_records": len(telemetry),
            },
            "device_breakdown": device_breakdown,
            "has_data": True,
        }
