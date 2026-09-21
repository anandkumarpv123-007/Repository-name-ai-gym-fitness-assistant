"""
AI Gym & Fitness Assistant — Longitudinal Performance Service
Phase 3 — Pose-to-Performance Analyzer & Weekly Progress Intelligence

Provides deterministic, explainable aggregation, trend evaluation, 
measurable improvement identification, recurring form issue analysis,
and actionable weekly fitness coaching guidance.
"""

from collections import Counter
from datetime import datetime, timedelta
import json
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, and_

from models.workout_session import WorkoutSession
from models.workout_exercise import WorkoutExercise
from models.pose_metric import PoseMetric
from models.exercise import Exercise


# Canonical Component Names & Tie-Breaking Priority Order (Master Guide Specification)
COMPONENT_PRIORITY = [
    ("form_score", "Posture & Form Accuracy"),
    ("completion_quality", "Repetition Completion Quality"),
    ("stability_score", "Joint Stability & Knee Tracking"),
    ("rom_score", "Range of Motion (Squat Depth)"),
    ("smooth_score", "Movement Fluidity (Min Jerk)"),
    ("tempo_score", "Cadence & Movement Tempo"),
    ("symmetry_score", "Bilateral Symmetry"),
]

# Biomechanical Severity Priority for Form Issue Tie-Breaking
VIOLATION_PRIORITY = [
    ("INSUFFICIENT_DEPTH", "Insufficient Squat Depth"),
    ("EXCESSIVE_TORSO_LEAN", "Excessive Torso Forward Lean"),
    ("KNEE_ALIGNMENT_ISSUE", "Knee Valgus (Knee Cave)"),
]

VIOLATION_DISPLAY_MAP = {
    "INSUFFICIENT_DEPTH": "Insufficient Squat Depth",
    "EXCESSIVE_TORSO_LEAN": "Excessive Torso Forward Lean",
    "KNEE_ALIGNMENT_ISSUE": "Knee Valgus (Knee Cave)",
}


