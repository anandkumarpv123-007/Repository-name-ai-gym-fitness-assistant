"""
AI Gym & Fitness Assistant — Squat State Machine & Rep Counter
Phase 2.3 — Joint Angles + Squat State Machine + Rep Counting

Implements a deterministic finite state machine (FSM) for squat tracking:
    States: UP -> DESCENDING -> BOTTOM -> ASCENDING -> UP (Rep increment)

Guarantees full cycle execution, eliminates spurious repetitions from static pauses
or noisy joint boundaries, and returns structured movement telemetry per frame.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union

from .angle_calculator import calculate_landmark_angle
from .pose_detector import PoseDetectionResult, PoseLandmarkPoint
from .smoothing import MovingAverageFilter


class SquatState(str, Enum):
    """Enumeration of possible squat biomechanical phases."""
    UP = "UP"
    DESCENDING = "DESCENDING"
    BOTTOM = "BOTTOM"
    ASCENDING = "ASCENDING"


@dataclass
class SquatMovementResult:
    """
    Structured outcome of a squat analysis evaluation on a single frame.
    
    Attributes:
        current_angle: Raw knee joint angle in degrees, or None if landmarks occluded.
        smoothed_angle: Moving-average filtered knee angle in degrees, or None.
        state: Current FSM phase (UP, DESCENDING, BOTTOM, ASCENDING).
        reps: Total completed repetition count.
        landmark_valid: True if required landmarks met the visibility confidence threshold.
        rep_completed: True only on the exact transition frame when a rep completes.
        feedback_message: Human-readable status or guidance string.
    """
    current_angle: Optional[float]
    smoothed_angle: Optional[float]
    state: SquatState
    reps: int
    landmark_valid: bool
    rep_completed: bool = False
    feedback_message: str = ""

    def to_dict(self) -> dict:
        """Serializes the movement telemetry to a standard dictionary."""
        return {
            "current_angle": round(self.current_angle, 2) if self.current_angle is not None else None,
            "smoothed_angle": round(self.smoothed_angle, 2) if self.smoothed_angle is not None else None,
            "state": self.state.value,
            "reps": self.reps,
            "landmark_valid": self.landmark_valid,
            "rep_completed": self.rep_completed,
            "feedback_message": self.feedback_message,
        }


class SquatStateMachine:
    """
    Finite State Machine tracking squat repetitions based on knee flexion/extension.
    
    State Cycle:
        1. UP: Standing tall (angle >= up_threshold, e.g. ~160 deg).
        2. DESCENDING: Hip and knee flex downward (angle drops below up_threshold - hysteresis).
        3. BOTTOM: Deep squat inflection zone (angle <= bottom_threshold, e.g. ~100 deg).
        4. ASCENDING: Driving upward from hole (angle rises above bottom_threshold + hysteresis).
        5. UP: Return to full lockout -> Reps increment by 1.
    """

    def __init__(
        self,
        up_threshold: float = 160.0,
        bottom_threshold: float = 100.0,
        hysteresis: float = 5.0,
        min_visibility: float = 0.5,
        smoothing_window: int = 5,
        side: str = "LEFT",
    ) -> None:
        """
        Initializes the Squat State Machine.
        
        Args:
            up_threshold: Knee angle considered full extension/standing (default 160.0 deg).
            bottom_threshold: Knee angle considered valid squat depth (default 100.0 deg).
            hysteresis: Buffer angle to prevent transition chatter around boundaries (default 5.0 deg).
            min_visibility: Minimum landmark confidence required for calculation.
            smoothing_window: Sliding window size for knee angle smoothing filter.
            side: Tracking anatomical side ('LEFT', 'RIGHT', or 'AUTO').
        """
        if bottom_threshold >= up_threshold:
            raise ValueError(f"bottom_threshold ({bottom_threshold}) must be < up_threshold ({up_threshold})")

        self.up_threshold = up_threshold
        self.bottom_threshold = bottom_threshold
        self.hysteresis = hysteresis
        self.min_visibility = min_visibility
        self.side = side.upper()

        self._filter = MovingAverageFilter(window_size=smoothing_window)
        self._state = SquatState.UP
        self._reps = 0
        self._hit_bottom = False

    @property
    def current_state(self) -> SquatState:
        """Current FSM state."""
        return self._state

    @property
    def rep_count(self) -> int:
        """Total completed repetitions."""
        return self._reps

    def reset(self) -> None:
        """Resets the state machine counters, FSM state, and smoothing filter."""
        self._state = SquatState.UP
        self._reps = 0
        self._hit_bottom = False
        self._filter.reset()

    def process_angle(self, raw_angle: Optional[float]) -> SquatMovementResult:
        """
        Processes a raw knee angle value through the smoothing filter and state machine.
        Useful for unit testing with deterministic synthetic angle sequences.
        
        Args:
            raw_angle: Measured knee angle in degrees, or None if signal was invalid.
            
        Returns:
            SquatMovementResult detailing state, smoothed angle, and rep status.
        """
        if raw_angle is None:
            return SquatMovementResult(
                current_angle=None,
                smoothed_angle=self._filter.current_value,
                state=self._state,
                reps=self._reps,
                landmark_valid=False,
                rep_completed=False,
                feedback_message="Knee landmarks occluded or out of frame.",
            )

        smoothed = self._filter.update(raw_angle)
        rep_completed = False
        feedback = ""

        # --- Deterministic State Machine Transitions ---
        if self._state == SquatState.UP:
            # Transition to DESCENDING when knee flexes past standing threshold
            if smoothed < (self.up_threshold - self.hysteresis):
                self._state = SquatState.DESCENDING
                self._hit_bottom = False
                feedback = "Squatting down..."
            else:
                feedback = "Standing position ready."

        elif self._state == SquatState.DESCENDING:
            # Reached valid squat depth
            if smoothed <= self.bottom_threshold:
                self._state = SquatState.BOTTOM
                self._hit_bottom = True
                feedback = "Good depth reached! Drive up."
            # Incomplete squat abort: user rises back up without reaching bottom depth
            elif smoothed >= self.up_threshold:
                self._state = SquatState.UP
                self._hit_bottom = False
                feedback = "Squat not deep enough. Rep uncounted."
            else:
                feedback = "Lowering..."

        elif self._state == SquatState.BOTTOM:
            # Transition to ASCENDING when user begins standing up
            if smoothed > (self.bottom_threshold + self.hysteresis):
                self._state = SquatState.ASCENDING
                feedback = "Ascending upward..."
            else:
                # Staying in the bottom hole (no repeated reps counted!)
                feedback = "Holding at bottom."

        elif self._state == SquatState.ASCENDING:
            # Returned to full extension -> complete repetition!
            if smoothed >= self.up_threshold:
                self._state = SquatState.UP
                if self._hit_bottom:
                    self._reps += 1
                    rep_completed = True
                    feedback = f"Rep {self._reps} completed!"
                self._hit_bottom = False
            # If user descends again without standing up fully
            elif smoothed <= self.bottom_threshold:
                self._state = SquatState.BOTTOM
                feedback = "Dropped back down before standing."
            else:
                feedback = "Pushing up..."

        return SquatMovementResult(
            current_angle=raw_angle,
            smoothed_angle=smoothed,
            state=self._state,
            reps=self._reps,
            landmark_valid=True,
            rep_completed=rep_completed,
            feedback_message=feedback,
        )

    def process_frame_landmarks(self, pose_result: PoseDetectionResult) -> SquatMovementResult:
        """
        Extracts knee angle from a PoseDetectionResult and updates movement state.
        
        Args:
            pose_result: Structured result from PoseDetector.
            
        Returns:
            SquatMovementResult.
        """
        if not pose_result.detected or not pose_result.landmarks:
            return SquatMovementResult(
                current_angle=None,
                smoothed_angle=self._filter.current_value,
                state=self._state,
                reps=self._reps,
                landmark_valid=False,
                rep_completed=False,
                feedback_message="No person detected in camera frame.",
            )

        # Determine side (LEFT, RIGHT, or AUTO)
        if self.side == "AUTO":
            # Pick side with highest cumulative visibility
            left_vis = sum(
                (pose_result.get(k).visibility if pose_result.get(k) else 0.0)
                for k in ("LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE")
            )
            right_vis = sum(
                (pose_result.get(k).visibility if pose_result.get(k) else 0.0)
                for k in ("RIGHT_HIP", "RIGHT_KNEE", "RIGHT_ANKLE")
            )
            selected_prefix = "LEFT" if left_vis >= right_vis else "RIGHT"
        else:
            selected_prefix = self.side

        hip = pose_result.get(f"{selected_prefix}_HIP")
        knee = pose_result.get(f"{selected_prefix}_KNEE")
        ankle = pose_result.get(f"{selected_prefix}_ANKLE")

        angle = calculate_landmark_angle(
            point_a=hip,
            point_b=knee,
            point_c=ankle,
            min_visibility=self.min_visibility,
            use_pixel_coords=True,
        )

        return self.process_angle(angle)
