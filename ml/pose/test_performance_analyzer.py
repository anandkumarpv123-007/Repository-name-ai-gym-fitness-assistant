"""
AI Gym & Fitness Assistant — Performance Analyzer Automated Test Suite
Phase 2 — AI Gym Trainer & Pose-to-Performance System

Verifies:
1. High-quality execution yields EXCELLENT score (>= 90).
2. Range of Motion (ROM) consistency deductions when depth varies significantly.
3. Half/Shallow squat detection & completion quality penalty.
4. Form violation penalties (torso lean, knee cave).
5. Inconsistent pacing & tempo deductions.
6. Zero-rep and single-rep edge cases handled cleanly.
7. Trajectory jerk/smoothness evaluation.
8. Qualitative rating scales and actionable coaching cue generation.
"""

import os
import sys
import unittest
import numpy as np

# Ensure project root is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.pose.form_analyzer import (
    RepFormSummary,
    VIOLATION_INSUFFICIENT_DEPTH,
    VIOLATION_EXCESSIVE_TORSO_LEAN,
    VIOLATION_KNEE_ALIGNMENT,
)
from ml.pose.performance_analyzer import PerformanceAnalyzer, PerformanceScoreBreakdown


class TestPerformanceAnalyzer(unittest.TestCase):
    """Unit tests for 7-factor deterministic performance scoring engine."""

    def setUp(self):
        self.analyzer = PerformanceAnalyzer(ideal_depth=90.0, ideal_rep_duration=3.0)

    def _make_rep(
        self,
        rep_number: int,
        min_knee_angle: float = 90.0,
        max_torso_lean: float = 25.0,
        depth_status: str = "ADEQUATE",
        knee_status: str = "ALIGNED",
        torso_status: str = "UPRIGHT",
        violations: list = None,
    ) -> RepFormSummary:
        viols = violations or []
        return RepFormSummary(
            rep_number=rep_number,
            depth_status=depth_status,
            knee_alignment_status=knee_status,
            torso_status=torso_status,
            min_knee_angle=min_knee_angle,
            max_torso_lean=max_torso_lean,
            violations=viols,
            feedback=[],
            passed=len(viols) == 0,
        )

    def test_01_excellent_session_score(self):
        """Clean, consistent reps with good depth and upright torso achieve EXCELLENT score (>= 90)."""
        reps = [
            self._make_rep(1, min_knee_angle=90.0),
            self._make_rep(2, min_knee_angle=91.0),
            self._make_rep(3, min_knee_angle=89.5),
            self._make_rep(4, min_knee_angle=90.5),
            self._make_rep(5, min_knee_angle=90.0),
        ]
        durations = [3.0, 3.1, 2.9, 3.0, 3.1]
        breakdown = self.analyzer.evaluate_session(reps, rep_durations=durations)

        self.assertGreaterEqual(breakdown.overall_score, 90.0)
        self.assertEqual(breakdown.rating, "EXCELLENT")
        self.assertEqual(breakdown.full_reps, 5)
        self.assertEqual(breakdown.shallow_reps, 0)
        self.assertAlmostEqual(breakdown.completion_quality, 100.0)

    def test_02_rom_inconsistency_penalty(self):
        """Erratic depths across reps significantly degrade the ROM consistency score."""
        # Rep depths ranging wildly from 75 deg to 125 deg
        reps = [
            self._make_rep(1, min_knee_angle=75.0),
            self._make_rep(2, min_knee_angle=120.0),
            self._make_rep(3, min_knee_angle=85.0),
            self._make_rep(4, min_knee_angle=115.0),
        ]
        breakdown = self.analyzer.evaluate_session(reps)

        # ROM consistency should suffer heavily
        self.assertLess(breakdown.rom_consistency, 60.0)

    def test_03_half_squats_penalized_in_completion_quality(self):
        """Direct verification of the Known Half-Squat Issue solution."""
        # 3 full squats, 2 shallow/half squats
        reps = [
            self._make_rep(1, min_knee_angle=88.0, depth_status="ADEQUATE"),
            self._make_rep(2, min_knee_angle=115.0, depth_status="INSUFFICIENT", violations=[VIOLATION_INSUFFICIENT_DEPTH]),
            self._make_rep(3, min_knee_angle=89.0, depth_status="ADEQUATE"),
            self._make_rep(4, min_knee_angle=118.0, depth_status="INSUFFICIENT", violations=[VIOLATION_INSUFFICIENT_DEPTH]),
            self._make_rep(5, min_knee_angle=91.0, depth_status="ADEQUATE"),
        ]
        breakdown = self.analyzer.evaluate_session(reps)

        self.assertEqual(breakdown.full_reps, 3)
        self.assertEqual(breakdown.shallow_reps, 2)
        # 3/5 full reps = exactly 60.0% completion quality
        self.assertAlmostEqual(breakdown.completion_quality, 60.0)
        # Actionable coaching cue must warn about shallow depth
        self.assertTrue(any("depth" in c.lower() for c in breakdown.feedback_summary))

    def test_04_form_violation_deductions(self):
        """Torso lean and knee cave violations systematically lower form accuracy."""
        reps = [
            self._make_rep(1, violations=[VIOLATION_EXCESSIVE_TORSO_LEAN]),
            self._make_rep(2, violations=[VIOLATION_KNEE_ALIGNMENT]),
            self._make_rep(3, violations=[VIOLATION_EXCESSIVE_TORSO_LEAN, VIOLATION_KNEE_ALIGNMENT]),
        ]
        breakdown = self.analyzer.evaluate_session(reps)

        # Average deductions: (10 + 10 + 20) / 3 = 13.3 -> score ~86.7
        self.assertLess(breakdown.form_accuracy, 90.0)
        self.assertGreater(breakdown.form_accuracy, 80.0)

    def test_05_tempo_consistency_deduction(self):
        """Wildly erratic rep durations degrade tempo score."""
        reps = [self._make_rep(i) for i in range(1, 5)]
        durations = [1.0, 5.5, 1.2, 6.0]  # Very erratic tempo
        breakdown = self.analyzer.evaluate_session(reps, rep_durations=durations)

        self.assertLess(breakdown.tempo_consistency, 60.0)

    def test_06_zero_reps_edge_case(self):
        """Zero completed reps produces 0 score and NEEDS_IMPROVEMENT without division by zero."""
        breakdown = self.analyzer.evaluate_session([])

        self.assertEqual(breakdown.overall_score, 0.0)
        self.assertEqual(breakdown.rating, "NEEDS_IMPROVEMENT")
        self.assertEqual(breakdown.total_reps, 0)
        self.assertIn("No complete repetitions", breakdown.feedback_summary[0])

    def test_07_single_rep_edge_case(self):
        """Single rep evaluated safely without std dev NaN."""
        rep = self._make_rep(1, min_knee_angle=92.0)
        breakdown = self.analyzer.evaluate_session([rep], rep_durations=[3.1])

        self.assertIsInstance(breakdown.overall_score, float)
        self.assertFalse(np.isnan(breakdown.overall_score))
        self.assertEqual(breakdown.total_reps, 1)

    def test_08_smoothness_jerk_evaluation(self):
        """Calculates trajectory jerk on synthetic frame data."""
        reps = [self._make_rep(1)]
        # Smooth sinusoidal trajectory
        t = np.linspace(0, 3.0, 60)
        angles = 135.0 + 45.0 * np.cos(2 * np.pi * t / 3.0)
        breakdown = self.analyzer.evaluate_session(reps, frame_angles=list(angles), frame_timestamps=list(t))

        self.assertGreater(breakdown.smoothness, 70.0)


def run_suite():
    print("=" * 70)
    print("PHASE 2.5 — PERFORMANCE ANALYZER AUTOMATED TESTS")
    print("=" * 70)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPerformanceAnalyzer)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("=" * 70)
    if result.wasSuccessful():
        print(f"[ALL {result.testsRun} PERFORMANCE ANALYZER TESTS PASSED]")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(run_suite())
