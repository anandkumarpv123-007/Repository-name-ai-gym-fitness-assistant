from datetime import datetime, timedelta, date
from collections import Counter
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.workout_session import WorkoutSession
from models.user import User


class HabitFeatureEngine:
    """
    Behavioral Feature Generation Layer for Fitness Habit Tracker.
    Extracts 8 deterministic behavioral features strictly from actual database records.
    Prevents temporal data leakage by enforcing an upper cutoff boundary (as_of_date).
    """

    @classmethod
    def extract_user_features(
        cls,
        db: Session,
        user_id: int,
        as_of_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Extracts behavioral feature vector for user as of target evaluation timestamp as_of_date.
        """
        target_time = as_of_date or datetime.utcnow()

        # Fetch all completed workout sessions strictly on or before target_time
        sessions = db.execute(
            select(WorkoutSession)
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.ended_at.is_not(None),
                WorkoutSession.started_at <= target_time,
            )
            .order_by(WorkoutSession.started_at.asc())
        ).scalars().all()

        total_sessions = len(sessions)

        if total_sessions == 0:
            return {
                "total_sessions": 0,
                "days_since_last_workout": 999,
                "workout_frequency_7d": 0,
                "workout_frequency_30d": 0,
                "avg_weekly_workouts": 0.0,
                "consistency_score": 0.0,
                "preferred_weekday_ratio": 0.0,
                "max_gap_days_30d": 0,
                "form_score_trend_delta": 0.0,
                "most_frequent_weekday": None,
                "peak_hour": None,
            }

        # 1. Days since last workout
        last_session = sessions[-1]
        days_since_last = max(0, (target_time - last_session.started_at).days)

        # 2. Workout frequency in past 7 days & 30 days
        cutoff_7d = target_time - timedelta(days=7)
        cutoff_30d = target_time - timedelta(days=30)
        cutoff_60d = target_time - timedelta(days=60)

        freq_7d = sum(1 for s in sessions if s.started_at >= cutoff_7d)
        freq_30d = sum(1 for s in sessions if s.started_at >= cutoff_30d)
        sessions_60d = [s for s in sessions if s.started_at >= cutoff_60d]

        # 3. User account creation & average weekly workouts
        user = db.execute(select(User).where(User.id == user_id)).scalars().first()
        created_at = user.created_at if (user and user.created_at) else sessions[0].started_at
        days_registered = max(1, (target_time - created_at).days)
        weeks_registered = max(1.0, days_registered / 7.0)

        avg_weekly = round(total_sessions / weeks_registered, 2)

        # 4. Consistency score (ratio of active calendar weeks with >= 1 workout)
        active_weeks = set()
        for s in sessions:
            # ISO year & week
            yw = s.started_at.isocalendar()[:2]
            active_weeks.add(yw)

        total_possible_weeks = max(1, int(weeks_registered))
        consistency_ratio = round(min(1.0, len(active_weeks) / total_possible_weeks), 2)

        # 5. Preferred weekday ratio & peak workout hour
        if sessions_60d:
            weekdays = [s.started_at.strftime("%A") for s in sessions_60d]
            hours = [s.started_at.hour for s in sessions_60d]
            day_counts = Counter(weekdays)
            hour_counts = Counter(hours)

            top_day, top_day_count = day_counts.most_common(1)[0]
            top_hour, _ = hour_counts.most_common(1)[0]
            preferred_weekday_ratio = round(top_day_count / len(sessions_60d), 2)
        else:
            top_day = None
            top_hour = None
            preferred_weekday_ratio = 0.0

        # 6. Max consecutive gap in past 30 days
        recent_30d_sessions = [s for s in sessions if s.started_at >= cutoff_30d]
        max_gap = 0
        if len(recent_30d_sessions) >= 2:
            gaps = [
                (recent_30d_sessions[i].started_at - recent_30d_sessions[i-1].started_at).days
                for i in range(1, len(recent_30d_sessions))
            ]
            max_gap = max(gaps) if gaps else 0
        elif len(recent_30d_sessions) == 1:
            max_gap = (target_time - recent_30d_sessions[0].started_at).days

        # 7. Form score trend delta (recent 2 vs prior 2)
        scores = [s.performance_score for s in sessions if s.performance_score is not None]
        if len(scores) >= 4:
            recent_avg = (scores[-1] + scores[-2]) / 2.0
            prior_avg = (scores[-3] + scores[-4]) / 2.0
            form_delta = round(recent_avg - prior_avg, 1)
        else:
            form_delta = 0.0

        return {
            "total_sessions": total_sessions,
            "days_since_last_workout": days_since_last,
            "workout_frequency_7d": freq_7d,
            "workout_frequency_30d": freq_30d,
            "avg_weekly_workouts": avg_weekly,
            "consistency_score": consistency_ratio,
            "preferred_weekday_ratio": preferred_weekday_ratio,
            "max_gap_days_30d": max_gap,
            "form_score_trend_delta": form_delta,
            "most_frequent_weekday": top_day,
            "peak_hour": top_hour,
        }
