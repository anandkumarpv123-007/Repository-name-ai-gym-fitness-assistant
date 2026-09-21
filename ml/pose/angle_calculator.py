"""
AI Gym & Fitness Assistant — Joint Angle Calculation Utility
Phase 2.3 — Joint Angles + Squat State Machine + Rep Counting

Calculates 2D planar joint angles between three anatomical landmarks:
    Vector 1: A -> B
    Vector 2: C -> B
    Angle at vertex B in degrees: [0.0, 180.0]

Includes landmark visibility and presence validation, zero-length vector safety,
and trigonometric domain boundary protection to strictly eliminate NaN values.
"""

from typing import Optional, Sequence, Tuple, Union
import numpy as np

from .pose_detector import PoseLandmarkPoint


def calculate_angle_2d(
    pt_a: Union[Sequence[float], Tuple[float, float], np.ndarray],
    pt_b: Union[Sequence[float], Tuple[float, float], np.ndarray],
    pt_c: Union[Sequence[float], Tuple[float, float], np.ndarray],
    eps: float = 1e-7,
) -> Optional[float]:
    """
    Calculates the internal angle at vertex B formed by line segments AB and CB.
    
    Args:
        pt_a: 2D coordinates (x, y) of first point A.
        pt_b: 2D coordinates (x, y) of vertex point B (the joint center).
        pt_c: 2D coordinates (x, y) of second point C.
        eps: Epsilon threshold for zero-length vector detection.
        
    Returns:
        Angle in degrees in range [0.0, 180.0], or None if vectors are degenerate.
    """
    try:
        ax, ay = float(pt_a[0]), float(pt_a[1])
        bx, by = float(pt_b[0]), float(pt_b[1])
        cx, cy = float(pt_c[0]), float(pt_c[1])
    except (IndexError, TypeError, ValueError):
        return None

    # Vectors from joint vertex B to endpoints A and C
    v1_x = ax - bx
    v1_y = ay - by
    v2_x = cx - bx
    v2_y = cy - by

    # Euclidean vector lengths (magnitudes)
    mag1 = np.sqrt(v1_x * v1_x + v1_y * v1_y)
    mag2 = np.sqrt(v2_x * v2_x + v2_y * v2_y)

    # Degenerate zero-length vector check: prevents division by zero
    if mag1 < eps or mag2 < eps:
        return None

    # Dot product: v1 · v2
    dot = v1_x * v2_x + v1_y * v2_y

    # Cosine value: (v1 · v2) / (|v1| * |v2|)
    cosine = dot / (mag1 * mag2)

    # Floating point clamp strictly within [-1.0, 1.0] to prevent arccos NaN
    clamped_cosine = float(np.clip(cosine, -1.0, 1.0))

    # Angle in radians and convert to degrees
    radians = np.arccos(clamped_cosine)
    degrees = float(np.degrees(radians))

    if np.isnan(degrees):
        return None

    return degrees


def calculate_landmark_angle(
    point_a: Optional[PoseLandmarkPoint],
    point_b: Optional[PoseLandmarkPoint],
    point_c: Optional[PoseLandmarkPoint],
    min_visibility: float = 0.5,
    use_pixel_coords: bool = True,
) -> Optional[float]:
    """
    Validates landmark visibility and calculates the joint angle at landmark B.
    
    Args:
        point_a: Landmark A (e.g. HIP).
        point_b: Landmark B vertex (e.g. KNEE).
        point_c: Landmark C (e.g. ANKLE).
        min_visibility: Minimum acceptable visibility confidence score [0.0, 1.0].
        use_pixel_coords: If True, uses (pixel_x, pixel_y) preserving true aspect ratio.
                          If False, uses normalized (x, y).
                          
    Returns:
        Angle in degrees [0.0, 180.0], or None if any landmark is missing or occluded.
    """
    if point_a is None or point_b is None or point_c is None:
        return None

    # Visibility & Presence Validation
    for pt in (point_a, point_b, point_c):
        if pt.visibility < min_visibility or pt.presence < min_visibility:
            return None

    if use_pixel_coords:
        pt_a = (point_a.pixel_x, point_a.pixel_y)
        pt_b = (point_b.pixel_x, point_b.pixel_y)
        pt_c = (point_c.pixel_x, point_c.pixel_y)
    else:
        pt_a = (point_a.x, point_a.y)
        pt_b = (point_b.x, point_b.y)
        pt_c = (point_c.x, point_c.y)

    return calculate_angle_2d(pt_a, pt_b, pt_c)
