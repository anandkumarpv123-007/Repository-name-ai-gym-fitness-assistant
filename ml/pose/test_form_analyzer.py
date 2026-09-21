"""
AI Gym & Fitness Assistant — Phase 2.4 Automated Test Suite
Squat Form Analysis & Real-Time Feedback

Mandatory test coverage:
1. Good squat posture -> no violations, 'valid=True'.
2. Insufficient depth -> INSUFFICIENT_DEPTH violation + 'Go slightly deeper.'
3. Detectable knee alignment problem -> KNEE_ALIGNMENT_ISSUE + 'Keep your knees aligned with your feet.'
4. Excessive forward torso lean -> EXCESSIVE_TORSO_LEAN + 'Keep your chest more upright.'
5. Poor landmark visibility -> valid=False, insufficient_data, no fabricated form judgments.
6. Multiple simultaneous violations -> all relevant violations returned together.
7. Correct feedback generated for each violation.
8. No false feedback when posture is acceptable.
9. Rep-level summary aggregation on rep completion.
10. Real MediaPipe fixture integration test on sample_person.png.
"""

import math
import os
import sys
import unittest
import cv2
import numpy as np

# Ensure project root is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.pose.form_analyzer import (
    SquatFormAnalyzer,
    FormAnalysisResult,
    RepFormSummary,
    VIOLATION_INSUFFICIENT_DEPTH,
    VIOLATION_EXCESSIVE_TORSO_LEAN,
    VIOLATION_KNEE_ALIGNMENT,
    FEEDBACK_INSUFFICIENT_DEPTH,
    FEEDBACK_EXCESSIVE_TORSO_LEAN,
    FEEDBACK_KNEE_ALIGNMENT,
    FEEDBACK_GOOD_FORM,
    FEEDBACK_INSUFFICIENT_DATA,
)
from ml.pose.pose_detector import PoseDetector, PoseDetectionResult, PoseLandmarkPoint
from ml.pose.squat_state_machine import SquatStateMachine, SquatMovementResult, SquatState
from ml.pose.visualizer import draw_pose_landmarks


FIXTURE_PATH = os.path.join(PROJECT_ROOT, "ml", "fixtures", "sample_person.png")


def create_synthetic_pose(
    shoulder_pos=(200, 100),
    hip_pos=(200, 250),
    knee_pos=(200, 370),
    ankle_pos=(200, 480),
    visibility: float = 0.95,
    side: str = "LEFT",
) -> PoseDetectionResult:
    """Helper creating a deterministic PoseDetectionResult with 33 landmarks."""
    landmarks: list[PoseLandmarkPoint] = []
    landmark_dict: dict[str, PoseLandmarkPoint] = {}

    for i in range(33):
        pt = PoseLandmarkPoint(
            id=i,
            name=f"LANDMARK_{i}",
            x=0.5,
            y=0.5,
            z=0.0,
            visibility=visibility,
            presence=visibility,
            pixel_x=320,
            pixel_y=240,
        )
        landmarks.append(pt)

    # Key anatomical joints
    key_points = [
        (f"{side}_SHOULDER", shoulder_pos),
        (f"{side}_HIP", hip_pos),
        (f"{side}_KNEE", knee_pos),
        (f"{side}_ANKLE", ankle_pos),
    ]
    for name, pos in key_points:
        pt = PoseLandmarkPoint(
            id=len(landmark_dict),
            name=name,
            x=pos[0] / 640.0,
            y=pos[1] / 480.0,
            z=0.0,
            visibility=visibility,
            presence=visibility,
            pixel_x=pos[0],
            pixel_y=pos[1],
        )
        landmark_dict[name] = pt

    return PoseDetectionResult(
        detected=True,
        landmarks=landmarks,
        landmark_dict=landmark_dict,
        image_width=640,
        image_height=480,
    )


