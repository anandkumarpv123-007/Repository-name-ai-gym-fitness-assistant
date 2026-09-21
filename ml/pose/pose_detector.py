"""
AI Gym & Fitness Assistant — Pose Detector Component
Phase 2.2 — OpenCV + MediaPipe Pose Pipeline

This module encapsulates MediaPipe Pose Landmark Detection into a reusable,
production-grade detector component. It converts OpenCV BGR frames, runs
detection using MediaPipe Tasks PoseLandmarker, and returns structured
pose landmark objects.
"""

from dataclasses import dataclass, field
import os
from typing import Dict, List, Optional, Union
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python.vision import (
    PoseLandmark,
    PoseLandmarker,
    PoseLandmarkerOptions,
    RunningMode,
)
import numpy as np

# Official MediaPipe Pose Landmarker Lite model URL (Float16)
DEFAULT_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/latest/pose_landmarker_lite.task"
)


@dataclass
class PoseLandmarkPoint:
    """
    Represents a single detected anatomical landmark on the human body.
    
    Attributes:
        id: Landmark index (0 to 32, following MediaPipe Pose topology).
        name: Name of the landmark (e.g. 'NOSE', 'LEFT_SHOULDER', 'RIGHT_KNEE').
        x: Normalized horizontal coordinate in [0.0, 1.0], relative to image width.
        y: Normalized vertical coordinate in [0.0, 1.0], relative to image height.
        z: Normalized depth coordinate relative to mid-hip point.
        visibility: Confidence score [0.0, 1.0] that the landmark is not occluded.
        presence: Confidence score [0.0, 1.0] that the landmark exists in the frame.
        pixel_x: Absolute pixel x-coordinate within the image dimensions.
        pixel_y: Absolute pixel y-coordinate within the image dimensions.
    """
    id: int
    name: str
    x: float
    y: float
    z: float
    visibility: float
    presence: float
    pixel_x: int
    pixel_y: int

    def to_dict(self) -> dict:
        """Returns landmark attributes as a standard dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "visibility": self.visibility,
            "presence": self.presence,
            "pixel_x": self.pixel_x,
            "pixel_y": self.pixel_y,
        }


@dataclass
class PoseDetectionResult:
    """
    Structured outcome of a pose detection pass on a single video or image frame.
    
    Attributes:
        detected: True if at least one human pose was detected, False otherwise.
        landmarks: Ordered list of 33 PoseLandmarkPoint objects (if detected).
        landmark_dict: Dictionary mapping landmark name (e.g. 'LEFT_ELBOW') to point.
        image_width: Width of the analyzed image frame in pixels.
        image_height: Height of the analyzed image frame in pixels.
    """
    detected: bool
    landmarks: List[PoseLandmarkPoint] = field(default_factory=list)
    landmark_dict: Dict[str, PoseLandmarkPoint] = field(default_factory=dict)
    image_width: int = 0
    image_height: int = 0

    def get(self, identifier: Union[str, int]) -> Optional[PoseLandmarkPoint]:
        """
        Retrieve a landmark by either its name or integer ID.
        
        Examples:
            result.get('LEFT_ELBOW')
            result.get(13)
        """
        if isinstance(identifier, int):
            if 0 <= identifier < len(self.landmarks):
                return self.landmarks[identifier]
            return None
        return self.landmark_dict.get(str(identifier).upper())

    def to_dict(self) -> dict:
        """Serializes the result to a dictionary for logging or API payload."""
        return {
            "detected": self.detected,
            "landmark_count": len(self.landmarks),
            "image_width": self.image_width,
            "image_height": self.image_height,
            "landmarks": [lm.to_dict() for lm in self.landmarks],
        }


class PoseDetector:
    """
    Encapsulates MediaPipe Pose Landmark Detection for AI Gym.
    
    Accepts OpenCV BGR frames, handles image format conversions, performs
    inference using the MediaPipe Tasks Vision API, and outputs structured
    PoseDetectionResult instances.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        min_detection_confidence: float = 0.5,
        min_presence_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
    ) -> None:
        """
        Initializes the PoseDetector.
        
        Args:
            model_path: Filepath to the MediaPipe .task model asset. If None,
                        the default pose_landmarker_lite.task is resolved or downloaded.
            min_detection_confidence: Minimum confidence score for pose detection.
            min_presence_confidence: Minimum confidence score for landmark presence.
            min_tracking_confidence: Minimum confidence score for landmark tracking.
        """
        self.model_path = self._resolve_model_path(model_path)
        self.min_detection_confidence = min_detection_confidence
        self.min_presence_confidence = min_presence_confidence
        self.min_tracking_confidence = min_tracking_confidence

        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=self.model_path),
            running_mode=RunningMode.IMAGE,
            min_pose_detection_confidence=self.min_detection_confidence,
            min_pose_presence_confidence=self.min_presence_confidence,
            min_tracking_confidence=self.min_tracking_confidence,
        )
        self._landmarker = PoseLandmarker.create_from_options(options)

    @staticmethod
    def _resolve_model_path(model_path: Optional[str]) -> str:
        """Resolves or downloads the pose landmarker model asset."""
        if model_path and os.path.isfile(model_path):
            return model_path

        # Default model location inside ml/models/
        current_dir = os.path.dirname(os.path.abspath(__file__))
        default_dir = os.path.abspath(os.path.join(current_dir, "..", "models"))
        os.makedirs(default_dir, exist_ok=True)
        default_path = os.path.join(default_dir, "pose_landmarker_lite.task")

        if not os.path.isfile(default_path):
            print(f"[INFO] Pose landmarker model not found. Downloading to: {default_path}...")
            urllib.request.urlretrieve(DEFAULT_MODEL_URL, default_path)
            print("[INFO] Model download complete.")

        return default_path

    def detect(self, frame: Optional[np.ndarray]) -> PoseDetectionResult:
        """
        Runs pose detection on an input OpenCV BGR frame.
        
        Args:
            frame: Numpy ndarray in BGR format (as returned by cv2.imread or cv2.VideoCapture).
                   Can be None or an empty array.
                   
        Returns:
            PoseDetectionResult containing detected status and 33 structured landmarks.
        """
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return PoseDetectionResult(detected=False)

        height, width = frame.shape[:2]

        # Convert OpenCV BGR to RGB format required by MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Run inference
        inference_result = self._landmarker.detect(mp_image)

        # Handle frames where no person is detected
        if not inference_result.pose_landmarks or len(inference_result.pose_landmarks) == 0:
            return PoseDetectionResult(
                detected=False,
                landmarks=[],
                landmark_dict={},
                image_width=width,
                image_height=height,
            )

        # Extract primary person's landmarks (33 points)
        raw_landmarks = inference_result.pose_landmarks[0]
        parsed_landmarks: List[PoseLandmarkPoint] = []
        landmark_dict: Dict[str, PoseLandmarkPoint] = {}

        for idx, lm in enumerate(raw_landmarks):
            # Resolve landmark name using MediaPipe PoseLandmark enum
            try:
                landmark_name = PoseLandmark(idx).name
            except (ValueError, IndexError):
                landmark_name = f"LANDMARK_{idx}"

            # Compute pixel coordinates bounded by image dimensions
            px = int(np.clip(lm.x * width, 0, width - 1))
            py = int(np.clip(lm.y * height, 0, height - 1))

            point = PoseLandmarkPoint(
                id=idx,
                name=landmark_name,
                x=float(lm.x),
                y=float(lm.y),
                z=float(lm.z),
                visibility=float(lm.visibility) if lm.visibility is not None else 1.0,
                presence=float(lm.presence) if lm.presence is not None else 1.0,
                pixel_x=px,
                pixel_y=py,
            )
            parsed_landmarks.append(point)
            landmark_dict[landmark_name] = point

        return PoseDetectionResult(
            detected=True,
            landmarks=parsed_landmarks,
            landmark_dict=landmark_dict,
            image_width=width,
            image_height=height,
        )

    def close(self) -> None:
        """Releases native resources allocated by the underlying MediaPipe landmarker."""
        if hasattr(self, "_landmarker") and self._landmarker is not None:
            self._landmarker.close()
            self._landmarker = None

    def __enter__(self) -> "PoseDetector":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
