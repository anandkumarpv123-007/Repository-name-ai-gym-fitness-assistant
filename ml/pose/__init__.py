"""
AI Gym & Fitness Assistant — Pose Package
Phase 2 — AI Gym Trainer & Pose-to-Performance System
"""

from .angle_calculator import (
    calculate_angle_2d,
    calculate_landmark_angle,
)
from .form_analyzer import (
    FormAnalysisResult,
    RepFormSummary,
    SquatFormAnalyzer,
    VIOLATION_INSUFFICIENT_DEPTH,
    VIOLATION_EXCESSIVE_TORSO_LEAN,
    VIOLATION_KNEE_ALIGNMENT,
    FEEDBACK_INSUFFICIENT_DEPTH,
    FEEDBACK_EXCESSIVE_TORSO_LEAN,
    FEEDBACK_KNEE_ALIGNMENT,
    FEEDBACK_GOOD_FORM,
    FEEDBACK_INSUFFICIENT_DATA,
)
from .performance_analyzer import (
    PerformanceAnalyzer,
    PerformanceScoreBreakdown,
)
from .pose_detector import (
    PoseDetector,
    PoseDetectionResult,
    PoseLandmarkPoint,
)
from .smoothing import (
    MovingAverageFilter,
    ExponentialMovingAverageFilter,
)
from .squat_state_machine import (
    SquatState,
    SquatStateMachine,
    SquatMovementResult,
)
from .visualizer import (
    draw_pose_landmarks,
    draw_movement_telemetry,
    save_annotated_frame,
)

__all__ = [
    "calculate_angle_2d",
    "calculate_landmark_angle",
    "PoseDetector",
    "PoseDetectionResult",
    "PoseLandmarkPoint",
    "MovingAverageFilter",
    "ExponentialMovingAverageFilter",
    "SquatState",
    "SquatStateMachine",
    "SquatMovementResult",
    "FormAnalysisResult",
    "RepFormSummary",
    "SquatFormAnalyzer",
    "PerformanceAnalyzer",
    "PerformanceScoreBreakdown",
    "VIOLATION_INSUFFICIENT_DEPTH",
    "VIOLATION_EXCESSIVE_TORSO_LEAN",
    "VIOLATION_KNEE_ALIGNMENT",
    "FEEDBACK_INSUFFICIENT_DEPTH",
    "FEEDBACK_EXCESSIVE_TORSO_LEAN",
    "FEEDBACK_KNEE_ALIGNMENT",
    "FEEDBACK_GOOD_FORM",
    "FEEDBACK_INSUFFICIENT_DATA",
    "draw_pose_landmarks",
    "draw_movement_telemetry",
    "save_annotated_frame",
]
