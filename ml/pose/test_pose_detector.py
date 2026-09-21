"""
AI Gym & Fitness Assistant — Pose Detector Automated Test Suite
Phase 2.2 — OpenCV + MediaPipe Pose Pipeline

Runs deterministic automated tests against PoseDetector and Visualizer.
Verifies real inference using MediaPipe (no mocked detection), blank frames,
real human fixture image, landmark structure integrity, and visualizer safety.
"""

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

from ml.pose.pose_detector import PoseDetector, PoseDetectionResult, PoseLandmarkPoint
from ml.pose.visualizer import draw_pose_landmarks, save_annotated_frame


FIXTURE_PATH = os.path.join(PROJECT_ROOT, "ml", "fixtures", "sample_person.png")
OUTPUT_TEMP_PATH = os.path.join(PROJECT_ROOT, "ml", "fixtures", "test_output_annotated.png")


class TestPoseDetector(unittest.TestCase):
    """Automated test cases for PoseDetector and Visualizer."""

    @classmethod
    def setUpClass(cls):
        """Initialize the detector once for test efficiency."""
        print("\n--- [SETUP] Initializing PoseDetector ---")
        cls.detector = PoseDetector(
            min_detection_confidence=0.5,
            min_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    @classmethod
    def tearDownClass(cls):
        """Clean up detector resources and any test outputs."""
        cls.detector.close()
        if os.path.exists(OUTPUT_TEMP_PATH):
            try:
                os.remove(OUTPUT_TEMP_PATH)
            except OSError:
                pass
        print("--- [TEARDOWN] PoseDetector Closed Cleanly ---")

    def test_01_detector_initialization(self):
        """Verifies PoseDetector initializes successfully and model file is valid."""
        self.assertIsNotNone(self.detector)
        self.assertTrue(os.path.isfile(self.detector.model_path))
        self.assertTrue(self.detector.model_path.endswith(".task"))
        print("  -> PASS: Test 1: Detector initialized and model asset verified.")

    def test_02_context_manager(self):
        """Verifies PoseDetector functions properly as a Python context manager."""
        with PoseDetector() as temp_detector:
            self.assertIsNotNone(temp_detector._landmarker)
        print("  -> PASS: Test 2: Context manager entered and exited cleanly.")

    def test_03_none_and_empty_frame(self):
        """Verifies that passing None or an empty frame is safely handled without raising exceptions."""
        result_none = self.detector.detect(None)
        self.assertIsInstance(result_none, PoseDetectionResult)
        self.assertFalse(result_none.detected)
        self.assertEqual(len(result_none.landmarks), 0)

        empty_frame = np.array([], dtype=np.uint8)
        result_empty = self.detector.detect(empty_frame)
        self.assertFalse(result_empty.detected)
        print("  -> PASS: Test 3: None and empty frame inputs handled safely.")

    def test_04_no_person_frame(self):
        """Verifies that a blank black frame returns detected=False and empty landmark lists."""
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = self.detector.detect(blank_frame)

        self.assertIsInstance(result, PoseDetectionResult)
        self.assertFalse(result.detected)
        self.assertEqual(len(result.landmarks), 0)
        self.assertEqual(len(result.landmark_dict), 0)
        self.assertEqual(result.image_width, 640)
        self.assertEqual(result.image_height, 480)
        print("  -> PASS: Test 4: Blank no-person frame processed safely with zero landmarks.")

    def test_05_detected_person_fixture(self):
        """Verifies that an image of a real human produces detected=True and exactly 33 landmarks."""
        self.assertTrue(
            os.path.isfile(FIXTURE_PATH),
            f"Test fixture not found at {FIXTURE_PATH}",
        )
        frame = cv2.imread(FIXTURE_PATH)
        self.assertIsNotNone(frame, "Failed to load sample fixture image with OpenCV.")

        result = self.detector.detect(frame)
        self.assertTrue(result.detected, "Expected human pose to be detected in fixture image.")
        self.assertEqual(
            len(result.landmarks),
            33,
            f"Expected 33 standard MediaPipe pose landmarks, got {len(result.landmarks)}.",
        )
        print(f"  -> PASS: Test 5: Real human fixture detected with {len(result.landmarks)} landmarks.")

    def test_06_landmark_structure_and_types(self):
        """Validates the schema, types, and mathematical bounds of all returned landmarks."""
        frame = cv2.imread(FIXTURE_PATH)
        result = self.detector.detect(frame)
        self.assertTrue(result.detected)

        h, w = frame.shape[:2]

        for i, lm in enumerate(result.landmarks):
            self.assertIsInstance(lm, PoseLandmarkPoint)
            self.assertEqual(lm.id, i)
            self.assertIsInstance(lm.name, str)
            self.assertTrue(len(lm.name) > 0)

            # Normalized coordinate bounds
            self.assertIsInstance(lm.x, float)
            self.assertIsInstance(lm.y, float)
            self.assertIsInstance(lm.z, float)

            # Pixel coordinate bounds
            self.assertIsInstance(lm.pixel_x, int)
            self.assertIsInstance(lm.pixel_y, int)
            self.assertTrue(0 <= lm.pixel_x < w, f"pixel_x {lm.pixel_x} out of bounds [0, {w})")
            self.assertTrue(0 <= lm.pixel_y < h, f"pixel_y {lm.pixel_y} out of bounds [0, {h})")

            # Confidence scores
            self.assertIsInstance(lm.visibility, float)
            self.assertIsInstance(lm.presence, float)
            self.assertTrue(0.0 <= lm.visibility <= 1.0)
            self.assertTrue(0.0 <= lm.presence <= 1.0)

            # Serialization to dict
            d = lm.to_dict()
            self.assertEqual(d["id"], i)
            self.assertEqual(d["name"], lm.name)

        # Full result dictionary
        result_dict = result.to_dict()
        self.assertTrue(result_dict["detected"])
        self.assertEqual(result_dict["landmark_count"], 33)
        print("  -> PASS: Test 6: Landmark schema, bounds, pixel coords, and serialization verified.")

    def test_07_landmark_lookups(self):
        """Verifies lookup helpers by both landmark name string and integer ID."""
        frame = cv2.imread(FIXTURE_PATH)
        result = self.detector.detect(frame)

        # Lookup by name
        nose = result.get("NOSE")
        self.assertIsNotNone(nose)
        self.assertEqual(nose.id, 0)
        self.assertEqual(nose.name, "NOSE")

        left_shoulder = result.get("LEFT_SHOULDER")
        self.assertIsNotNone(left_shoulder)
        self.assertEqual(left_shoulder.id, 11)

        right_shoulder = result.get("RIGHT_SHOULDER")
        self.assertIsNotNone(right_shoulder)
        self.assertEqual(right_shoulder.id, 12)

        # Lookup by integer ID
        lm_0 = result.get(0)
        self.assertEqual(lm_0.name, "NOSE")

        # Invalid lookups
        self.assertIsNone(result.get("NON_EXISTENT_JOINT"))
        self.assertIsNone(result.get(999))
        print("  -> PASS: Test 7: Landmark lookups by name and index verified.")

    def test_08_visualizer_on_detected_person(self):
        """Verifies that drawing annotations on a detected person frame succeeds without errors."""
        frame = cv2.imread(FIXTURE_PATH)
        result = self.detector.detect(frame)

        annotated = draw_pose_landmarks(frame, result)
        self.assertIsInstance(annotated, np.ndarray)
        self.assertEqual(annotated.shape, frame.shape)
        self.assertEqual(annotated.dtype, frame.dtype)

        # Ensure original frame was not mutated in place
        self.assertFalse(np.array_equal(frame, annotated))

        # Test image saving
        save_success = save_annotated_frame(OUTPUT_TEMP_PATH, annotated)
        self.assertTrue(save_success)
        self.assertTrue(os.path.isfile(OUTPUT_TEMP_PATH))
        self.assertGreater(os.path.getsize(OUTPUT_TEMP_PATH), 0)
        print("  -> PASS: Test 8: Visualizer rendered skeleton and saved output frame without errors.")

    def test_09_visualizer_on_no_person(self):
        """Verifies visualizer safely renders a frame where no person was detected."""
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        result = self.detector.detect(blank_frame)

        annotated = draw_pose_landmarks(blank_frame, result)
        self.assertIsInstance(annotated, np.ndarray)
        self.assertEqual(annotated.shape, blank_frame.shape)
        print("  -> PASS: Test 9: Visualizer handled no-person frame safely.")


def run_suite():
    """Runs the test suite directly with a clean runner."""
    print("=" * 70)
    print("PHASE 2.2 — POSE DETECTOR & VISUALIZER AUTOMATED TESTS")
    print("=" * 70)
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPoseDetector)
    runner = unittest.TextTestRunner(verbosity=1)
    result = runner.run(suite)
    print("=" * 70)
    if result.wasSuccessful():
        print("[ALL 9 PHASE 2.2 AUTOMATED TESTS PASSED SUCCESSFULLY]")
        return 0
    else:
        print(f"[FAILURES DETECTED: {len(result.failures)}, ERRORS: {len(result.errors)}]")
        return 1


if __name__ == "__main__":
    sys.exit(run_suite())
