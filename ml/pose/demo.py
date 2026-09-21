"""
AI Gym & Fitness Assistant — Pose Pipeline Demonstration Script
Phase 2.2 — OpenCV + MediaPipe Pose Pipeline

Runs an interactive or headless demonstration of the pose detector.
Supports webcam live feed (if hardware is available) with automatic graceful
fallback to sample image fixtures, video files, or custom static images.

Usage:
    # Run with automatic webcam detection (falls back to sample fixture if no webcam):
    python demo.py

    # Run on sample image fixture:
    python demo.py --source fixture --save demo_output.png

    # Run on a custom image:
    python demo.py --source image --path /path/to/photo.jpg --save output.png

    # Run on a custom video:
    python demo.py --source video --path /path/to/workout.mp4

    # Run headless (no GUI window popup, writes output to disk):
    python demo.py --headless --save output.png
"""

import argparse
import os
import sys
import time

import cv2

# Ensure project root is in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml.pose.pose_detector import PoseDetector
from ml.pose.squat_state_machine import SquatStateMachine
from ml.pose.form_analyzer import SquatFormAnalyzer
from ml.pose.visualizer import draw_pose_landmarks, save_annotated_frame

DEFAULT_FIXTURE_PATH = os.path.join(PROJECT_ROOT, "ml", "fixtures", "sample_person.png")
DEFAULT_OUTPUT_PATH = os.path.join(PROJECT_ROOT, "ml", "fixtures", "demo_output.png")