class TestSquatFormAnalyzer(unittest.TestCase):
    """Unit tests for rule-based biomechanical form analysis."""

    def setUp(self):
        self.analyzer = SquatFormAnalyzer(
            depth_threshold=100.0,
            max_torso_lean=45.0,
            knee_deviation_threshold=0.35,
            min_visibility=0.5,
            side="LEFT",
        )

    def test_01_good_squat_posture_no_violations(self):
        """Standard upright standing posture -> no violations, good posture feedback."""
        # Upright torso: shoulder directly above hip (dx=0 -> 0 deg lean)
        # Knee and ankle aligned vertically
        pose = create_synthetic_pose(
            shoulder_pos=(200, 100),
            hip_pos=(200, 250),
            knee_pos=(200, 370),
            ankle_pos=(200, 480),
        )
        result = self.analyzer.analyze_frame(pose)

        self.assertTrue(result.valid)
        self.assertEqual(len(result.violations), 0)
        self.assertEqual(result.torso_status, "UPRIGHT")
        self.assertEqual(result.knee_alignment_status, "ALIGNED")
        self.assertIn(FEEDBACK_GOOD_FORM, result.feedback)

    def test_02_insufficient_depth_violation(self):
        """User at bottom phase but knee angle > 100 deg -> INSUFFICIENT_DEPTH."""
        # Shallow squat knee angle (~120 deg)
        pose = create_synthetic_pose(
            shoulder_pos=(200, 120),
            hip_pos=(200, 260),
            knee_pos=(240, 350),
            ankle_pos=(200, 450),
        )
        movement = SquatMovementResult(
            current_angle=120.0,
            smoothed_angle=120.0,
            state=SquatState.BOTTOM,
            reps=0,
            landmark_valid=True,
        )
        result = self.analyzer.analyze_frame(pose, movement_result=movement)

        self.assertTrue(result.valid)
        self.assertIn(VIOLATION_INSUFFICIENT_DEPTH, result.violations)
        self.assertIn(FEEDBACK_INSUFFICIENT_DEPTH, result.feedback)
        self.assertEqual(result.depth_status, "INSUFFICIENT")

    def test_03_knee_alignment_issue(self):
        """Knee laterally displaced far away from ankle -> KNEE_ALIGNMENT_ISSUE."""
        # dy = |480 - 360| = 120; dx = |300 - 200| = 100 -> ratio = 100/120 = 0.83 > 0.35
        pose = create_synthetic_pose(
            shoulder_pos=(200, 100),
            hip_pos=(200, 250),
            knee_pos=(300, 360),
            ankle_pos=(200, 480),
        )
        result = self.analyzer.analyze_frame(pose)

        self.assertTrue(result.valid)
        self.assertIn(VIOLATION_KNEE_ALIGNMENT, result.violations)
        self.assertIn(FEEDBACK_KNEE_ALIGNMENT, result.feedback)
        self.assertEqual(result.knee_alignment_status, "MISALIGNED")

    def test_04_excessive_torso_lean_violation(self):
        """Shoulder displaced forward relative to hip -> EXCESSIVE_TORSO_LEAN."""
        # dx = |350 - 200| = 150; dy = 260 - 120 = 140 -> angle = arctan(150/140) = 47.0 deg > 45 deg
        pose = create_synthetic_pose(
            shoulder_pos=(350, 120),
            hip_pos=(200, 260),
            knee_pos=(200, 360),
            ankle_pos=(200, 480),
        )
        result = self.analyzer.analyze_frame(pose)

        self.assertTrue(result.valid)
        self.assertIn(VIOLATION_EXCESSIVE_TORSO_LEAN, result.violations)
        self.assertIn(FEEDBACK_EXCESSIVE_TORSO_LEAN, result.feedback)
        self.assertEqual(result.torso_status, "EXCESSIVE_LEAN")

    def test_05_poor_landmark_visibility_safely_rejected(self):
        """If key landmarks have visibility < 0.5 -> valid=False, no fabricated form judgments."""
        pose = create_synthetic_pose(
            shoulder_pos=(200, 100),
            hip_pos=(200, 250),
            knee_pos=(200, 370),
            ankle_pos=(200, 480),
            visibility=0.20,  # Below threshold!
        )
        result = self.analyzer.analyze_frame(pose)

        self.assertFalse(result.valid)
        self.assertEqual(len(result.violations), 0)
        self.assertEqual(result.torso_status, "UNKNOWN")
        self.assertEqual(result.depth_status, "UNKNOWN")
        self.assertIn(FEEDBACK_INSUFFICIENT_DATA, result.feedback)

    def test_06_multiple_simultaneous_violations(self):
        """Both insufficient depth and excessive torso lean occur at once -> both reported."""
        pose = create_synthetic_pose(
            shoulder_pos=(360, 130),  # Forward torso lean (> 45 deg)
            hip_pos=(200, 260),
            knee_pos=(200, 360),
            ankle_pos=(200, 480),
        )
        movement = SquatMovementResult(
            current_angle=118.0,
            smoothed_angle=118.0,
            state=SquatState.BOTTOM,
            reps=0,
            landmark_valid=True,
        )
        result = self.analyzer.analyze_frame(pose, movement_result=movement)

        self.assertTrue(result.valid)
        self.assertIn(VIOLATION_INSUFFICIENT_DEPTH, result.violations)
        self.assertIn(VIOLATION_EXCESSIVE_TORSO_LEAN, result.violations)
        self.assertIn(FEEDBACK_INSUFFICIENT_DEPTH, result.feedback)
        self.assertIn(FEEDBACK_EXCESSIVE_TORSO_LEAN, result.feedback)

    def test_07_rep_level_summary_aggregation(self):
        """When rep_completed=True, a structured RepFormSummary is returned and logged."""
        pose = create_synthetic_pose(
            shoulder_pos=(200, 100),
            hip_pos=(200, 250),
            knee_pos=(200, 370),
            ankle_pos=(200, 480),
        )
        # Simulate passing through bottom at 90 deg (adequate depth)
        movement_bottom = SquatMovementResult(
            current_angle=90.0,
            smoothed_angle=90.0,
            state=SquatState.BOTTOM,
            reps=0,
            landmark_valid=True,
        )
        self.analyzer.analyze_frame(pose, movement_result=movement_bottom)

        # Rep completion frame
        movement_finish = SquatMovementResult(
            current_angle=165.0,
            smoothed_angle=165.0,
            state=SquatState.UP,
            reps=1,
            landmark_valid=True,
            rep_completed=True,
        )
        res_finish = self.analyzer.analyze_frame(pose, movement_result=movement_finish)

        self.assertIsNotNone(res_finish.rep_summary)
        summary: RepFormSummary = res_finish.rep_summary
        self.assertEqual(summary.rep_number, 1)
        self.assertEqual(summary.depth_status, "ADEQUATE")
        self.assertTrue(summary.passed)
        self.assertEqual(len(self.analyzer.rep_summaries), 1)

    def test_09_feedback_content_mapping(self):
        """Verifies exact user-facing feedback messages match each distinct violation."""
        # 1. Torso lean feedback
        pose_torso = create_synthetic_pose(shoulder_pos=(350, 120), hip_pos=(200, 260))
        res_torso = self.analyzer.analyze_frame(pose_torso)
        self.assertIn(FEEDBACK_EXCESSIVE_TORSO_LEAN, res_torso.feedback)

        # 2. Knee alignment feedback
        pose_knee = create_synthetic_pose(knee_pos=(300, 360), ankle_pos=(200, 480))
        res_knee = self.analyzer.analyze_frame(pose_knee)
        self.assertIn(FEEDBACK_KNEE_ALIGNMENT, res_knee.feedback)

        # 3. Insufficient depth feedback
        pose_depth = create_synthetic_pose()
        m_depth = SquatMovementResult(
            current_angle=120.0, smoothed_angle=120.0, state=SquatState.BOTTOM, reps=0, landmark_valid=True
        )
        res_depth = self.analyzer.analyze_frame(pose_depth, movement_result=m_depth)
        self.assertIn(FEEDBACK_INSUFFICIENT_DEPTH, res_depth.feedback)

    def test_10_no_false_feedback_when_acceptable(self):
        """When torso is within acceptable natural lean (< 45 deg), no violation is triggered."""
        # 30 degree lean: dx = 200 * tan(30) ~ 115 px.
        pose_acceptable = create_synthetic_pose(
            shoulder_pos=(280, 100),  # dx=80, dy=150 -> arctan(80/150) = 28 deg < 45 deg
            hip_pos=(200, 250),
            knee_pos=(200, 370),
            ankle_pos=(200, 480),
        )
        res = self.analyzer.analyze_frame(pose_acceptable)
        self.assertEqual(res.torso_status, "ACCEPTABLE")
        self.assertEqual(len(res.violations), 0)
        self.assertNotIn(FEEDBACK_EXCESSIVE_TORSO_LEAN, res.feedback)

    def test_11_squat_counting_with_form_analyzer(self):
        """Existing Phase 2.3 squat counting is preserved when form analyzer is active."""
        fsm = SquatStateMachine(up_threshold=160.0, bottom_threshold=100.0, hysteresis=5.0, smoothing_window=1)
        angles = [170.0, 140.0, 95.0, 130.0, 165.0]

        for a in angles:
            m = fsm.process_angle(a)
            # Create synthetic pose matching angle
            pose = create_synthetic_pose()
            form_res = self.analyzer.analyze_frame(pose, movement_result=m)

        # 1 rep counted
        self.assertEqual(fsm.rep_count, 1)
        self.assertEqual(len(self.analyzer.rep_summaries), 1)
        self.assertEqual(self.analyzer.rep_summaries[0].rep_number, 1)

    def test_12_real_mediapipe_fixture_integration(self):
        """End-to-end integration test with real MediaPipe fixture sample_person.png."""
        self.assertTrue(os.path.isfile(FIXTURE_PATH))
        frame = cv2.imread(FIXTURE_PATH)
        self.assertIsNotNone(frame)

        detector = PoseDetector()
        try:
            pose_result = detector.detect(frame)
            self.assertTrue(pose_result.detected)

            fsm = SquatStateMachine(side="LEFT")
            movement_res = fsm.process_frame_landmarks(pose_result)

            form_res = self.analyzer.analyze_frame(pose_result, movement_res)

            self.assertTrue(form_res.valid)
            self.assertIsNotNone(form_res.knee_angle)
            self.assertIsNotNone(form_res.torso_angle)
            self.assertIn(form_res.torso_status, ["UPRIGHT", "ACCEPTABLE"])

            # Verify HUD rendering doesn't raise errors
            annotated = draw_pose_landmarks(
                frame,
                pose_result,
                movement_result=movement_res,
                form_result=form_res,
            )
            self.assertIsInstance(annotated, np.ndarray)
            self.assertEqual(annotated.shape, frame.shape)
        finally:
            detector.close()


def run_suite():
    print("=" * 70)
    print("PHASE 2.4 — SQUAT FORM ANALYZER AUTOMATED TESTS")
    print("=" * 70)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSquatFormAnalyzer)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("=" * 70)
    if result.wasSuccessful():
        print(f"[ALL {result.testsRun} PHASE 2.4 TESTS PASSED SUCCESSFULLY]")
        return 0
    else:
        print(f"[FAILED: {len(result.failures)}, ERRORS: {len(result.errors)}]")
        return 1


if __name__ == "__main__":
    sys.exit(run_suite())
