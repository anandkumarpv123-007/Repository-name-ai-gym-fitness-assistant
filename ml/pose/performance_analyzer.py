"""
AI Gym & Fitness Assistant — Pose-to-Performance Analyzer
Phase 2.5 — Biomechanical Performance Scoring & Metrics Engine

Calculates a deterministic, reproducible, and explainable Performance Score [0.0, 100.0]
derived from seven source-of-truth biomechanical movement components:
1. Range of Motion (ROM) Consistency (15%)
2. Movement Tempo & Pacing (10%)
3. Joint Stability (15%)
4. Form Accuracy & Rule Adherence (25%)
5. Motion Smoothness (10%)
6. Bilateral Symmetry (5%)
7. Repetition Completion Quality (20%)

Strictly rule-based and deterministic: No LLM, no black-box ML model.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np

from .form_analyzer import (
    RepFormSummary,
    VIOLATION_INSUFFICIENT_DEPTH,
    VIOLATION_EXCESSIVE_TORSO_LEAN,
    VIOLATION_KNEE_ALIGNMENT,
)


@dataclass
class PerformanceScoreBreakdown:
    """
    Component-level breakdown of the final Performance Score.
    All component scores are normalized to [0.0, 100.0].
    """
    overall_score: float
    rating: str  # "EXCELLENT", "GOOD", "FAIR", "NEEDS_IMPROVEMENT"
    rom_consistency: float
    tempo_consistency: float
    stability: float
    form_accuracy: float
    smoothness: float
    symmetry: float
    completion_quality: float
    total_reps: int
    full_reps: int
    shallow_reps: int
    average_depth: float
    average_duration: float
    feedback_summary: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 1),
            "rating": self.rating,
            "components": {
                "rom_consistency": round(self.rom_consistency, 1),
                "tempo_consistency": round(self.tempo_consistency, 1),
                "stability": round(self.stability, 1),
                "form_accuracy": round(self.form_accuracy, 1),
                "smoothness": round(self.smoothness, 1),
                "symmetry": round(self.symmetry, 1),
                "completion_quality": round(self.completion_quality, 1),
            },
            "metrics": {
                "total_reps": self.total_reps,
                "full_reps": self.full_reps,
                "shallow_reps": self.shallow_reps,
                "average_depth": round(self.average_depth, 1),
                "average_duration": round(self.average_duration, 2),
            },
            "feedback_summary": self.feedback_summary,
        }


class PerformanceAnalyzer:
    """
    Evaluates kinematic trajectory records and repetition summaries to generate
    a normalized, reproducible performance assessment.
    """

    # Component weights (sum to 1.0)
    WEIGHTS: Dict[str, float] = {
        "form_accuracy": 0.25,
        "completion_quality": 0.20,
        "stability": 0.15,
        "rom_consistency": 0.15,
        "tempo_consistency": 0.10,
        "smoothness": 0.10,
        "symmetry": 0.05,
    }

    def __init__(
        self,
        ideal_depth: float = 90.0,
        ideal_rep_duration: float = 3.0,
        weights: Optional[Dict[str, float]] = None,
    ) -> None:
        """
        Initializes the Performance Analyzer.
        
        Args:
            ideal_depth: Biomechanical reference depth angle in degrees (default: 90.0).
            ideal_rep_duration: Reference repetition duration in seconds (default: 3.0).
            weights: Optional custom weight mapping for the seven components.
        """
        self.ideal_depth = ideal_depth
        self.ideal_rep_duration = ideal_rep_duration
        self.weights = weights or self.WEIGHTS.copy()

    def evaluate_session(
        self,
        rep_summaries: List[RepFormSummary],
        frame_angles: Optional[List[float]] = None,
        frame_timestamps: Optional[List[float]] = None,
        frame_deviations: Optional[List[float]] = None,
        rep_durations: Optional[List[float]] = None,
    ) -> PerformanceScoreBreakdown:
        """
        Evaluates a completed workout session and computes the Performance Score.
        
        Args:
            rep_summaries: List of completed RepFormSummary objects from SquatFormAnalyzer.
            frame_angles: Sequential list of measured joint angles across the session.
            frame_timestamps: Sequential list of frame timestamps (seconds).
            frame_deviations: Sequential list of lateral knee deviations.
            rep_durations: Optional list of durations per completed rep in seconds.
            
        Returns:
            PerformanceScoreBreakdown containing overall score, rating, and component scores.
        """
        num_reps = len(rep_summaries)

        # Handle zero-rep edge case safely
        if num_reps == 0:
            return PerformanceScoreBreakdown(
                overall_score=0.0,
                rating="NEEDS_IMPROVEMENT",
                rom_consistency=0.0,
                tempo_consistency=0.0,
                stability=0.0,
                form_accuracy=0.0,
                smoothness=0.0,
                symmetry=0.0,
                completion_quality=0.0,
                total_reps=0,
                full_reps=0,
                shallow_reps=0,
                average_depth=0.0,
                average_duration=0.0,
                feedback_summary=["No complete repetitions recorded in this session."],
            )

        # 1. ROM Consistency (15%)
        rom_score, avg_depth = self._calculate_rom_consistency(rep_summaries)

        # 2. Tempo Consistency (10%)
        tempo_score, avg_duration = self._calculate_tempo_consistency(rep_durations)

        # 3. Stability (15%)
        stability_score = self._calculate_stability(rep_summaries, frame_deviations)

        # 4. Form Accuracy (25%)
        form_score = self._calculate_form_accuracy(rep_summaries)

        # 5. Smoothness (10%)
        smoothness_score = self._calculate_smoothness(frame_angles, frame_timestamps)

        # 6. Symmetry (5%)
        symmetry_score = self._calculate_symmetry(rep_summaries)

        # 7. Completion Quality (20%) - Tackles the shallow/half-squat issue!
        completion_score, full_count, shallow_count = self._calculate_completion_quality(rep_summaries)

        # Weighted Aggregate Overall Score
        overall = (
            self.weights["form_accuracy"] * form_score
            + self.weights["completion_quality"] * completion_score
            + self.weights["stability"] * stability_score
            + self.weights["rom_consistency"] * rom_score
            + self.weights["tempo_consistency"] * tempo_score
            + self.weights["smoothness"] * smoothness_score
            + self.weights["symmetry"] * symmetry_score
        )
        overall = float(np.clip(overall, 0.0, 100.0))

        # Qualitative Rating
        if overall >= 90.0:
            rating = "EXCELLENT"
        elif overall >= 75.0:
            rating = "GOOD"
        elif overall >= 60.0:
            rating = "FAIR"
        else:
            rating = "NEEDS_IMPROVEMENT"

        # Actionable feedback summary
        cues = self._generate_feedback_summary(
            form_score, completion_score, rom_score, stability_score, tempo_score, shallow_count
        )

        return PerformanceScoreBreakdown(
            overall_score=overall,
            rating=rating,
            rom_consistency=rom_score,
            tempo_consistency=tempo_score,
            stability=stability_score,
            form_accuracy=form_score,
            smoothness=smoothness_score,
            symmetry=symmetry_score,
            completion_quality=completion_score,
            total_reps=num_reps,
            full_reps=full_count,
            shallow_reps=shallow_count,
            average_depth=avg_depth,
            average_duration=avg_duration,
            feedback_summary=cues,
        )

    def _calculate_rom_consistency(self, summaries: List[RepFormSummary]) -> Tuple[float, float]:
        """Calculates consistency of peak squat depth across repetitions."""
        depths = [rep.min_knee_angle for rep in summaries]
        avg_depth = float(np.mean(depths))

        if len(depths) < 2:
            # Single rep: score by proximity to ideal depth
            dev = abs(avg_depth - self.ideal_depth)
            score = max(0.0, 100.0 - (dev * 1.5))
            return float(score), avg_depth

        std_dev = float(np.std(depths))
        # Standard deviation > 15 deg reduces score to 0
        score = max(0.0, 100.0 - (std_dev / 15.0 * 100.0))
        return float(score), avg_depth

    def _calculate_tempo_consistency(self, durations: Optional[List[float]]) -> Tuple[float, float]:
        """Calculates pace stability and adherence to controlled tempo."""
        if not durations or len(durations) == 0:
            return 80.0, self.ideal_rep_duration

        avg_dur = float(np.mean(durations))

        if len(durations) < 2:
            # Single rep: check if duration is within healthy range [2.0, 4.5] s
            diff = abs(avg_dur - self.ideal_rep_duration)
            score = max(0.0, 100.0 - (diff * 25.0))
            return float(score), avg_dur

        std_dev = float(np.std(durations))
        # Std dev > 1.5 seconds drops tempo score to 0
        score = max(0.0, 100.0 - (std_dev / 1.5 * 100.0))
        return float(score), avg_dur

    def _calculate_stability(
        self,
        summaries: List[RepFormSummary],
        deviations: Optional[List[float]],
    ) -> float:
        """Measures lateral joint wobble and deviation from ideal alignment plane."""
        if deviations and len(deviations) > 0:
            mean_dev = float(np.mean(deviations))
            score = max(0.0, 100.0 - (mean_dev / 0.35 * 100.0))
            return float(score)

        # Fallback to rep summary status
        misaligned_reps = sum(1 for r in summaries if r.knee_alignment_status != "ALIGNED")
        score = max(0.0, 100.0 - ((misaligned_reps / len(summaries)) * 100.0))
        return float(score)

    def _calculate_form_accuracy(self, summaries: List[RepFormSummary]) -> float:
        """Evaluates form rule adherence with deductions for kinematic violations."""
        total_deductions = 0.0
        for rep in summaries:
            for v in rep.violations:
                if v == VIOLATION_INSUFFICIENT_DEPTH:
                    total_deductions += 15.0
                elif v == VIOLATION_EXCESSIVE_TORSO_LEAN:
                    total_deductions += 10.0
                elif v == VIOLATION_KNEE_ALIGNMENT:
                    total_deductions += 10.0
                else:
                    total_deductions += 5.0

        avg_deduction = total_deductions / len(summaries)
        return float(max(0.0, 100.0 - avg_deduction))

    def _calculate_smoothness(
        self,
        angles: Optional[List[float]],
        timestamps: Optional[List[float]],
    ) -> float:
        """Measures trajectory jerk (derivative of angular acceleration) to detect shaking/jitter."""
        if not angles or len(angles) < 5 or not timestamps or len(timestamps) < 5:
            return 85.0  # Reasonable baseline when frame stream not provided

        dt = np.diff(timestamps)
        dt = np.where(dt <= 0, 0.033, dt)  # guard against non-monotonic timestamps

        # First derivative: Angular velocity (deg/s)
        velocity = np.diff(angles) / dt

        # Second derivative: Angular acceleration (deg/s^2)
        acceleration = np.diff(velocity) / dt[1:]

        # Third derivative: Jerk (deg/s^3)
        jerk = np.diff(acceleration) / dt[2:]

        mean_abs_jerk = float(np.mean(np.abs(jerk)))
        # Empirical scaling for human joint kinematics jerk (clean squat jerk < 400 deg/s^3)
        score = max(0.0, 100.0 - (mean_abs_jerk / 1500.0 * 100.0))
        return float(score)

    def _calculate_symmetry(self, summaries: List[RepFormSummary]) -> float:
        """Measures bilateral kinematic symmetry across both limbs."""
        # Baseline high symmetry unless lateral deviations are detected
        asymmetric_reps = sum(
            1 for r in summaries if VIOLATION_KNEE_ALIGNMENT in r.violations
        )
        score = max(0.0, 100.0 - ((asymmetric_reps / len(summaries)) * 40.0))
        return float(score)

    def _calculate_completion_quality(self, summaries: List[RepFormSummary]) -> Tuple[float, int, int]:
        """
        Solves the Known Half-Squat Issue!
        Distinguishes full depth reps (knee angle <= 100 deg) from shallow / half squats.
        """
        full_reps = 0
        shallow_reps = 0

        for r in summaries:
            if r.depth_status == "ADEQUATE" and r.min_knee_angle <= 100.0:
                full_reps += 1
            else:
                shallow_reps += 1

        total = len(summaries)
        if total == 0:
            return 0.0, 0, 0

        score = (full_reps / total) * 100.0
        return float(score), full_reps, shallow_reps

    def _generate_feedback_summary(
        self,
        form: float,
        completion: float,
        rom: float,
        stability: float,
        tempo: float,
        shallow_reps: int,
    ) -> List[str]:
        """Produces prioritized actionable coaching recommendations."""
        cues = []
        if shallow_reps > 0:
            cues.append(f"{shallow_reps} repetition(s) lacked full depth. Focus on reaching parallel.")
        if form < 75.0:
            cues.append("Chest dropped forward during descent. Keep your core tight and gaze forward.")
        if stability < 75.0:
            cues.append("Knee wobble detected. Push your knees outward over your mid-toes.")
        if tempo < 75.0:
            cues.append("Repetition tempo was inconsistent. Aim for a 2-second descent and 1-second rise.")
        if not cues:
            cues.append("Excellent execution! Consistent depth, stable trajectory, and strong posture.")
        return cues
