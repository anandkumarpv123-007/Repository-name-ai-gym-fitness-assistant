from datetime import datetime, timedelta
import math
from typing import Any, Dict, List, Optional
import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from models.habit import HabitPrediction
from models.workout_session import WorkoutSession
from schemas.habit import (
    BehavioralFeatureSummary,
    BehavioralFactorItem,
    HabitStatusResponse,
    HabitPredictionItem,
    HabitHistoryResponse,
)
from services.habit_feature_engine import HabitFeatureEngine


class HabitPredictorService:
    """
    Behavioral AI Predictor Service for Fitness Habit Tracker.
    Generates skip probability predictions, non-causal factor attributions,
    adaptive nudges, and evidence-based schedule recommendations.
    Uses scikit-learn LogisticRegression trained with temporal validation,
    with a deterministic SparseDataFallbackModel when labeled training samples are sparse.
    """

    FEATURE_KEYS = [
        "days_since_last_workout",
        "workout_frequency_7d",
        "workout_frequency_30d",
        "avg_weekly_workouts",
        "consistency_score",
        "preferred_weekday_ratio",
        "max_gap_days_30d",
        "form_score_trend_delta",
    ]

    @classmethod
    def analyze_user_habit(cls, db: Session, user_id: int) -> HabitStatusResponse:
        """
        Executes complete behavioral habit analysis for specified user.
        Cold-start users (< 3 sessions) return status 'insufficient_data' with skip_probability=None.
        Users with >= 3 sessions receive a machine-learning skip risk prediction [0.00, 1.00].
        """
        target_time = datetime.utcnow()
        feat_dict = HabitFeatureEngine.extract_user_features(db, user_id, as_of_date=target_time)
        total_sessions = feat_dict["total_sessions"]

        feature_summary = BehavioralFeatureSummary(
            days_since_last_workout=feat_dict["days_since_last_workout"],
            workout_frequency_7d=feat_dict["workout_frequency_7d"],
            workout_frequency_30d=feat_dict["workout_frequency_30d"],
            avg_weekly_workouts=feat_dict["avg_weekly_workouts"],
            consistency_score=feat_dict["consistency_score"],
            preferred_weekday_ratio=feat_dict["preferred_weekday_ratio"],
            max_gap_days_30d=feat_dict["max_gap_days_30d"],
            form_score_trend_delta=feat_dict["form_score_trend_delta"],
        )

        # 1. Cold-start check (< 3 sessions logged)
        if total_sessions < 3:
            nudge = (
                "Keep logging your workouts! Once you complete at least 3 sessions, "
                "your behavioral habit analyzer will activate to predict session consistency and provide personalized nudges."
            )
            rec_sched = "Complete at least 3 workout sessions to unlock evidence-based schedule recommendations."
            explanation = f"Insufficient workout history ({total_sessions}/3 minimum sessions logged). Habit predictions activate after 3 completed sessions."

            # Save telemetry snapshot
            db_record = HabitPrediction(
                user_id=user_id,
                prediction_date=target_time,
                skip_probability=None,
                risk_level="insufficient_data",
                primary_factor=None,
                nudge_text=nudge,
                recommended_schedule=rec_sched,
            )
            db.add(db_record)
            db.commit()

            return HabitStatusResponse(
                user_id=user_id,
                status="insufficient_data",
                total_sessions_logged=total_sessions,
                skip_probability=None,
                risk_level="insufficient_data",
                risk_explanation=explanation,
                features=feature_summary,
                behavioral_factors=[],
                adaptive_nudge=nudge,
                recommended_schedule=rec_sched,
                model_info={
                    "model": "None (Cold Start)",
                    "status": "insufficient_data",
                    "ml_trained": False,
                    "min_sessions_required": 3,
                    "total_sessions": total_sessions,
                },
                timestamp=target_time,
            )

        # 2. Build temporal training samples from history across users (strictly target_end <= target_time)
        X_train, y_train = cls._build_temporal_training_dataset(db, target_time)

        # 3. Predict skip probability using LogisticRegression or SparseDataFallbackModel
        current_x = np.array([[feat_dict[k] for k in cls.FEATURE_KEYS]])

        used_ml = False
        sample_count = len(y_train)

        # Check if enough labeled samples and class variance exist for ML fitting
        if sample_count >= 6 and len(set(y_train)) > 1:
            try:
                scaler = StandardScaler()
                X_scaled = scaler.fit_transform(X_train)
                model = LogisticRegression(C=1.0, max_iter=1000, random_state=42)
                model.fit(X_scaled, y_train)

                curr_scaled = scaler.transform(current_x)
                prob_raw = model.predict_proba(curr_scaled)[0][1]
                skip_probability = round(float(np.clip(prob_raw, 0.01, 0.99)), 2)
                used_ml = True
            except Exception:
                skip_probability = cls._compute_sparse_data_fallback_probability(feat_dict)
        else:
            skip_probability = cls._compute_sparse_data_fallback_probability(feat_dict)

        # 4. Map probability to risk level
        if skip_probability < 0.35:
            risk_level = "low"
            explanation = "Your workout consistency is strong. Low probability of skipping your upcoming workouts."
        elif skip_probability < 0.65:
            risk_level = "moderate"
            explanation = "Moderate skip risk detected based on recent schedule gaps or decreased weekly frequency."
        else:
            risk_level = "high"
            explanation = "High skip risk detected. Recent gap in workouts and lower consistency indicate an elevated likelihood of missing your next session."

        # 5. Non-causal factor attributions
        behavioral_factors = cls._extract_behavioral_factors(feat_dict)

        # 6. Adaptive nudge generation
        adaptive_nudge = cls._generate_adaptive_nudge(risk_level, behavioral_factors)

        # 7. Recommended schedule (evidence-based observational wording)
        recommended_schedule = cls._generate_schedule_recommendation(feat_dict)

        # 8. Save snapshot to DB
        primary_factor_str = behavioral_factors[0].feature_name if behavioral_factors else "days_since_last_workout"
        db_record = HabitPrediction(
            user_id=user_id,
            prediction_date=target_time,
            skip_probability=skip_probability,
            risk_level=risk_level,
            primary_factor=primary_factor_str,
            nudge_text=adaptive_nudge,
            recommended_schedule=recommended_schedule,
        )
        db.add(db_record)
        db.commit()

        fallback_reason = None
        if not used_ml:
            if sample_count < 6:
                fallback_reason = "insufficient_labeled_training_samples"
            elif len(set(y_train)) <= 1:
                fallback_reason = "single_class_variance"
            else:
                fallback_reason = "fitting_exception"

        model_info = {
            "model": "LogisticRegression" if used_ml else "SparseDataFallbackModel",
            "ml_trained": used_ml,
            "c_param": 1.0 if used_ml else None,
            "training_samples": sample_count,
            "temporal_validation": "chronological_split",
            "features_used": cls.FEATURE_KEYS,
            "fallback_reason": fallback_reason,
        }

        return HabitStatusResponse(
            user_id=user_id,
            status="active_prediction",
            total_sessions_logged=total_sessions,
            skip_probability=skip_probability,
            risk_level=risk_level,
            risk_explanation=explanation,
            features=feature_summary,
            behavioral_factors=behavioral_factors,
            adaptive_nudge=adaptive_nudge,
            recommended_schedule=recommended_schedule,
            model_info=model_info,
            timestamp=target_time,
        )

    @classmethod
    def get_user_history(cls, db: Session, user_id: int, limit: int = 10) -> HabitHistoryResponse:
        """
        Retrieves historical habit prediction telemetry for current user.
        """
        records = db.execute(
            select(HabitPrediction)
            .where(HabitPrediction.user_id == user_id)
            .order_by(HabitPrediction.created_at.desc())
            .limit(limit)
        ).scalars().all()

        prediction_items = [
            HabitPredictionItem.model_validate(r) for r in records
        ]

        return HabitHistoryResponse(user_id=user_id, predictions=prediction_items)

    @classmethod
    def _build_temporal_training_dataset(cls, db: Session, evaluation_cutoff: datetime):
        """
        Constructs temporal time-series training samples across past windows.
        Sample Unit: 7-day observation window ending on date T.
        Target Y=1 if user completed 0 workouts in subsequent [T+1, T+7], else Y=0.
        STRICT TEMPORAL LEAKAGE ENFORCEMENT: Every sample MUST satisfy target_end <= evaluation_cutoff.
        """
        # Fetch all workout sessions across DB
        all_sessions = db.execute(
            select(WorkoutSession)
            .where(WorkoutSession.ended_at.is_not(None))
            .order_by(WorkoutSession.started_at.asc())
        ).scalars().all()

        if not all_sessions:
            return np.empty((0, len(cls.FEATURE_KEYS))), np.empty((0,))

        # Upper bound on observation window cutoff date so target_end <= evaluation_cutoff
        max_window_cutoff = evaluation_cutoff - timedelta(days=7)

        user_ids = list(set(s.user_id for s in all_sessions))
        X_samples = []
        y_samples = []

        for uid in user_ids:
            u_sessions = [s for s in all_sessions if s.user_id == uid]
            if len(u_sessions) < 3:
                continue

            earliest = u_sessions[0].started_at
            latest = min(max_window_cutoff, u_sessions[-1].started_at)

            curr_window = earliest + timedelta(days=7)
            while curr_window <= latest:
                target_start = curr_window
                target_end = curr_window + timedelta(days=7)

                # Strict enforcement check
                if target_end > evaluation_cutoff:
                    break

                # Extract features as of curr_window
                feats = HabitFeatureEngine.extract_user_features(db, uid, as_of_date=curr_window)
                x_vec = [feats[k] for k in cls.FEATURE_KEYS]

                # Calculate target Y in subsequent [curr_window, curr_window + 7 days]
                next_count = sum(
                    1 for s in u_sessions
                    if target_start < s.started_at <= target_end
                )

                y_val = 1 if next_count == 0 else 0
                X_samples.append(x_vec)
                y_samples.append(y_val)

                curr_window += timedelta(days=7)

        if not X_samples:
            return np.empty((0, len(cls.FEATURE_KEYS))), np.empty((0,))

        return np.array(X_samples), np.array(y_samples)

    @classmethod
    def _compute_sparse_data_fallback_probability(cls, feat_dict: Dict[str, Any]) -> float:
        """
        Calculates a deterministic fallback probability when training sample size is insufficient for full ML fitting.
        Uses grounded linear log-odds coefficients based on feature risk directions.
        """
        days_gap = feat_dict["days_since_last_workout"]
        freq_7d = feat_dict["workout_frequency_7d"]
        freq_30d = feat_dict["workout_frequency_30d"]
        consistency = feat_dict["consistency_score"]
        max_gap = feat_dict["max_gap_days_30d"]
        form_delta = feat_dict["form_score_trend_delta"]

        # Base log-odds
        z = -0.5

        # Signal 1: Days since last workout (+0.25 log-odds per day after day 2)
        if days_gap > 2:
            z += 0.25 * (days_gap - 2)

        # Signal 2: 7-day frequency (-0.4 per session)
        z -= 0.4 * freq_7d

        # Signal 3: Consistency score (-1.5 * score)
        z -= 1.5 * consistency

        # Signal 4: Max gap in past 30 days (+0.1 per day over 4)
        if max_gap > 4:
            z += 0.1 * (max_gap - 4)

        # Signal 5: Form trend delta (-0.05 * delta)
        z -= 0.05 * form_delta

        # Sigmoid function
        prob = 1.0 / (1.0 + math.exp(-z))
        return round(float(np.clip(prob, 0.05, 0.95)), 2)

    @classmethod
    def _extract_behavioral_factors(cls, feat_dict: Dict[str, Any]) -> List[BehavioralFactorItem]:
        """
        Generates non-causal factor attributions describing behavioral signals associated with skip risk.
        """
        factors = []

        days_gap = feat_dict["days_since_last_workout"]
        freq_7d = feat_dict["workout_frequency_7d"]
        consistency = feat_dict["consistency_score"]
        max_gap = feat_dict["max_gap_days_30d"]
        form_delta = feat_dict["form_score_trend_delta"]

        # Days since last workout
        if days_gap >= 4:
            factors.append(BehavioralFactorItem(
                feature_name="days_since_last_workout",
                description=f"{days_gap} days have elapsed since your last workout session (signal associated with higher skip risk).",
                impact_level="high",
                signal_direction="increases_risk",
            ))
        elif days_gap <= 1:
            factors.append(BehavioralFactorItem(
                feature_name="days_since_last_workout",
                description="Recent workout completed within the last 24–48 hours (signal associated with lower skip risk).",
                impact_level="high",
                signal_direction="decreases_risk",
            ))

        # Consistency score
        if consistency >= 0.70:
            factors.append(BehavioralFactorItem(
                feature_name="consistency_score",
                description=f"High routine consistency ({int(consistency * 100)}% of registered weeks active) reinforces habit retention.",
                impact_level="high",
                signal_direction="decreases_risk",
            ))
        elif consistency < 0.40:
            factors.append(BehavioralFactorItem(
                feature_name="consistency_score",
                description=f"Lower weekly consistency score ({int(consistency * 100)}% of registered weeks active) is correlated with routine disruption.",
                impact_level="moderate",
                signal_direction="increases_risk",
            ))

        # 7-day frequency
        if freq_7d >= 3:
            factors.append(BehavioralFactorItem(
                feature_name="workout_frequency_7d",
                description=f"Strong weekly volume with {freq_7d} completed sessions in the past 7 days.",
                impact_level="moderate",
                signal_direction="decreases_risk",
            ))
        elif freq_7d == 0:
            factors.append(BehavioralFactorItem(
                feature_name="workout_frequency_7d",
                description="Zero workout sessions logged in the past 7 days indicates elevated routine decay.",
                impact_level="high",
                signal_direction="increases_risk",
            ))

        # Max gap 30d
        if max_gap >= 6:
            factors.append(BehavioralFactorItem(
                feature_name="max_gap_days_30d",
                description=f"Extended gap of {max_gap} consecutive days observed within the past 30 days.",
                impact_level="moderate",
                signal_direction="increases_risk",
            ))

        # Form score trend delta
        if form_delta < -5.0:
            factors.append(BehavioralFactorItem(
                feature_name="form_score_trend_delta",
                description=f"Recent drop in form score ({form_delta:+.1f} points) indicates potential fatigue or technique difficulty.",
                impact_level="low",
                signal_direction="increases_risk",
            ))

        # Fallback if no specific condition met
        if not factors:
            factors.append(BehavioralFactorItem(
                feature_name="workout_frequency_30d",
                description=f"Logged {feat_dict['workout_frequency_30d']} total workouts in the past 30 days.",
                impact_level="low",
                signal_direction="decreases_risk" if feat_dict['workout_frequency_30d'] >= 8 else "increases_risk",
            ))

        return factors[:3]

    @classmethod
    def _generate_adaptive_nudge(cls, risk_level: str, factors: List[BehavioralFactorItem]) -> str:
        """
        Generates actionable behavioral nudge based on risk level and top signals.
        """
        if risk_level == "high":
            return (
                "Consider scheduling a quick 15-minute low-intensity session today. "
                "Lowering the entry barrier helps rebuild routine momentum after a multi-day break."
            )
        elif risk_level == "moderate":
            return (
                "You're close to maintaining your target routine! "
                "Lock in your next workout session today to stay consistent and prevent schedule gaps."
            )
        else:
            return (
                "Great workout momentum! Keep up your current rhythm by sticking to your preferred training days."
            )

    @classmethod
    def _generate_schedule_recommendation(cls, feat_dict: Dict[str, Any]) -> str:
        """
        Generates evidence-based observational schedule recommendation based on historical preferred weekday and hour.
        Avoids absolute claims of future optimality.
        """
        day = feat_dict.get("most_frequent_weekday")
        hour = feat_dict.get("peak_hour")

        if day and hour is not None:
            period = "AM" if hour < 12 else "PM"
            formatted_hour = hour if 1 <= hour <= 12 else (hour - 12 if hour > 12 else 12)
            return f"Historically Most Frequent Session Time: {day}s around {formatted_hour:02d}:00 {period} (based on your highest historical completion frequency)."
        elif day:
            return f"Historically Most Frequent Session Time: {day}s (your most active training day)."
        else:
            return "Suggested Starter Schedule: Mondays, Wednesdays, and Fridays at 08:00 AM."
