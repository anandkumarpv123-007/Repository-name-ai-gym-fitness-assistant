"""
AI Gym & Fitness Assistant — Pose Visualizer Component
Phase 2.4 — Squat Form Analysis + Real-Time Feedback

Renders pose landmarks, skeletal connections, and biomechanical movement telemetry
(knee angle, state machine phase, rep count, and real-time form feedback) onto OpenCV BGR frames.
"""

from typing import Optional, Tuple
import cv2
from mediapipe.tasks.python.vision import PoseLandmarksConnections
import numpy as np

from .pose_detector import PoseDetectionResult


# Aesthetic BGR color palette
COLOR_LANDMARK_FILL = (0, 255, 128)      # Vibrant neon green
COLOR_LANDMARK_BORDER = (0, 50, 0)       # Dark green border
COLOR_CONNECTION = (0, 200, 255)         # Warm amber/gold
COLOR_TEXT_BG = (24, 24, 24)             # Dark slate container
COLOR_DETECTED_TEXT = (0, 255, 0)        # Green
COLOR_NOT_DETECTED_TEXT = (0, 0, 255)    # Red
COLOR_METRIC_LABEL = (180, 180, 180)     # Soft gray
COLOR_METRIC_VALUE = (255, 255, 255)     # Bright white
COLOR_STATE_UP = (0, 255, 128)           # Neon green for standing
COLOR_STATE_DESCENDING = (0, 215, 255)   # Gold/yellow for descending
COLOR_STATE_BOTTOM = (0, 100, 255)       # Orange for bottom depth
COLOR_STATE_ASCENDING = (255, 191, 0)    # Deep sky blue for ascending
COLOR_FORM_GOOD = (0, 255, 128)          # Green for good form
COLOR_FORM_WARN = (0, 140, 255)          # Orange/amber for form violation


def draw_pose_landmarks(
    frame: np.ndarray,
    result: PoseDetectionResult,
    draw_connections: bool = True,
    min_visibility: float = 0.3,
    point_radius: int = 5,
    line_thickness: int = 2,
    show_status_badge: bool = True,
    movement_result: Optional[object] = None,
    form_result: Optional[object] = None,
) -> np.ndarray:
    """
    Renders detected pose landmarks, skeletal connections, movement and form telemetry.
    
    Args:
        frame: The OpenCV BGR image array.
        result: The PoseDetectionResult object from PoseDetector.
        draw_connections: Whether to draw skeletal lines between anatomical joints.
        min_visibility: Visibility threshold below which landmarks are not rendered.
        point_radius: Radius of the landmark circles in pixels.
        line_thickness: Thickness of skeleton connection lines in pixels.
        show_status_badge: Whether to display a status badge in the top-left corner.
        movement_result: Optional SquatMovementResult providing angle, state, and reps.
        form_result: Optional FormAnalysisResult providing form status and coaching cues.
        
    Returns:
        A new annotated np.ndarray frame.
    """
    if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
        return frame

    annotated_frame = frame.copy()
    height, width = annotated_frame.shape[:2]

    # Draw standard status badge if requested and no telemetry is shown
    if show_status_badge and movement_result is None and form_result is None:
        _draw_status_badge(annotated_frame, result.detected, len(result.landmarks))

    # 1. Draw skeletal connections if person is detected
    if result.detected and result.landmarks:
        if draw_connections:
            for connection in PoseLandmarksConnections.POSE_LANDMARKS:
                start_point = result.get(connection.start)
                end_point = result.get(connection.end)

                if start_point is None or end_point is None:
                    continue

                if (
                    start_point.visibility < min_visibility
                    or end_point.visibility < min_visibility
                ):
                    continue

                pt1 = (start_point.pixel_x, start_point.pixel_y)
                pt2 = (end_point.pixel_x, end_point.pixel_y)

                cv2.line(
                    annotated_frame,
                    pt1,
                    pt2,
                    color=COLOR_CONNECTION,
                    thickness=line_thickness,
                    lineType=cv2.LINE_AA,
                )

        # 2. Draw anatomical landmark keypoints
        for lm in result.landmarks:
            if lm.visibility < min_visibility:
                continue

            center = (lm.pixel_x, lm.pixel_y)

            cv2.circle(
                annotated_frame,
                center,
                radius=point_radius + 1,
                color=COLOR_LANDMARK_BORDER,
                thickness=-1,
                lineType=cv2.LINE_AA,
            )
            cv2.circle(
                annotated_frame,
                center,
                radius=point_radius,
                color=COLOR_LANDMARK_FILL,
                thickness=-1,
                lineType=cv2.LINE_AA,
            )

    # 3. Draw movement and form telemetry HUD
    if movement_result is not None or form_result is not None:
        draw_movement_telemetry(annotated_frame, movement_result, form_result)

    return annotated_frame