def run_image_demo(
    detector: PoseDetector,
    image_path: str,
    save_path: str,
    headless: bool = False,
) -> None:
    """Runs pose detection and visualization on a single static image."""
    print(f"\n[DEMO] Loading image from: {image_path}")
    if not os.path.isfile(image_path):
        print(f"[ERROR] Image file does not exist: {image_path}")
        return

    frame = cv2.imread(image_path)
    if frame is None:
        print(f"[ERROR] Failed to load image using OpenCV: {image_path}")
        return

    h, w = frame.shape[:2]
    print(f"[DEMO] Image dimensions: {w}x{h} px")

    start_time = time.perf_counter()
    result = detector.detect(frame)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    print(f"[DEMO] Inference completed in {elapsed_ms:.1f} ms")
    print(f"[DEMO] Person detected: {result.detected}")

    if result.detected:
        print(f"[DEMO] Detected landmarks: {len(result.landmarks)} points")
        print("\n--- Key Landmarks Sample ---")
        sample_keys = [
            "NOSE",
            "LEFT_SHOULDER",
            "RIGHT_SHOULDER",
            "LEFT_ELBOW",
            "RIGHT_ELBOW",
            "LEFT_WRIST",
            "RIGHT_WRIST",
            "LEFT_HIP",
            "RIGHT_HIP",
            "LEFT_KNEE",
            "RIGHT_KNEE",
            "LEFT_ANKLE",
            "RIGHT_ANKLE",
        ]
        for key in sample_keys:
            point = result.get(key)
            if point:
                print(
                    f"  {point.name:<15} (id={point.id:>2}): "
                    f"px=({point.pixel_x:>4}, {point.pixel_y:>4}) "
                    f"norm=({point.x:.3f}, {point.y:.3f}, {point.z:+.3f}) "
                    f"vis={point.visibility:.2f}"
                )
    else:
        print("[DEMO] No person was detected in this frame.")

    # Evaluate Squat Telemetry & Form Analysis
    fsm = SquatStateMachine(side="LEFT")
    analyzer = SquatFormAnalyzer(side="LEFT")
    movement_res = fsm.process_frame_landmarks(result)
    form_res = analyzer.analyze_frame(result, movement_res)

    if movement_res.landmark_valid and movement_res.current_angle is not None:
        print(f"\n[DEMO] Squat Telemetry: Knee Angle = {movement_res.current_angle:.1f}°, "
              f"State = {movement_res.state.value}, Reps = {movement_res.reps}")
        print(f"[DEMO] Form Analysis: Torso = {form_res.torso_status} ({form_res.torso_angle:.1f}°), "
              f"Depth = {form_res.depth_status}, Feedback = {form_res.feedback}")
    else:
        print("\n[DEMO] Squat Telemetry: Key knee landmarks occluded or not detected.")

    # Annotate frame with pose skeleton and movement telemetry HUD
    annotated = draw_pose_landmarks(frame, result, movement_result=movement_res, form_result=form_res)

    # Save output
    if save_path:
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        saved = save_annotated_frame(save_path, annotated)
        if saved:
            print(f"[DEMO] Successfully saved annotated frame to: {save_path}")
        else:
            print(f"[ERROR] Failed to save frame to: {save_path}")

    # Display GUI window if not headless
    if not headless:
        try:
            cv2.imshow("AI Gym — Pose Detection Demo (Press any key to close)", annotated)
            print("[DEMO] Displaying annotated image window. Press any key to close...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        except cv2.error:
            print("[INFO] Headless or display-unavailable environment. GUI display skipped.")


def run_webcam_demo(
    detector: PoseDetector,
    device_index: int = 0,
    save_path: str = None,
    headless: bool = False,
) -> None:
    """
    Runs real-time pose detection from a webcam stream.
    Falls back gracefully to test image fixture if webcam is unavailable.
    """
    print(f"\n[DEMO] Attempting to connect to webcam device index {device_index}...")
    cap = cv2.VideoCapture(device_index)

    if not cap.isOpened():
        print(f"[INFO] Webcam device {device_index} is unavailable (no camera detected or access denied).")
        print(f"[INFO] Falling back gracefully to deterministic fixture image: {DEFAULT_FIXTURE_PATH}")
        cap.release()
        run_image_demo(
            detector,
            image_path=DEFAULT_FIXTURE_PATH,
            save_path=save_path or DEFAULT_OUTPUT_PATH,
            headless=headless,
        )
        return

    print("[DEMO] Webcam opened successfully. Press 'q' or ESC in the preview window to exit.")
    frame_count = 0
    start_total = time.perf_counter()
    fsm = SquatStateMachine(side="LEFT")
    analyzer = SquatFormAnalyzer(side="LEFT")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[WARNING] Failed to grab frame from webcam. Exiting loop.")
                break

            frame_count += 1
            t0 = time.perf_counter()
            result = detector.detect(frame)
            fps = 1.0 / max(time.perf_counter() - t0, 0.001)

            # Evaluate movement & form telemetry
            movement_res = fsm.process_frame_landmarks(result)
            form_res = analyzer.analyze_frame(result, movement_res)

            if movement_res.rep_completed:
                print(f"[DEMO] *** REP COMPLETED! Total Reps: {movement_res.reps} ***")
                if form_res.rep_summary:
                    print(f"       Summary: Depth={form_res.rep_summary.depth_status}, "
                          f"Torso={form_res.rep_summary.torso_status}, "
                          f"Knee={form_res.rep_summary.knee_alignment_status}, "
                          f"Passed={form_res.rep_summary.passed}")

            annotated = draw_pose_landmarks(frame, result, movement_result=movement_res, form_result=form_res)

            # Draw real-time FPS counter on frame
            cv2.putText(
                annotated,
                f"FPS: {fps:.1f}",
                (annotated.shape[1] - 120, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2,
                cv2.LINE_AA,
            )

            if not headless:
                cv2.imshow("AI Gym — Pose Pipeline Live (Press Q to exit)", annotated)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q") or key == 27:
                    print("[DEMO] User requested exit.")
                    break
            else:
                # In headless webcam test, process 10 frames and capture last frame
                if frame_count >= 10:
                    print("[DEMO] Headless webcam test processed 10 frames.")
                    if save_path:
                        save_annotated_frame(save_path, annotated)
                        print(f"[DEMO] Saved live snapshot to: {save_path}")
                    break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        elapsed = time.perf_counter() - start_total
        avg_fps = frame_count / max(elapsed, 0.001)
        print(f"[DEMO] Processed {frame_count} frames in {elapsed:.2f}s (Avg {avg_fps:.1f} FPS).")


def main():
    parser = argparse.ArgumentParser(description="AI Gym — Pose Detection Demonstration")
    parser.add_argument(
        "--source",
        choices=["webcam", "image", "video", "fixture"],
        default="webcam",
        help="Input source (default: webcam with automatic fixture fallback)",
    )
    parser.add_argument(
        "--path",
        type=str,
        default="",
        help="Filepath for image or video source",
    )
    parser.add_argument(
        "--device",
        type=int,
        default=0,
        help="Webcam device index (default: 0)",
    )
    parser.add_argument(
        "--save",
        type=str,
        default=DEFAULT_OUTPUT_PATH,
        help=f"Filepath to save annotated result (default: {DEFAULT_OUTPUT_PATH})",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without displaying GUI window (saves result to disk)",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("AI GYM & FITNESS ASSISTANT — POSE PIPELINE DEMO")
    print("Phase 2.2: OpenCV + MediaPipe Pose Landmark Acquisition")
    print("=" * 70)

    detector = PoseDetector()

    try:
        if args.source == "fixture":
            run_image_demo(
                detector,
                image_path=DEFAULT_FIXTURE_PATH,
                save_path=args.save,
                headless=args.headless,
            )
        elif args.source == "image":
            target_path = args.path if args.path else DEFAULT_FIXTURE_PATH
            run_image_demo(
                detector,
                image_path=target_path,
                save_path=args.save,
                headless=args.headless,
            )
        elif args.source == "webcam":
            run_webcam_demo(
                detector,
                device_index=args.device,
                save_path=args.save,
                headless=args.headless,
            )
        elif args.source == "video":
            if not args.path or not os.path.isfile(args.path):
                print(f"[ERROR] Video file not found: {args.path}")
            else:
                print(f"[DEMO] Video input support: {args.path}")
                # Process first frame of video as demo
                cap = cv2.VideoCapture(args.path)
                ret, frame = cap.read()
                cap.release()
                if ret:
                    result = detector.detect(frame)
                    annotated = draw_pose_landmarks(frame, result)
                    save_annotated_frame(args.save, annotated)
                    print(f"[DEMO] Saved first frame annotated output to {args.save}")
                else:
                    print("[ERROR] Could not read video frame.")
    finally:
        detector.close()
        print("[DEMO] Demo finished cleanly.")


if __name__ == "__main__":
    main()
