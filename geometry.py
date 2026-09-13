"""
Geometric and mathematical utilities for Useless 3.0 Posture Glass.
Handles vector math, angle calculations with wraparound prevention, and normalization.
"""
import math
from typing import Tuple, Optional
import numpy as np

def wrap_angle_90(angle_deg: float) -> float:
    """
    Wraps an undirected line angle to [-90, 90] degrees relative to horizontal/axis.
    Handles wraparound: e.g. 177° behaves like -3°, and -177° behaves like +3°.
    """
    return (angle_deg + 90.0) % 180.0 - 90.0

def wrap_angle_180(angle_deg: float) -> float:
    """Wraps an angle in degrees into [-180, 180)."""
    return (angle_deg + 180.0) % 360.0 - 180.0

def angular_distance(a1_deg: float, a2_deg: float) -> float:
    """
    Computes shortest signed angular difference (a1 - a2) in degrees,
    handling 179 deg vs -179 deg wraparound seamlessly.
    Result is always in [-180, 180].
    """
    diff = (a1_deg - a2_deg) % 360.0
    if diff > 180.0:
        diff -= 360.0
    return diff

def abs_angular_distance(a1_deg: float, a2_deg: float) -> float:
    """Returns absolute shortest angular distance in [0, 180]."""
    return abs(angular_distance(a1_deg, a2_deg))

def distance_2d(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """2D Euclidean distance."""
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def distance_3d(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
    """3D Euclidean distance."""
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    dz = p1[2] - p2[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)

def angle_with_horizontal_deg(p_left: Tuple[float, float], p_right: Tuple[float, float]) -> float:
    """
    Returns tilt angle of the line connecting left point to right point relative to horizontal.
    0 deg = level horizontal.
    Positive = right point is lower than left.
    Negative = right point is higher than left.
    Handles 180-degree wraparound: e.g. 177 deg behaves like -3 deg.
    """
    dx = p_right[0] - p_left[0]
    dy = p_right[1] - p_left[1] # In image coords, +y is downwards
    if abs(dx) < 1e-6:
        return 90.0 if dy > 0 else -90.0
    angle_rad = math.atan2(dy, dx)
    deg = math.degrees(angle_rad)
    return wrap_angle_90(deg)

def angle_with_vertical_deg(p_top: Tuple[float, float], p_bottom: Tuple[float, float]) -> float:
    """
    Returns tilt angle of a vertical segment (e.g. torso from hip to shoulder) relative to true vertical.
    0 deg = perfectly vertical.
    """
    dx = p_top[0] - p_bottom[0]
    dy = p_top[1] - p_bottom[1] # dy is negative when top is above bottom in image coords
    # Standard vertical vector points straight up: (0, -1)
    # Angle between (dx, dy) and (0, -1)
    len_v = math.hypot(dx, dy)
    if len_v < 1e-6:
        return 0.0
    cos_angle = (-dy) / len_v
    cos_angle = max(-1.0, min(1.0, cos_angle))
    deg = math.degrees(math.acos(cos_angle))
    # Sign: positive if leaning right (dx > 0), negative if leaning left
    return deg if dx >= 0 else -deg

def compute_head_angles(
    nose: Tuple[float, float, float],
    left_eye: Tuple[float, float, float],
    right_eye: Tuple[float, float, float],
    left_ear: Tuple[float, float, float],
    right_ear: Tuple[float, float, float],
    chin: Optional[Tuple[float, float, float]] = None,
) -> Tuple[float, float, float]:
    """
    Computes (pitch, roll, yaw) in degrees for the head.
    - ROLL: Tilt towards left/right shoulder (from eye line).
    - YAW: Turning left/right (from nose position relative to ears/eyes midpoint).
    - PITCH: Looking up/down (from nose elevation relative to eye-ear plane or chin).
    """
    # 1. ROLL: Eye line angle relative to horizontal
    roll = angle_with_horizontal_deg(
        (left_eye[0], left_eye[1]),
        (right_eye[0], right_eye[1])
    )
    
    # 2. YAW: Compare distance from nose to left ear vs right ear
    eye_mid_x = (left_eye[0] + right_eye[0]) * 0.5
    ear_mid_x = (left_ear[0] + right_ear[0]) * 0.5
    inter_ear_dist = abs(left_ear[0] - right_ear[0]) + 1e-6
    # Relative offset of nose from ear midline normalized by ear width
    nose_offset = (nose[0] - ear_mid_x) / inter_ear_dist
    # Map to approximate yaw degrees (-90 to +90)
    yaw = max(-90.0, min(90.0, nose_offset * 110.0))
    
    # 3. PITCH: Angle of nose relative to ear midpoint calibrated for human facial anatomy
    # In anatomical neutral head position, the nose tip is naturally ~16.5° lower than the ear canals.
    # Calibrating this baseline makes normal upright laptop sitting ~11.5°, with forward bending > 17.5°.
    ear_mid_y = (left_ear[1] + right_ear[1]) * 0.5
    dy_nose = nose[1] - ear_mid_y
    inter_ear_dist = max(abs(left_ear[0] - right_ear[0]), 0.05)
    raw_pitch = math.degrees(math.atan2(dy_nose, inter_ear_dist))
    pitch = raw_pitch - 16.5
    pitch = max(-90.0, min(90.0, pitch))
    return pitch, roll, yaw

def compute_torso_recline_angle_deg(
    shoulder_center: Tuple[float, float, float],
    hip_center: Optional[Tuple[float, float, float]],
) -> float:
    """
    Computes torso recline (pitch backwards) angle in degrees.
    If hips are not visible, uses 3D Z-delta between shoulder center and camera baseline.
    Positive = torso reclined backwards into chair.
    Negative = torso tilted forward.
    """
    if hip_center is not None:
        # Vector from hip to shoulder: (dx, dy, dz)
        dy = shoulder_center[1] - hip_center[1] # Negative in image coords when shoulder is above hip
        dz = shoulder_center[2] - hip_center[2] # Positive if shoulder is further from camera (backwards)
        if abs(dy) > 1e-6:
            # Recline angle relative to vertical plane
            angle_rad = math.atan2(dz, -dy)
            return math.degrees(angle_rad)
    
    # When hips are occluded (typical laptop webcam view), MediaPipe pose landmark
    # coordinates place z=0 relative to hip origin. Positive shoulder_center[2]
    # indicates the upper body is tilted backwards into chair.
    # Normal upper torso vertical height is approximately 0.45 - 0.50 in normalized coordinates.
    dz = shoulder_center[2]
    angle_rad = math.atan2(dz, 0.48)
    return math.degrees(angle_rad)

def compute_neck_flexion_deg(
    head_pitch_deg: float,
    torso_recline_deg: float,
) -> float:
    """
    Computes neck flexion angle relative to the torso axis.
    If the torso is reclined back by 20 deg, but the head is pitched forward to look at laptop,
    neck flexion is head_pitch - (-torso_recline) = head_pitch + torso_recline.
    A neutral neck on a reclined torso would have head tilted back with the torso!
    """
    if torso_recline_deg > 5.0:
        # Torso is reclined backwards. Looking straight at laptop requires bending the neck forward!
        return head_pitch_deg + torso_recline_deg
    return head_pitch_deg