def draw_movement_telemetry(
    frame: np.ndarray,
    movement_result: Optional[object] = None,
    form_result: Optional[object] = None,
) -> None:
    """
    Renders a compact, high-readability HUD showing:
        - Knee angle: XX.X°
        - State: UP / DESCENDING / BOTTOM / ASCENDING
        - Reps: N
        - Form Status & Real-Time Coaching Cue (if form_result is available)
    """
    if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
        return

    # Extract movement telemetry
    angle_val = None
    state_str = "UP"
    reps_count = 0
    if movement_result is not None:
        angle_val = getattr(movement_result, "smoothed_angle", None)
        if angle_val is None:
            angle_val = getattr(movement_result, "current_angle", None)
        state_obj = getattr(movement_result, "state", "UP")
        state_str = state_obj.value if hasattr(state_obj, "value") else str(state_obj)
        reps_count = getattr(movement_result, "reps", 0)

    angle_str = f"{angle_val:.1f}°" if angle_val is not None else "--"

    # Color for state indicator
    if state_str == "UP":
        state_color = COLOR_STATE_UP
    elif state_str == "DESCENDING":
        state_color = COLOR_STATE_DESCENDING
    elif state_str == "BOTTOM":
        state_color = COLOR_STATE_BOTTOM
    elif state_str == "ASCENDING":
        state_color = COLOR_STATE_ASCENDING
    else:
        state_color = COLOR_METRIC_VALUE

    # Form analysis extraction
    form_str = "CHECKING..."
    form_color = COLOR_METRIC_LABEL
    feedback_str = ""

    if form_result is not None:
        violations = getattr(form_result, "violations", [])
        feedback_list = getattr(form_result, "feedback", [])
        is_valid = getattr(form_result, "valid", True)

        if not is_valid:
            form_str = "OCCLUDED"
            form_color = (0, 0, 255)
            feedback_str = "Landmarks occluded"
        elif violations:
            form_str = violations[0].replace("_", " ")
            form_color = COLOR_FORM_WARN
            feedback_str = feedback_list[0] if feedback_list else "Adjust posture"
        else:
            form_str = "GOOD"
            form_color = COLOR_FORM_GOOD
            feedback_str = feedback_list[0] if feedback_list else "Good form!"

    # Card layout coordinates
    x1, y1 = 16, 16
    w = 280
    h = 160 if form_result is not None else 110
    x2, y2 = x1 + w, y1 + h

    # Semi-transparent dark container card
    overlay = frame.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), COLOR_TEXT_BG, -1)
    cv2.rectangle(overlay, (x1, y1), (x2, y2), (60, 60, 60), 1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

    font = cv2.FONT_HERSHEY_SIMPLEX

    # Line 1: Knee Angle
    cv2.putText(frame, "Knee Angle:", (x1 + 14, y1 + 28), font, 0.52, COLOR_METRIC_LABEL, 1, cv2.LINE_AA)
    cv2.putText(frame, angle_str, (x1 + 130, y1 + 28), font, 0.62, (0, 255, 255), 2, cv2.LINE_AA)

    # Line 2: State
    cv2.putText(frame, "State:", (x1 + 14, y1 + 58), font, 0.52, COLOR_METRIC_LABEL, 1, cv2.LINE_AA)
    cv2.putText(frame, state_str, (x1 + 80, y1 + 58), font, 0.62, state_color, 2, cv2.LINE_AA)

    # Line 3: Reps Counter
    cv2.putText(frame, "Reps:", (x1 + 14, y1 + 88), font, 0.52, COLOR_METRIC_LABEL, 1, cv2.LINE_AA)
    cv2.putText(frame, str(reps_count), (x1 + 80, y1 + 88), font, 0.75, (0, 255, 0), 2, cv2.LINE_AA)

    # Line 4 & 5: Form Status & Feedback Cue
    if form_result is not None:
        cv2.putText(frame, "Form:", (x1 + 14, y1 + 118), font, 0.52, COLOR_METRIC_LABEL, 1, cv2.LINE_AA)
        cv2.putText(frame, form_str[:16], (x1 + 80, y1 + 118), font, 0.58, form_color, 2, cv2.LINE_AA)

        # Cue text truncated to fit card
        cv2.putText(frame, f"> {feedback_str[:30]}", (x1 + 14, y1 + 145), font, 0.45, (220, 220, 220), 1, cv2.LINE_AA)


def _draw_status_badge(frame: np.ndarray, detected: bool, landmark_count: int) -> None:
    """Draws a clean status overlay badge at the top-left of the frame."""
    if detected:
        text = f"Pose: DETECTED ({landmark_count} points)"
        text_color = COLOR_DETECTED_TEXT
    else:
        text = "Pose: NO PERSON DETECTED"
        text_color = COLOR_NOT_DETECTED_TEXT

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    thickness = 2
    padding = 8

    (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    box_x1, box_y1 = 15, 15
    box_x2 = box_x1 + text_w + (padding * 2)
    box_y2 = box_y1 + text_h + (padding * 2)

    overlay = frame.copy()
    cv2.rectangle(overlay, (box_x1, box_y1), (box_x2, box_y2), COLOR_TEXT_BG, -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

    text_origin = (box_x1 + padding, box_y1 + text_h + padding - 2)
    cv2.putText(
        frame,
        text,
        text_origin,
        font,
        font_scale,
        text_color,
        thickness,
        lineType=cv2.LINE_AA,
    )


def save_annotated_frame(output_path: str, frame: np.ndarray) -> bool:
    """Saves the rendered frame to an image file."""
    if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
        return False
    return cv2.imwrite(output_path, frame)
