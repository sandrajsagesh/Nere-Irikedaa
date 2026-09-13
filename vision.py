"""
Vision module for Useless 3.0 Posture Glass.
Wraps MediaPipe Tasks (PoseLandmarker and FaceLandmarker) to extract reliable 3D upper-body landmarks.
"""
from dataclasses import dataclass
from typing import Optional, Tuple, List
import time
import numpy as np
import mediapipe as mp
import cv2

from config import POSE_MODEL_PATH, FACE_MODEL_PATH

BaseOptions = mp.tasks.BaseOptions
PoseLandmarker = mp.tasks.vision.PoseLandmarker
PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

@dataclass
class LandmarkBundle:
    # 3D points normalized to [0, 1] for x, y; z is depth relative to center
    nose: Tuple[float, float, float]
    left_eye: Tuple[float, float, float]
    right_eye: Tuple[float, float, float]
    left_ear: Tuple[float, float, float]
    right_ear: Tuple[float, float, float]
    head_center: Tuple[float, float, float]
    
    left_shoulder: Tuple[float, float, float]
    right_shoulder: Tuple[float, float, float]
    shoulder_center: Tuple[float, float, float]
    
    left_hip: Optional[Tuple[float, float, float]]
    right_hip: Optional[Tuple[float, float, float]]
    hip_center: Optional[Tuple[float, float, float]]
    
    chin: Optional[Tuple[float, float, float]]
    
    # Scale normalization metrics
    inter_shoulder_dist: float
    face_width_ratio: float
    
    # Metadata
    confidence: float
    is_valid: bool
    timestamp: float

class VisionDetector:
    def __init__(self):
        if not POSE_MODEL_PATH.exists():
            raise FileNotFoundError(f"Pose model not found at {POSE_MODEL_PATH}")
            
        pose_options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(POSE_MODEL_PATH)),
            running_mode=VisionRunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.pose_landmarker = PoseLandmarker.create_from_options(pose_options)
        
        # Face landmarker for high fidelity pitch / proximity
        self.face_landmarker = None
        if FACE_MODEL_PATH.exists():
            try:
                face_options = FaceLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=str(FACE_MODEL_PATH)),
                    running_mode=VisionRunningMode.IMAGE,
                    num_faces=1,
                    min_face_detection_confidence=0.5,
                )
                self.face_landmarker = FaceLandmarker.create_from_options(face_options)
            except Exception as e:
                print(f"[VisionDetector] Face Landmarker initialization skipped: {e}")

    def process_frame(self, frame_bgr: np.ndarray) -> Optional[LandmarkBundle]:
        """
        Processes a BGR image frame from camera, returns LandmarkBundle or None if no valid person found.
        """
        now = time.time()
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # 1. Detect Pose Landmarks
        pose_result = self.pose_landmarker.detect(mp_image)
        if not pose_result.pose_landmarks or len(pose_result.pose_landmarks) == 0:
            return None
            
        landmarks = pose_result.pose_landmarks[0]
        
        # Landmark indices in MediaPipe Pose:
        # 0: nose, 2: left_eye, 5: right_eye, 7: left_ear, 8: right_ear
        # 11: left_shoulder, 12: right_shoulder
        # 23: left_hip, 24: right_hip
        
        # Check core landmark visibility
        nose_lm = landmarks[0]
        left_sh_lm = landmarks[11]
        right_sh_lm = landmarks[12]
        
        # Visibility check (must be at least 0.5)
        core_lms = [nose_lm, left_sh_lm, right_sh_lm]
        avg_vis = sum(lm.visibility for lm in core_lms) / len(core_lms)
        if avg_vis < 0.45:
            return None
            
        def to_point(lm) -> Tuple[float, float, float]:
            return (float(lm.x), float(lm.y), float(lm.z))
            
        nose = to_point(nose_lm)
        left_eye = to_point(landmarks[2])
        right_eye = to_point(landmarks[5])
        left_ear = to_point(landmarks[7])
        right_ear = to_point(landmarks[8])
        left_sh = to_point(left_sh_lm)
        right_sh = to_point(right_sh_lm)
        
        # Shoulder center
        sh_center = (
            (left_sh[0] + right_sh[0]) * 0.5,
            (left_sh[1] + right_sh[1]) * 0.5,
            (left_sh[2] + right_sh[2]) * 0.5,
        )
        
        # Inter-shoulder distance
        dx_sh = left_sh[0] - right_sh[0]
        dy_sh = left_sh[1] - right_sh[1]
        inter_sh_dist = np.hypot(dx_sh, dy_sh)
        if inter_sh_dist < 0.08: # User too far or shoulders collapsed/not visible
            return None
            
        # Head center estimate
        head_center = (
            (left_ear[0] + right_ear[0] + nose[0]) / 3.0,
            (left_ear[1] + right_ear[1] + nose[1]) / 3.0,
            (left_ear[2] + right_ear[2] + nose[2]) / 3.0,
        )
        
        # Hips (if visible)
        left_hip_lm = landmarks[23]
        right_hip_lm = landmarks[24]
        left_hip = None
        right_hip = None
        hip_center = None
        if left_hip_lm.visibility > 0.4 and right_hip_lm.visibility > 0.4:
            left_hip = to_point(left_hip_lm)
            right_hip = to_point(right_hip_lm)
            hip_center = (
                (left_hip[0] + right_hip[0]) * 0.5,
                (left_hip[1] + right_hip[1]) * 0.5,
                (left_hip[2] + right_hip[2]) * 0.5,
            )
            
        # Face Landmarker for chin and proximity width
        chin = None
        face_width_ratio = 0.20
        if self.face_landmarker:
            face_result = self.face_landmarker.detect(mp_image)
            if face_result.face_landmarks and len(face_result.face_landmarks) > 0:
                f_lms = face_result.face_landmarks[0]
                # Landmark 152 in Face Mesh is chin bottom
                chin_lm = f_lms[152]
                chin = (float(chin_lm.x), float(chin_lm.y), float(chin_lm.z))
                # Left cheek: 234, Right cheek: 454
                cheek_l = f_lms[234]
                cheek_r = f_lms[454]
                face_width_ratio = abs(float(cheek_l.x) - float(cheek_r.x))
        else:
            # Fallback face width from ears
            face_width_ratio = abs(left_ear[0] - right_ear[0])
            
        confidence = min(1.0, max(0.0, avg_vis))
        
        return LandmarkBundle(
            nose=nose,
            left_eye=left_eye,
            right_eye=right_eye,
            left_ear=left_ear,
            right_ear=right_ear,
            head_center=head_center,
            left_shoulder=left_sh,
            right_shoulder=right_sh,
            shoulder_center=sh_center,
            left_hip=left_hip,
            right_hip=right_hip,
            hip_center=hip_center,
            chin=chin,
            inter_shoulder_dist=float(inter_sh_dist),
            face_width_ratio=float(face_width_ratio),
            confidence=float(confidence),
            is_valid=True,
            timestamp=now,
        )

    def close(self):
        try:
            self.pose_landmarker.close()
        except Exception:
            pass
        if self.face_landmarker:
            try:
                self.face_landmarker.close()
            except Exception:
                pass