class PerformanceService:
    """
    Core service handling longitudinal workout data aggregation,
    trend analysis, strongest improvement area detection, recurring issue analysis,
    and next-week actionable coaching focus generation.
    """

    @staticmethod
    def get_weekly_performance_report(
        db: Session,
        user_id: int,
        days: int = 7,
    ) -> Dict:
        """
        Aggregates and analyzes workout sessions for the authenticated user
        over a specified rolling period (default 7 days).
        
        Guarantees strict current-user scoping and cross-user data isolation.
        """
        now = datetime.utcnow()
        cutoff_date = now - timedelta(days=days) if days > 0 else None

        # Build query strictly scoped to current_user
        query = (
            select(WorkoutSession)
            .options(
                selectinload(WorkoutSession.workout_exercises).selectinload(
                    WorkoutExercise.exercise
                ),
                selectinload(WorkoutSession.pose_metrics),
            )
            .where(
                WorkoutSession.user_id == user_id,
                WorkoutSession.ended_at.is_not(None),
            )
        )

        if cutoff_date is not None:
            query = query.where(WorkoutSession.started_at >= cutoff_date)

        query = query.order_by(WorkoutSession.started_at.asc())
        sessions = db.execute(query).scalars().all()

        start_date_str = (cutoff_date or (sessions[0].started_at if sessions else now)).strftime("%Y-%m-%d")
        end_date_str = now.strftime("%Y-%m-%d")

        reporting_period = {
            "start_date": start_date_str,
            "end_date": end_date_str,
            "days": days,
        }

        # ---------------------------------------------------------------------
        # Empty History Case
        # ---------------------------------------------------------------------
        if not sessions:
            return {
                "reporting_period": reporting_period,
                "total_sessions": 0,
                "total_reps": 0,
                "average_score": None,
                "trend": "insufficient_history",
                "score_delta": None,
                "strongest_improvement": "Insufficient history (complete sessions to evaluate improvement)",
                "recurring_form_issue": "None — Clean Movement Form",
                "next_week_focus": "Complete your first guided workout session to establish a personal performance baseline.",
                "exercise_stats": [],
                "form_warnings": [],
                "session_history": [],
            }

        # ---------------------------------------------------------------------
        # 3.1 Data Aggregation
        # ---------------------------------------------------------------------
        total_sessions = len(sessions)
        total_reps = 0
        scores: List[float] = []
        session_history: List[Dict] = []
        exercise_agg: Dict[int, Dict] = {}
        all_violations: List[str] = []
        session_component_records: List[Dict[str, float]] = []

        for s in sessions:
            if s.performance_score is not None:
                scores.append(s.performance_score)

            # Reps & Exercise info
            reps_in_session = 0
            ex_id = 1
            ex_name = "Squat"
            ex_cat = "Legs"

            if s.workout_exercises:
                we = s.workout_exercises[0]
                reps_in_session = we.reps or 0
                if we.exercise:
                    ex_id = we.exercise.id
                    ex_name = we.exercise.name
                    ex_cat = we.exercise.category

            total_reps += reps_in_session

            if ex_id not in exercise_agg:
                exercise_agg[ex_id] = {
                    "exercise_id": ex_id,
                    "name": ex_name,
                    "category": ex_cat,
                    "sessions": 0,
                    "total_reps": 0,
                    "scores": [],
                }

            exercise_agg[ex_id]["sessions"] += 1
            exercise_agg[ex_id]["total_reps"] += reps_in_session
            if s.performance_score is not None:
                exercise_agg[ex_id]["scores"].append(s.performance_score)

            # Pose metrics & violation extraction
            session_comp_map: Dict[str, List[float]] = {}
            for pm in s.pose_metrics:
                if pm.violations:
                    for v in pm.violations.split(","):
                        v_clean = v.strip()
                        if v_clean:
                            all_violations.append(v_clean)

                if pm.metrics_json:
                    try:
                        m_data = json.loads(pm.metrics_json) if isinstance(pm.metrics_json, str) else pm.metrics_json
                        if isinstance(m_data, dict):
                            for key in (
                                "form_score",
                                "completion_quality",
                                "stability_score",
                                "rom_score",
                                "smooth_score",
                                "tempo_score",
                                "symmetry_score",
                            ):
                                if key in m_data and m_data[key] is not None:
                                    session_comp_map.setdefault(key, []).append(float(m_data[key]))
                    except Exception:
                        pass

            # Average components for this session
            avg_session_comps = {
                k: sum(v_list) / len(v_list) for k, v_list in session_comp_map.items() if v_list
            }
            session_component_records.append(avg_session_comps)

            # Chronological session point
            dur_s = (s.ended_at - s.started_at).total_seconds() if s.ended_at else None
            session_history.append(
                {
                    "session_id": s.id,
                    "date": s.started_at.strftime("%Y-%m-%d %H:%M"),
                    "exercise": ex_name,
                    "score": s.performance_score,
                    "reps": reps_in_session,
                    "duration_seconds": round(dur_s, 1) if dur_s is not None else None,
                    "calories": s.calories,
                }
            )

        avg_score = round(sum(scores) / len(scores), 1) if scores else None

        # Format exercise statistics
        exercise_stats = []
        for ex_item in exercise_agg.values():
            s_list = ex_item["scores"]
            exercise_stats.append(
                {
                    "exercise_id": ex_item["exercise_id"],
                    "name": ex_item["name"],
                    "category": ex_item["category"],
                    "sessions": ex_item["sessions"],
                    "total_reps": ex_item["total_reps"],
                    "average_score": round(sum(s_list) / len(s_list), 1) if s_list else None,
                }
            )

        # ---------------------------------------------------------------------
        # 3.2 Performance Trend Calculation
        # ---------------------------------------------------------------------
        trend = "insufficient_history"
        score_delta: Optional[float] = None

        if len(scores) >= 2:
            if len(scores) >= 4:
                # Compare earlier half against recent half
                mid = len(scores) // 2
                prior_half = scores[:mid]
                recent_half = scores[mid:]
                prior_avg = sum(prior_half) / len(prior_half)
                recent_avg = sum(recent_half) / len(recent_half)
                score_delta = round(recent_avg - prior_avg, 1)
            else:
                # 2 or 3 sessions: compare latest against prior average
                prior_scores = scores[:-1]
                prior_avg = sum(prior_scores) / len(prior_scores)
                latest = scores[-1]
                score_delta = round(latest - prior_avg, 1)

            if score_delta >= 2.5:
                trend = "improving"
            elif score_delta <= -2.5:
                trend = "declining"
            else:
                trend = "stable"

        # ---------------------------------------------------------------------
        # 3.3 Strongest Improvement Area (Deterministic Component Analysis)
        # ---------------------------------------------------------------------
        strongest_improvement = PerformanceService._calculate_strongest_improvement(
            session_component_records
        )

        # ---------------------------------------------------------------------
        # 3.4 Recurring Form Issue Analysis & Tie-Breaking
        # ---------------------------------------------------------------------
        recurring_form_issue, form_warnings = PerformanceService._analyze_recurring_issues(
            all_violations
        )

        # ---------------------------------------------------------------------
        # 3.5 Actionable Next-Week Fitness Coaching Focus
        # ---------------------------------------------------------------------
        next_week_focus = PerformanceService._generate_next_week_focus(
            recurring_form_issue, session_component_records
        )

        return {
            "reporting_period": reporting_period,
            "total_sessions": total_sessions,
            "total_reps": total_reps,
            "average_score": avg_score,
            "trend": trend,
            "score_delta": score_delta,
            "strongest_improvement": strongest_improvement,
            "recurring_form_issue": recurring_form_issue,
            "next_week_focus": next_week_focus,
            "exercise_stats": exercise_stats,
            "form_warnings": form_warnings,
            "session_history": session_history,
        }

    @staticmethod
    def _calculate_strongest_improvement(
        session_components: List[Dict[str, float]],
    ) -> str:
        """
        Determines the component with the largest positive delta from earlier to recent sessions.
        Ties are broken deterministically using COMPONENT_PRIORITY.
        """
        if len(session_components) < 2:
            return "Baseline session established"

        mid = len(session_components) // 2
        prior_records = session_components[:mid]
        recent_records = session_components[mid:]

        # Compute average score per component for prior vs recent
        prior_averages: Dict[str, float] = {}
        recent_averages: Dict[str, float] = {}

        for key, _ in COMPONENT_PRIORITY:
            p_vals = [r[key] for r in prior_records if key in r]
            r_vals = [r[key] for r in recent_records if key in r]

            if p_vals and r_vals:
                prior_averages[key] = sum(p_vals) / len(p_vals)
                recent_averages[key] = sum(r_vals) / len(r_vals)

        # Calculate positive improvements
        deltas: Dict[str, float] = {}
        for key in prior_averages:
            diff = recent_averages[key] - prior_averages[key]
            if diff > 0.0:
                deltas[key] = round(diff, 1)

        if not deltas:
            return "Consistent Baseline Performance Across All Components"

        max_delta = max(deltas.values())
        candidates = [k for k, v in deltas.items() if v == max_delta]

        # Break tie using COMPONENT_PRIORITY order
        best_component_key = candidates[0]
        if len(candidates) > 1:
            for priority_key, _ in COMPONENT_PRIORITY:
                if priority_key in candidates:
                    best_component_key = priority_key
                    break

        disp_name = dict(COMPONENT_PRIORITY).get(best_component_key, best_component_key)
        return f"{disp_name} (+{max_delta} pts)"

    @staticmethod
    def _analyze_recurring_issues(
        all_violations: List[str],
    ) -> Tuple[str, List[Dict]]:
        """
        Aggregates stored violations, counts frequencies, calculates percentages,
        and determines the recurring issue with deterministic tie-breaking.
        """
        if not all_violations:
            return "None — Clean Movement Form", []

        counts = Counter(all_violations)
        total_v = len(all_violations)

        form_warnings = []
        for code, count in counts.most_common():
            disp = VIOLATION_DISPLAY_MAP.get(code, code.replace("_", " ").title())
            form_warnings.append(
                {
                    "violation_code": code,
                    "display_name": disp,
                    "count": count,
                    "percentage": round((count / total_v) * 100, 1),
                }
            )

        # Find highest count
        max_count = max(counts.values())
        tied_codes = [c for c, cnt in counts.items() if cnt == max_count]

        # Tie breaking by VIOLATION_PRIORITY, then alphabetical
        selected_code = tied_codes[0]
        if len(tied_codes) > 1:
            priority_dict = {code: idx for idx, (code, _) in enumerate(VIOLATION_PRIORITY)}
            tied_codes.sort(key=lambda c: (priority_dict.get(c, 999), c))
            selected_code = tied_codes[0]

        top_issue_display = VIOLATION_DISPLAY_MAP.get(
            selected_code, selected_code.replace("_", " ").title()
        )
        return top_issue_display, form_warnings

    @staticmethod
    def _generate_next_week_focus(
        recurring_issue: str,
        session_components: List[Dict[str, float]],
    ) -> str:
        """
        Generates transparent, actionable coaching advice.
        Strictly non-diagnostic fitness coaching guidance.
        """
        issue_lower = recurring_issue.lower()

        if "depth" in issue_lower or "insufficient" in issue_lower:
            return "Focus on reaching full parallel depth (femur horizontal to floor) on every repetition before starting ascent."
        elif "torso" in issue_lower or "lean" in issue_lower:
            return "Focus on bracing your abdominal core and keeping your chest proud and upright throughout the descent."
        elif "knee" in issue_lower or "valgus" in issue_lower:
            return "Focus on actively driving your knees outward over your mid-toes to eliminate inward knee cave."

        # If clean posture, identify lowest recent component score
        if session_components:
            recent_comps = session_components[-1]
            if recent_comps:
                min_comp = min(recent_comps.items(), key=lambda x: x[1])
                comp_key, val = min_comp
                if val < 85.0:
                    if "tempo" in comp_key:
                        return "Focus on pacing: maintain a controlled 2-second eccentric descent and avoid rushing repetitions."
                    elif "stability" in comp_key:
                        return "Focus on foundation: maintain firm foot tripod contact with the floor to enhance balance."
                    elif "smooth" in comp_key:
                        return "Focus on motion fluidity: transition smoothly between descent and ascent without abrupt stops."

        return "Great consistency! Maintain progression by adding 1-2 repetitions per set while preserving clean technique."
