"""
AI Gym & Fitness Assistant — Squat Form Analyzer & Real-Time Feedback
Phase 2.4 — Squat Form Analysis + Real-Time Feedback

Provides explainable, rule-based biomechanical form analysis for squats:
1. Squat Depth: Compares knee flexion against configurable depth threshold.
2. Torso Angle: Checks forward lean relative to vertical axis (shoulder -> hip).
3. Knee Alignment: Checks knee displacement relative to hip-ankle alignment corridor.
4. Landmark Quality: Gates all evaluations on visibility confidence to prevent fabricated feedback.
5. Rep-Level Summaries: Aggregates biomechanical metrics across the repetition cycle.

Strictly non-diagnostic: Provides athletic movement cues, not medical advice.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import numpy as np

from .angle_calculator import calculate_landmark_angle, calculate_angle_2d
from .pose_detector import PoseDetectionResult, PoseLandmarkPoint
from .squat_state_machine import SquatMovementResult, SquatState


# Standard Machine-Readable Violation Codes
VIOLATION_INSUFFICIENT_DEPTH = "INSUFFICIENT_DEPTH"
VIOLATION_EXCESSIVE_TORSO_LEAN = "EXCESSIVE_TORSO_LEAN"
VIOLATION_KNEE_ALIGNMENT = "KNEE_ALIGNMENT_ISSUE"

# Standard Actionable Feedback Strings
FEEDBACK_INSUFFICIENT_DEPTH = "Go slightly deeper."
FEEDBACK_EXCESSIVE_TORSO_LEAN = "Keep your chest more upright."
FEEDBACK_KNEE_ALIGNMENT = "Keep your knees aligned with your feet."
FEEDBACK_GOOD_FORM = "Good posture maintained."
FEEDBACK_INSUFFICIENT_DATA = "Landmarks occluded or out of frame."


@dataclass
class RepFormSummary:
    """
    Biomechanical summary of a single completed squat repetition.
    
    Attributes:
        rep_number: Sequential index of the completed repetition.
        depth_status: "ADEQUATE" or "INSUFFICIENT".
        knee_alignment_status: "ALIGNED" or "MISALIGNED".
        torso_status: "UPRIGHT", "ACCEPTABLE", or "EXCESSIVE_LEAN".
        min_knee_angle: Deepest knee flexion reached during the repetition (deg).
        max_torso_lean: Maximum forward torso lean recorded during the repetition (deg).
        violations: List of all violation codes triggered during this repetition.
        feedback: Distinct list of actionable coaching cues.
        passed: True if rep completed with zero violations.
    """
    rep_number: int
    depth_status: str
    knee_alignment_status: str
    torso_status: str
    min_knee_angle: float
    max_torso_lean: float
    violations: List[str] = field(default_factory=list)
    feedback: List[str] = field(default_factory=list)
    passed: bool = True

    def to_dict(self) -> dict:
        return {
            "rep_number": self.rep_number,
            "depth_status": self.depth_status,
            "knee_alignment_status": self.knee_alignment_status,
            "torso_status": self.torso_status,
            "min_knee_angle": round(self.min_knee_angle, 1),
            "max_torso_lean": round(self.max_torso_lean, 1),
            "violations": self.violations,
            "feedback": self.feedback,
            "passed": self.passed,
        }


@dataclass
class FormAnalysisResult:
    """
    Structured outcome of a per-frame form analysis evaluation.
    
    Attributes:
        valid: True if required landmarks are reliably visible; False otherwise.
        depth_status: "ADEQUATE", "INSUFFICIENT", "NOT_AT_DEPTH", or "PENDING".
        knee_alignment_status: "ALIGNED", "MISALIGNED", or "UNKNOWN".
        torso_status: "UPRIGHT", "ACCEPTABLE", "EXCESSIVE_LEAN", or "UNKNOWN".
        violations: List of triggered violation codes on this frame.
        feedback: List of actionable coaching cues on this frame.
        knee_angle: Current evaluated knee angle in degrees.
        torso_angle: Current evaluated torso lean angle relative to vertical (degrees).
        rep_summary: Available only on the exact frame when a repetition finishes.
    """
    valid: bool
    depth_status: str
    knee_alignment_status: str
    torso_status: str
    violations: List[str] = field(default_factory=list)
    feedback: List[str] = field(default_factory=list)
    knee_angle: Optional[float] = None
    torso_angle: Optional[float] = None
    rep_summary: Optional[RepFormSummary] = None

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "depth_status": self.depth_status,
            "knee_alignment_status": self.knee_alignment_status,
            "torso_status": self.torso_status,
            "violations": self.violations,
            "feedback": self.feedback,
            "knee_angle": round(self.knee_angle, 1) if self.knee_angle is not None else None,
            "torso_angle": round(self.torso_angle, 1) if self.torso_angle is not None else None,
            "rep_summary": self.rep_summary.to_dict() if self.rep_summary else None,
        }


class SquatFormAnalyzer:
    """
    Rule-based form analyzer evaluating squat depth, torso angle, and knee alignment.
    """

    def __init__(
        self,
        depth_threshold: float = 100.0,
        max_torso_lean: float = 45.0,
        knee_deviation_threshold: float = 0.35,
        min_visibility: float = 0.5,
        side: str = "LEFT",
    ) -> None:
        """
        Initializes the SquatFormAnalyzer.
        
        Args:
            depth_threshold: Knee angle considered adequate depth (deg, default: 100.0).
            max_torso_lean: Max forward lean angle from vertical (deg, default: 45.0).
            knee_deviation_threshold: Normalized lateral knee displacement ratio (default: 0.35).
            min_visibility: Minimum confidence required for all evaluated landmarks (default: 0.5).
            side: Anatomical side to track ('LEFT', 'RIGHT', or 'AUTO').
        """
        self.depth_threshold = depth_threshold
        self.max_torso_lean = max_torso_lean
        self.knee_deviation_threshold = knee_deviation_threshold
        self.min_visibility = min_visibility
        self.side = side.upper()

        # Repetition tracking history & accumulators
        self.rep_summaries: List[RepFormSummary] = []
        self._rep_min_knee_angle: float = 180.0
        self._rep_max_torso_lean: float = 0.0
        self._rep_worst_knee_deviation: float = 0.0
        self._rep_violations: set = set()
        self._in_rep_cycle: bool = False

    def reset(self) -> None:
        """Resets the analyzer state and rep history."""
        self.rep_summaries.clear()
        self._reset_current_rep_accumulators()

    def _reset_current_rep_accumulators(self) -> None:
        self._rep_min_knee_angle = 180.0
        self._rep_max_torso_lean = 0.0
        self._rep_worst_knee_deviation = 0.0
        self._rep_violations.clear()
        self._in_rep_cycle = False

    def calculate_torso_lean(
        self,
        shoulder: Optional[PoseLandmarkPoint],
        hip: Optional[PoseLandmarkPoint],
    ) -> Optional[float]:
        """
        Calculates torso angle relative to the upward vertical axis.
        
        Vector from HIP to SHOULDER: v = (x_shoulder - x_hip, y_shoulder - y_hip)
        In image space, y increases downwards, so vertical upward is (0, -1).
        
        Angle = arctan2(|dx|, dy_upward) in degrees.
        0 deg = perfectly vertical standing upright.
        90 deg = horizontal torso (bent over 90 deg).
        """
        if shoulder is None or hip is None:
            return None

        if (
            shoulder.visibility < self.min_visibility
            or shoulder.presence < self.min_visibility
            or hip.visibility < self.min_visibility
            or hip.presence < self.min_visibility
        ):
            return None

        dx = abs(shoulder.pixel_x - hip.pixel_x)
        dy = hip.pixel_y - shoulder.pixel_y  # positive when shoulder is above hip

        if dy <= 0:
            # Shoulder dropped below or at hip level (extreme inversion)
            return 90.0

        angle_rad = np.arctan2(dx, dy)
        return float(np.degrees(angle_rad))

    def calculate_knee_alignment_deviation(
        self,
        hip: Optional[PoseLandmarkPoint],
        knee: Optional[PoseLandmarkPoint],
        ankle: Optional[PoseLandmarkPoint],
    ) -> Optional[float]:
        """
        Calculates normalized lateral knee displacement relative to hip-ankle corridor.
        
        Formula:
            deviation = |x_knee - x_ankle| / max(|y_ankle - y_knee|, 1.0)
        """
        if hip is None or knee is None or ankle is None:
            return None

        for pt in (hip, knee, ankle):
            if pt.visibility < self.min_visibility or pt.presence < self.min_visibility:
                return None

        dy = abs(ankle.pixel_y - knee.pixel_y)
        if dy < 1:
            return 0.0

        dx = abs(knee.pixel_x - ankle.pixel_x)
        return float(dx / dy)

    def analyze_frame(
        self,
        pose_result: PoseDetectionResult,
        movement_result: Optional[SquatMovementResult] = None,
    ) -> FormAnalysisResult:
        """
        Evaluates current posture and generates per-frame form telemetry.
        """
        if not pose_result.detected or not pose_result.landmarks:
            return FormAnalysisResult(
                valid=False,
                depth_status="UNKNOWN",
                knee_alignment_status="UNKNOWN",
                torso_status="UNKNOWN",
                violations=[],
                feedback=[FEEDBACK_INSUFFICIENT_DATA],
            )

        # Resolve anatomical tracking side
        selected_side = self.side
        if selected_side == "AUTO":
            left_vis = sum(
                pose_result.get(k).visibility if pose_result.get(k) else 0.0
                for k in ("LEFT_SHOULDER", "LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE")
            )
            right_vis = sum(
                pose_result.get(k).visibility if pose_result.get(k) else 0.0
                for k in ("RIGHT_SHOULDER", "RIGHT_HIP", "RIGHT_KNEE", "RIGHT_ANKLE")
            )
            selected_side = "LEFT" if left_vis >= right_vis else "RIGHT"

        shoulder = pose_result.get(f"{selected_side}_SHOULDER")
        hip = pose_result.get(f"{selected_side}_HIP")
        knee = pose_result.get(f"{selected_side}_KNEE")
        ankle = pose_result.get(f"{selected_side}_ANKLE")

        # 1. Landmark Reliability Gate
        required_landmarks = [shoulder, hip, knee, ankle]
        if any(pt is None for pt in required_landmarks):
            return FormAnalysisResult(
                valid=False,
                depth_status="UNKNOWN",
                knee_alignment_status="UNKNOWN",
                torso_status="UNKNOWN",
                violations=[],
                feedback=[FEEDBACK_INSUFFICIENT_DATA],
            )

        for pt in required_landmarks:
            if pt.visibility < self.min_visibility or pt.presence < self.min_visibility:
                return FormAnalysisResult(
                    valid=False,
                    depth_status="UNKNOWN",
                    knee_alignment_status="UNKNOWN",
                    torso_status="UNKNOWN",
                    violations=[],
                    feedback=[FEEDBACK_INSUFFICIENT_DATA],
                )

        violations: List[str] = []
        feedback_list: List[str] = []

        # 2. Knee Angle Evaluation (reuse smoothed angle from movement_result if provided)
        if movement_result is not None and movement_result.smoothed_angle is not None:
            knee_angle = movement_result.smoothed_angle
        elif movement_result is not None and movement_result.current_angle is not None:
            knee_angle = movement_result.current_angle
        else:
            knee_angle = calculate_landmark_angle(hip, knee, ankle, min_visibility=self.min_visibility)

        # 3. Torso Angle Evaluation
        torso_angle = self.calculate_torso_lean(shoulder, hip)
        torso_status = "UPRIGHT"
        if torso_angle is not None:
            if torso_angle > self.max_torso_lean:
                torso_status = "EXCESSIVE_LEAN"
                violations.append(VIOLATION_EXCESSIVE_TORSO_LEAN)
                feedback_list.append(FEEDBACK_EXCESSIVE_TORSO_LEAN)
            elif torso_angle > 20.0:
                torso_status = "ACCEPTABLE"
            else:
                torso_status = "UPRIGHT"

        # 4. Knee Alignment Evaluation
        knee_dev = self.calculate_knee_alignment_deviation(hip, knee, ankle)
        knee_status = "ALIGNED"
        if knee_dev is not None:
            if knee_dev > self.knee_deviation_threshold:
                knee_status = "MISALIGNED"
                violations.append(VIOLATION_KNEE_ALIGNMENT)
                feedback_list.append(FEEDBACK_KNEE_ALIGNMENT)
            else:
                knee_status = "ALIGNED"

        # 5. Depth Status Evaluation
        depth_status = "NOT_AT_DEPTH"
        current_state = movement_result.state if movement_result else SquatState.UP

        if current_state in (SquatState.DESCENDING, SquatState.BOTTOM):
            self._in_rep_cycle = True
            if knee_angle is not None:
                self._rep_min_knee_angle = min(self._rep_min_knee_angle, knee_angle)
            if torso_angle is not None:
                self._rep_max_torso_lean = max(self._rep_max_torso_lean, torso_angle)
            if knee_dev is not None:
                self._rep_worst_knee_deviation = max(self._rep_worst_knee_deviation, knee_dev)

            # Record violations occurring during the descent/bottom
            for v in violations:
                self._rep_violations.add(v)

            if knee_angle is not None and knee_angle <= self.depth_threshold:
                depth_status = "ADEQUATE"
            else:
                depth_status = "INSUFFICIENT"
                if current_state == SquatState.BOTTOM and knee_angle is not None and knee_angle > self.depth_threshold:
                    violations.append(VIOLATION_INSUFFICIENT_DEPTH)
                    feedback_list.append(FEEDBACK_INSUFFICIENT_DEPTH)
        elif current_state == SquatState.UP:
            depth_status = "NOT_AT_DEPTH"

        # If no violations occurred and posture is valid
        if not violations and feedback_list == []:
            feedback_list.append(FEEDBACK_GOOD_FORM)

        # 6. Rep-Level Summary Generation on Rep Completion
        rep_summary: Optional[RepFormSummary] = None
        if movement_result and movement_result.rep_completed:
            rep_num = movement_result.reps

            # Check if bottom depth was reached during this rep
            rep_depth_ok = self._rep_min_knee_angle <= self.depth_threshold
            rep_depth_status = "ADEQUATE" if rep_depth_ok else "INSUFFICIENT"
            if not rep_depth_ok:
                self._rep_violations.add(VIOLATION_INSUFFICIENT_DEPTH)

            rep_torso_ok = self._rep_max_torso_lean <= self.max_torso_lean
            rep_torso_status = "ACCEPTABLE" if rep_torso_ok else "EXCESSIVE_LEAN"
            if not rep_torso_ok:
                self._rep_violations.add(VIOLATION_EXCESSIVE_TORSO_LEAN)

            rep_knee_ok = self._rep_worst_knee_deviation <= self.knee_deviation_threshold
            rep_knee_status = "ALIGNED" if rep_knee_ok else "MISALIGNED"
            if not rep_knee_ok:
                self._rep_violations.add(VIOLATION_KNEE_ALIGNMENT)

            # Generate final feedback for this rep
            rep_feedback: List[str] = []
            if VIOLATION_INSUFFICIENT_DEPTH in self._rep_violations:
                rep_feedback.append(FEEDBACK_INSUFFICIENT_DEPTH)
            if VIOLATION_EXCESSIVE_TORSO_LEAN in self._rep_violations:
                rep_feedback.append(FEEDBACK_EXCESSIVE_TORSO_LEAN)
            if VIOLATION_KNEE_ALIGNMENT in self._rep_violations:
                rep_feedback.append(FEEDBACK_KNEE_ALIGNMENT)

            if not rep_feedback:
                rep_feedback.append("Rep completed with good form!")

            rep_summary = RepFormSummary(
                rep_number=rep_num,
                depth_status=rep_depth_status,
                knee_alignment_status=rep_knee_status,
                torso_status=rep_torso_status,
                min_knee_angle=self._rep_min_knee_angle,
                max_torso_lean=self._rep_max_torso_lean,
                violations=sorted(list(self._rep_violations)),
                feedback=rep_feedback,
                passed=len(self._rep_violations) == 0,
            )
            self.rep_summaries.append(rep_summary)
            self._reset_current_rep_accumulators()

        return FormAnalysisResult(
            valid=True,
            depth_status=depth_status,
            knee_alignment_status=knee_status,
            torso_status=torso_status,
            violations=violations,
            feedback=feedback_list,
            knee_angle=knee_angle,
            torso_angle=torso_angle,
            rep_summary=rep_summary,
        )
