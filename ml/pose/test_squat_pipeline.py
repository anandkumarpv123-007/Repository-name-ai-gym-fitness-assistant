"""
AI Gym & Fitness Assistant — Phase 2.3 Automated Test Suite
Joint Angles + Squat State Machine + Rep Counting

Mandatory test coverage:
1. 2D Angle Calculation (known 90°, straight 180°, acute 45°, collinear, zero-length).
2. Landmark Visibility Validation (all visible -> valid, below threshold -> rejected).
3. Moving Average Smoothing (startup, windowing, noise reduction).
4. State Machine Rep Counting:
   - Complete squat -> 1 rep
   - Two complete squats -> 2 reps
   - Staying at bottom (~95°) -> zero extra reps
   - Incomplete squat (shallow dip) -> 0 reps
   - Noisy angle sequence stability (jitter around thresholds -> no false reps)
5. Real MediaPipe integration test on sample_person.png fixture.
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

from ml.pose.angle_calculator import calculate_angle_2d, calculate_landmark_angle
from ml.pose.pose_detector import PoseDetector, PoseLandmarkPoint
from ml.pose.smoothing import MovingAverageFilter, ExponentialMovingAverageFilter
from ml.pose.squat_state_machine import SquatState, SquatStateMachine, SquatMovementResult
from ml.pose.visualizer import draw_pose_landmarks, draw_movement_telemetry


FIXTURE_PATH = os.path.join(PROJECT_ROOT, "ml", "fixtures", "sample_person.png")


class TestAngleCalculation(unittest.TestCase):
    """Verifies geometric angle calculation under known mathematical conditions."""

    def test_known_90_degree_geometry(self):
        """Right angle: A=(0, 1), B=(0, 0), C=(1, 0) should equal exactly 90.0 degrees."""
        angle = calculate_angle_2d((0.0, 1.0), (0.0, 0.0), (1.0, 0.0))
        self.assertIsNotNone(angle)
        self.assertAlmostEqual(angle, 90.0, places=4)

    def test_known_180_degree_straight_line(self):
        """Collinear straight line: A=(0, 1), B=(0, 0), C=(0, -1) should equal 180.0 degrees."""
        angle = calculate_angle_2d((0.0, 1.0), (0.0, 0.0), (0.0, -1.0))
        self.assertIsNotNone(angle)
        self.assertAlmostEqual(angle, 180.0, places=4)

    def test_known_45_degree_geometry(self):
        """45-degree angle: A=(1, 1), B=(0, 0), C=(1, 0)."""
        angle = calculate_angle_2d((1.0, 1.0), (0.0, 0.0), (1.0, 0.0))
        self.assertIsNotNone(angle)
        self.assertAlmostEqual(angle, 45.0, places=4)

    def test_zero_length_vector_handling(self):
        """Points coinciding with vertex B: must return None safely without raising NaN/ZeroDivisionError."""
        # A coincides with B
        angle_a_b = calculate_angle_2d((0.0, 0.0), (0.0, 0.0), (1.0, 0.0))
        self.assertIsNone(angle_a_b)

        # C coincides with B
        angle_c_b = calculate_angle_2d((1.0, 0.0), (0.0, 0.0), (0.0, 0.0))
        self.assertIsNone(angle_c_b)

        # All points identical
        angle_all = calculate_angle_2d((5.0, 5.0), (5.0, 5.0), (5.0, 5.0))
        self.assertIsNone(angle_all)

    def test_invalid_and_empty_inputs(self):
        """Invalid types and empty sequences return None safely."""
        self.assertIsNone(calculate_angle_2d([], (0, 0), (1, 1)))
        self.assertIsNone(calculate_angle_2d((0, 0), None, (1, 1)))


class TestLandmarkVisibility(unittest.TestCase):
    """Verifies landmark visibility gatekeeping before geometric angle calculation."""

    def _make_point(self, name: str, x: float, y: float, vis: float) -> PoseLandmarkPoint:
        return PoseLandmarkPoint(
            id=0,
            name=name,
            x=x,
            y=y,
            z=0.0,
            visibility=vis,
            presence=vis,
            pixel_x=int(x * 640),
            pixel_y=int(y * 480),
        )

    def test_all_landmarks_visible_produces_angle(self):
        """When all three points exceed visibility threshold, angle is calculated."""
        hip = self._make_point("LEFT_HIP", 0.5, 0.2, 0.95)
        knee = self._make_point("LEFT_KNEE", 0.5, 0.5, 0.90)
        ankle = self._make_point("LEFT_ANKLE", 0.5, 0.8, 0.85)

        angle = calculate_landmark_angle(hip, knee, ankle, min_visibility=0.5)
        self.assertIsNotNone(angle)
        self.assertAlmostEqual(angle, 180.0, places=2)

    def test_low_visibility_on_one_point_is_rejected(self):
        """If any single point has visibility below threshold, result is None."""
        hip = self._make_point("LEFT_HIP", 0.5, 0.2, 0.95)
        knee = self._make_point("LEFT_KNEE", 0.5, 0.5, 0.30)  # Occluded knee!
        ankle = self._make_point("LEFT_ANKLE", 0.5, 0.8, 0.85)

        angle = calculate_landmark_angle(hip, knee, ankle, min_visibility=0.5)
        self.assertIsNone(angle)

    def test_none_landmark_is_rejected(self):
        """If any landmark is None, result is safely None."""
        hip = self._make_point("LEFT_HIP", 0.5, 0.2, 0.95)
        self.assertIsNone(calculate_landmark_angle(hip, None, hip))


class TestSmoothingFilters(unittest.TestCase):
    """Verifies moving average filtering under initial startup and noisy inputs."""

    def test_startup_and_window_filling(self):
        """Filter handles fewer samples than window_size by averaging available samples."""
        filter_sma = MovingAverageFilter(window_size=3)
        self.assertIsNone(filter_sma.current_value)

        # 1st sample
        val1 = filter_sma.update(100.0)
        self.assertAlmostEqual(val1, 100.0)

        # 2nd sample: average of 100 and 110 -> 105
        val2 = filter_sma.update(110.0)
        self.assertAlmostEqual(val2, 105.0)

        # 3rd sample: average of 100, 110, 120 -> 110
        val3 = filter_sma.update(120.0)
        self.assertAlmostEqual(val3, 110.0)

        # 4th sample: window evicts 100 -> average of 110, 120, 130 -> 120
        val4 = filter_sma.update(130.0)
        self.assertAlmostEqual(val4, 120.0)

    def test_filter_attenuates_jitter(self):
        """Alternating jitter around 160 is smoothed."""
        filter_sma = MovingAverageFilter(window_size=4)
        for s in [158.0, 162.0, 158.0, 162.0]:
            filter_sma.update(s)
        self.assertAlmostEqual(filter_sma.current_value, 160.0)

    def test_reset(self):
        filter_sma = MovingAverageFilter(window_size=3)
        filter_sma.update(100.0)
        filter_sma.reset()
        self.assertEqual(filter_sma.sample_count, 0)
        self.assertIsNone(filter_sma.current_value)


class TestSquatStateMachine(unittest.TestCase):
    """Verifies deterministic FSM state transitions and rep counting logic."""

    def setUp(self):
        self.fsm = SquatStateMachine(
            up_threshold=160.0,
            bottom_threshold=100.0,
            hysteresis=5.0,
            smoothing_window=1,  # Raw 1-sample pass for exact sequence boundary testing
        )

    def test_complete_single_squat_cycle(self):
        """UP -> DESCENDING -> BOTTOM -> ASCENDING -> UP yields exactly 1 rep."""
        angles = [
            170.0,  # UP
            150.0,  # DESCENDING (< 155)
            120.0,  # DESCENDING
            95.0,   # BOTTOM (<= 100)
            115.0,  # ASCENDING (> 105)
            140.0,  # ASCENDING
            165.0,  # UP (>= 160) -> Rep completed!
        ]
        results = [self.fsm.process_angle(a) for a in angles]

        self.assertEqual(self.fsm.rep_count, 1)
        self.assertEqual(self.fsm.current_state, SquatState.UP)
        self.assertTrue(results[-1].rep_completed)
        self.assertFalse(results[-2].rep_completed)

    def test_two_complete_squat_cycles(self):
        """Two full cycles yield exactly 2 reps."""
        # Rep 1
        for a in [170.0, 140.0, 90.0, 130.0, 165.0]:
            self.fsm.process_angle(a)
        self.assertEqual(self.fsm.rep_count, 1)

        # Rep 2
        for a in [170.0, 135.0, 85.0, 125.0, 162.0]:
            self.fsm.process_angle(a)
        self.assertEqual(self.fsm.rep_count, 2)

    def test_staying_at_bottom_does_not_increment_reps(self):
        """Holding at bottom (~95 deg) for 20 frames must never produce extra reps."""
        # Descend to bottom
        self.fsm.process_angle(170.0)
        self.fsm.process_angle(140.0)
        self.fsm.process_angle(95.0)
        self.assertEqual(self.fsm.current_state, SquatState.BOTTOM)

        # Hold at bottom for 20 consecutive frames
        for _ in range(20):
            res = self.fsm.process_angle(95.0)
            self.assertEqual(res.state, SquatState.BOTTOM)
            self.assertEqual(res.reps, 0)
            self.assertFalse(res.rep_completed)

        self.assertEqual(self.fsm.rep_count, 0)

    def test_incomplete_squat_aborted_early_yields_zero_reps(self):
        """Starting down but rising back up before reaching bottom threshold -> 0 reps."""
        angles = [
            170.0,  # UP
            140.0,  # DESCENDING
            120.0,  # DESCENDING (stopped above 100 bottom threshold!)
            145.0,  # aborted
            165.0,  # returned to standing
        ]
        for a in angles:
            self.fsm.process_angle(a)

        self.assertEqual(self.fsm.rep_count, 0)
        self.assertEqual(self.fsm.current_state, SquatState.UP)

    def test_noisy_signal_stability(self):
        """Simulate camera angle jitter (+-2 degrees) during movement; ensures reliable rep count."""
        fsm_smooth = SquatStateMachine(
            up_threshold=160.0,
            bottom_threshold=100.0,
            hysteresis=5.0,
            smoothing_window=5,
        )

        np.random.seed(42)

        def add_jitter(val):
            return val + float(np.random.uniform(-2.0, 2.0))

        # Standing
        for _ in range(10):
            fsm_smooth.process_angle(add_jitter(170.0))

        # Descending
        for angle in np.linspace(165.0, 95.0, 15):
            fsm_smooth.process_angle(add_jitter(angle))

        # Bottom
        for _ in range(8):
            fsm_smooth.process_angle(add_jitter(95.0))

        # Ascending
        for angle in np.linspace(100.0, 168.0, 15):
            fsm_smooth.process_angle(add_jitter(angle))

        # Full lockout
        for _ in range(5):
            fsm_smooth.process_angle(add_jitter(170.0))

        # Must count exactly 1 clean rep despite continuous noise
        self.assertEqual(fsm_smooth.rep_count, 1)

    # =========================================================================
    # Explicit Developer 1 Review Regression Tests for Rep Validation
    # =========================================================================

    def test_regression_shallow_half_squat_never_increments_rep(self):
        """
        REGRESSION CHECK 1: Shallow/Half Squat.
        Athlete descends only to 105° (above 100° bottom threshold) and ascends to 165°.
        FSM must abort to UP with 0 reps counted and rep_completed=False.
        """
        shallow_sequence = [170.0, 150.0, 130.0, 115.0, 105.0, 120.0, 140.0, 165.0]
        results = [self.fsm.process_angle(a) for a in shallow_sequence]

        self.assertEqual(self.fsm.rep_count, 0)
        self.assertEqual(self.fsm.current_state, SquatState.UP)
        self.assertFalse(any(r.rep_completed for r in results))
        self.assertIn("Squat not deep enough", results[-1].feedback_message)

    def test_regression_complete_squat_increments_rep(self):
        """
        REGRESSION CHECK 2: Complete Squat.
        Athlete descends to 85° (deep/parallel, below 100° threshold) and ascends to 165°.
        FSM must transition through BOTTOM and increment reps to exactly 1.
        """
        complete_sequence = [170.0, 150.0, 120.0, 85.0, 115.0, 140.0, 165.0]
        results = [self.fsm.process_angle(a) for a in complete_sequence]

        self.assertEqual(self.fsm.rep_count, 1)
        self.assertEqual(self.fsm.current_state, SquatState.UP)
        self.assertTrue(results[-1].rep_completed)

    def test_regression_incomplete_descent_yields_zero_reps(self):
        """
        REGRESSION CHECK 3: Incomplete Descent.
        Athlete dips slightly (170° -> 135° -> 140° -> 165°) without reaching bottom.
        FSM must abort without incrementing reps.
        """
        incomplete_sequence = [170.0, 145.0, 135.0, 140.0, 155.0, 165.0]
        for a in incomplete_sequence:
            self.fsm.process_angle(a)

        self.assertEqual(self.fsm.rep_count, 0)
        self.assertEqual(self.fsm.current_state, SquatState.UP)

    def test_regression_complete_return_to_up_required(self):
        """
        REGRESSION CHECK 4: Complete Return to UP.
        Athlete reaches valid depth (85°), ascends to 140° (not locked out), pausing.
        Rep count must NOT increment until user fully returns to up_threshold (>= 160°).
        """
        # Descend to 85° and rise partially to 140°
        for a in [170.0, 140.0, 85.0, 115.0, 140.0]:
            res = self.fsm.process_angle(a)

        self.assertEqual(self.fsm.current_state, SquatState.ASCENDING)
        self.assertEqual(self.fsm.rep_count, 0)
        self.assertFalse(res.rep_completed)

        # Now complete return to UP
        final_res = self.fsm.process_angle(162.0)
        self.assertEqual(self.fsm.current_state, SquatState.UP)
        self.assertEqual(self.fsm.rep_count, 1)
        self.assertTrue(final_res.rep_completed)

    def test_regression_multiple_valid_reps(self):
        """
        REGRESSION CHECK 5: Multiple Valid Reps.
        Athlete completes 3 consecutive full-depth squats (85°).
        FSM must increment reps accurately to 3 without dropping or duplicating.
        """
        for rep in range(1, 4):
            for a in [170.0, 140.0, 85.0, 115.0, 162.0]:
                self.fsm.process_angle(a)
            self.assertEqual(self.fsm.rep_count, rep)

        self.assertEqual(self.fsm.rep_count, 3)


class TestMediaPipeIntegration(unittest.TestCase):
    """Integration test verifying end-to-end pipeline on real MediaPipe detection fixture."""

    @classmethod
    def setUpClass(cls):
        cls.detector = PoseDetector()
        cls.fsm = SquatStateMachine(side="LEFT")

    @classmethod
    def tearDownClass(cls):
        cls.detector.close()

    def test_real_fixture_end_to_end(self):
        """Processes real image fixture through PoseDetector -> Angle -> SquatStateMachine -> Visualizer."""
        self.assertTrue(os.path.isfile(FIXTURE_PATH), f"Fixture not found at {FIXTURE_PATH}")
        frame = cv2.imread(FIXTURE_PATH)
        self.assertIsNotNone(frame)

        # 1. MediaPipe Pose Landmark Detection
        pose_result = self.detector.detect(frame)
        self.assertTrue(pose_result.detected)
        self.assertEqual(len(pose_result.landmarks), 33)

        # 2. Movement & Angle Analysis
        movement_result = self.fsm.process_frame_landmarks(pose_result)
        self.assertIsInstance(movement_result, SquatMovementResult)
        self.assertTrue(movement_result.landmark_valid)
        self.assertIsNotNone(movement_result.current_angle)
        self.assertIsNotNone(movement_result.smoothed_angle)

        # Knee angle of the athlete in fixture should be a valid angle between 0 and 180
        self.assertTrue(0.0 <= movement_result.smoothed_angle <= 180.0)

        # 3. Visualization Rendering with Telemetry HUD
        annotated = draw_pose_landmarks(frame, pose_result, movement_result=movement_result)
        self.assertIsInstance(annotated, np.ndarray)
        self.assertEqual(annotated.shape, frame.shape)


def run_suite():
    print("=" * 70)
    print("PHASE 2.3 — SQUAT PIPELINE & JOINT ANGLE AUTOMATED TESTS")
    print("=" * 70)
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print("=" * 70)
    if result.wasSuccessful():
        print(f"[ALL {result.testsRun} PHASE 2.3 TESTS PASSED SUCCESSFULLY]")
        return 0
    else:
        print(f"[FAILED: {len(result.failures)}, ERRORS: {len(result.errors)}]")
        return 1


if __name__ == "__main__":
    sys.exit(run_suite())
