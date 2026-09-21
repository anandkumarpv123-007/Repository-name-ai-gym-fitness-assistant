from collections import Counter
from datetime import datetime
import json
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func

from models.exercise import Exercise
from models.user import User
from models.workout_session import WorkoutSession
from models.workout_exercise import WorkoutExercise
from models.pose_metric import PoseMetric
from routers.auth import get_current_user, get_db
from schemas.workout import (
    ExerciseResponse,
    WorkoutStartRequest,
    WorkoutStartResponse,
    WorkoutCompleteRequest,
    WorkoutCompleteResponse,
    WorkoutHistoryItem,
    WorkoutDetailResponse,
    PoseMetricDetail,
    PerformanceSummaryResponse,
)

router = APIRouter(tags=["Workouts & Performance"])


# =====================================================================
# 1. Exercise Catalogue
# =====================================================================

@router.get("/exercises", response_model=List[ExerciseResponse])
def get_exercise_catalogue(db: Session = Depends(get_db)):
    """Retrieve all available exercises from the catalogue."""
    exercises = db.execute(select(Exercise).order_by(Exercise.id)).scalars().all()
    return exercises


# =====================================================================
# 2. Workout Session Lifecycle
# =====================================================================

@router.post("/workouts/start", response_model=WorkoutStartResponse)
def start_workout_session(
    payload: WorkoutStartRequest = WorkoutStartRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Start a new workout session for the authenticated user."""
    session = WorkoutSession(
        user_id=current_user.id,
        started_at=datetime.utcnow(),
        notes=payload.notes,
    )
    db.add(session)
    db.flush()

    # Pre-stage workout exercise record if exercise_id is provided
    if payload.exercise_id:
        exercise = db.get(Exercise, payload.exercise_id)
        if exercise:
            we = WorkoutExercise(
                workout_session_id=session.id,
                exercise_id=exercise.id,
                sets=1,
                reps=0,
            )
            db.add(we)

    db.commit()
    db.refresh(session)

    return WorkoutStartResponse(
        session_id=session.id,
        started_at=session.started_at,
        message="Workout session started successfully",
    )


@router.post("/workouts/{session_id}/complete", response_model=WorkoutCompleteResponse)
def complete_workout_session(
    session_id: int,
    payload: WorkoutCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Finalize a workout session:
    Calculates duration, saves performance score, records exercise reps,
    and persists individual repetition pose metrics.
    """
    session = db.get(WorkoutSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Workout session not found")

    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this workout session",
        )

    # Validate exercise exists
    exercise = db.get(Exercise, payload.exercise_id)
    if not exercise:
        raise HTTPException(status_code=400, detail="Invalid exercise ID")

    now = datetime.utcnow()
    session.ended_at = now
    session.performance_score = payload.performance_score
    session.calories = payload.calories
    if payload.notes:
        session.notes = payload.notes

    # Update or create WorkoutExercise row
    stmt = select(WorkoutExercise).where(
        WorkoutExercise.workout_session_id == session.id,
        WorkoutExercise.exercise_id == exercise.id,
    )
    we = db.execute(stmt).scalars().first()
    if we:
        we.sets = max(payload.sets, 1)
        we.reps = max(payload.reps, 0)
    else:
        we = WorkoutExercise(
            workout_session_id=session.id,
            exercise_id=exercise.id,
            sets=max(payload.sets, 1),
            reps=max(payload.reps, 0),
        )
        db.add(we)

    # Persist PoseMetric rows for each recorded rep
    if payload.rep_metrics:
        for rm in payload.rep_metrics:
            viols_str = ",".join(rm.violations) if rm.violations else None
            metrics_str = json.dumps(rm.metrics_json) if rm.metrics_json else None

            pm = PoseMetric(
                workout_session_id=session.id,
                rep_number=rm.rep_number,
                min_knee_angle=rm.min_knee_angle,
                max_torso_lean=rm.max_torso_lean,
                duration_seconds=rm.duration_seconds,
                form_status=rm.form_status,
                violations=viols_str,
                metrics_json=metrics_str,
                created_at=now,
            )
            db.add(pm)

    db.commit()
    db.refresh(session)

    duration_s = (session.ended_at - session.started_at).total_seconds()

    return WorkoutCompleteResponse(
        session_id=session.id,
        reps=payload.reps,
        performance_score=session.performance_score,
        duration_seconds=duration_s,
        message="Workout session completed and metrics saved successfully",
    )


# =====================================================================
# 3. Workout History & Session Details
# =====================================================================

@router.get("/workouts/history", response_model=List[WorkoutHistoryItem])
def get_workout_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve historical workout sessions for the current authenticated user."""
    stmt = (
        select(WorkoutSession)
        .options(
            selectinload(WorkoutSession.workout_exercises).selectinload(
                WorkoutExercise.exercise
            )
        )
        .where(WorkoutSession.user_id == current_user.id)
        .order_by(WorkoutSession.started_at.desc())
    )
    sessions = db.execute(stmt).scalars().all()

    results = []
    for s in sessions:
        ex_name = "Workout"
        sets_count = 0
        reps_count = 0
        if s.workout_exercises:
            we = s.workout_exercises[0]
            if we.exercise:
                ex_name = we.exercise.name
            sets_count = we.sets or 0
            reps_count = we.reps or 0

        dur = (s.ended_at - s.started_at).total_seconds() if s.ended_at else None

        results.append(
            WorkoutHistoryItem(
                session_id=s.id,
                started_at=s.started_at,
                ended_at=s.ended_at,
                duration_seconds=dur,
                exercise_name=ex_name,
                sets=sets_count,
                reps=reps_count,
                performance_score=s.performance_score,
                calories=s.calories,
            )
        )

    return results


@router.get("/workouts/{session_id}", response_model=WorkoutDetailResponse)
def get_workout_detail(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve detailed breakdown of a specific workout session."""
    stmt = (
        select(WorkoutSession)
        .options(
            selectinload(WorkoutSession.workout_exercises).selectinload(
                WorkoutExercise.exercise
            ),
            selectinload(WorkoutSession.pose_metrics),
        )
        .where(WorkoutSession.id == session_id)
    )
    session = db.execute(stmt).scalars().first()

    if not session:
        raise HTTPException(status_code=404, detail="Workout session not found")

    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this workout session",
        )

    ex_name = "Workout"
    sets_count = 0
    reps_count = 0
    if session.workout_exercises:
        we = session.workout_exercises[0]
        if we.exercise:
            ex_name = we.exercise.name
        sets_count = we.sets or 0
        reps_count = we.reps or 0

    dur = (
        (session.ended_at - session.started_at).total_seconds()
        if session.ended_at
        else None
    )

    pose_list = [
        PoseMetricDetail(
            rep_number=pm.rep_number,
            min_knee_angle=pm.min_knee_angle,
            max_torso_lean=pm.max_torso_lean,
            duration_seconds=pm.duration_seconds,
            form_status=pm.form_status,
            violations=pm.violations,
        )
        for pm in sorted(session.pose_metrics, key=lambda x: x.rep_number)
    ]

    return WorkoutDetailResponse(
        session_id=session.id,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_seconds=dur,
        exercise_name=ex_name,
        sets=sets_count,
        reps=reps_count,
        performance_score=session.performance_score,
        calories=session.calories,
        notes=session.notes,
        pose_metrics=pose_list,
    )


# =====================================================================
# 4. Longitudinal Performance Summary & Comparisons
# =====================================================================

@router.get("/performance/summary", response_model=PerformanceSummaryResponse)
def get_performance_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generates longitudinal performance progress reports:
    Compares current metrics against user's historical performance,
    computes score trends, detects recurring form issues, and suggests focus areas.
    """
    stmt = (
        select(WorkoutSession)
        .options(
            selectinload(WorkoutSession.workout_exercises).selectinload(
                WorkoutExercise.exercise
            ),
            selectinload(WorkoutSession.pose_metrics),
        )
        .where(
            WorkoutSession.user_id == current_user.id,
            WorkoutSession.ended_at.is_not(None),
        )
        .order_by(WorkoutSession.started_at.asc())
    )
    sessions = db.execute(stmt).scalars().all()

    total_sessions = len(sessions)
    if total_sessions == 0:
        return PerformanceSummaryResponse(
            total_sessions=0,
            total_reps=0,
            average_score=None,
            score_trend="NEW",
            score_delta=None,
            strongest_area="Ready for baseline evaluation",
            recurring_issue="None",
            next_week_focus="Complete your first guided squat session to establish a performance baseline.",
            recent_sessions=[],
        )

    # Aggregate reps and scores
    total_reps = 0
    scores = []
    recent_list = []
    all_violations = []

    for s in sessions:
        if s.performance_score is not None:
            scores.append(s.performance_score)

        reps_in_session = 0
        ex_name = "Squat"
        if s.workout_exercises:
            we = s.workout_exercises[0]
            reps_in_session = we.reps or 0
            if we.exercise:
                ex_name = we.exercise.name
        total_reps += reps_in_session

        # Collect violations
        for pm in s.pose_metrics:
            if pm.violations:
                for v in pm.violations.split(","):
                    if v.strip():
                        all_violations.append(v.strip())

        recent_list.append(
            {
                "session_id": s.id,
                "date": s.started_at.strftime("%Y-%m-%d %H:%M"),
                "exercise": ex_name,
                "score": s.performance_score,
                "reps": reps_in_session,
            }
        )
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    # Trend calculation: compare latest score with prior average
    trend = "STABLE"
    score_delta = None
    if len(scores) >= 2:
        latest = scores[-1]
        prior_scores = scores[:-1]
        prior_avg = sum(prior_scores) / len(prior_scores)
        score_delta = round(latest - prior_avg, 1)
        if score_delta >= 3.0:
            trend = "IMPROVING"
        elif score_delta <= -3.0:
            trend = "DECLINING"
        else:
            trend = "STABLE"
    elif len(scores) == 1:
        trend = "NEW"
        score_delta = 0.0

    # Recurring issue analysis
    if all_violations:
        issue_counts = Counter(all_violations)
        top_issue, count = issue_counts.most_common(1)[0]
        recurring_issue = top_issue.replace("_", " ").title()

        if "DEPTH" in top_issue:
            next_focus = "Focus on reaching parallel depth (<= 90-100°) on every repetition."
            strongest_area = "Torso Stability"
        elif "TORSO" in top_issue:
            next_focus = "Focus on bracing your core and keeping your chest upright during descent."
            strongest_area = "Squat Depth"
        elif "KNEE" in top_issue:
            next_focus = "Focus on driving knees outward in line with your feet to avoid knee cave."
            strongest_area = "Torso Control"
        else:
            next_focus = "Maintain controlled tempo and full range of motion."
            strongest_area = "Form Consistency"
    else:
        recurring_issue = "None — Clean Form"
        next_focus = "Great technique! Gradually increase repetitions while maintaining form quality."
        strongest_area = "Overall Execution"

    return PerformanceSummaryResponse(
        total_sessions=total_sessions,
        total_reps=total_reps,
        average_score=round(avg_score, 1) if avg_score is not None else None,
        score_trend=trend,
        score_delta=score_delta,
        strongest_area=strongest_area,
        recurring_issue=recurring_issue,
        next_week_focus=next_focus,
        recent_sessions=recent_list[-10:],
    )
