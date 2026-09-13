"""
Posture Engine for Useless 3.0 — Posture Glass.
Extracts geometric metrics, classifies upper-body posture, and performs temporal hysteresis filtering.
"""
from collections import deque
from dataclasses import dataclass
import time
from typing import Optional, Tuple, Dict, Any

from config import (
    PostureState,
    Sensitivity,
    THRESHOLDS_BY_SENSITIVITY,
    SUSTAINED_BAD_POSTURE_SEC,
    STABLE_GOOD_POSTURE_SEC,
    SMOOTHING_ALPHA,
)
from geometry import (
    compute_head_angles,
    angle_with_horizontal_deg,
    compute_torso_recline_angle_deg,
    compute_neck_flexion_deg,
)
from vision import LandmarkBundle

@dataclass
class PostureMetrics:
    head_pitch_deg: float = 0.0
    head_roll_deg: float = 0.0
    head_yaw_deg: float = 0.0
    shoulder_tilt_deg: float = 0.0
    torso_recline_deg: float = 0.0
    neck_flexion_deg: float = 0.0
    head_shoulder_offset_x: float = 0.0  # normalized by shoulder width
    head_shoulder_offset_z: float = 0.0  # head forward protrusion
    chin_shoulder_ratio: float = 0.42   # chin to shoulder vertical distance / shoulder width
    head_shoulder_ratio: float = 0.80   # head center to shoulder vertical distance / shoulder width
    slouch_ratio: float = 1.0           # vertical compression ratio
    proximity_ratio: float = 0.20        # face size ratio
    confidence: float = 0.0

@dataclass
class PostureEvaluation:
    state: PostureState
    raw_state: PostureState
    metrics: PostureMetrics
    confidence: float
    time_in_state: float
    warning_active: bool

class PostureEngine:
    def __init__(self, sensitivity: Sensitivity = Sensitivity.NORMAL):
        self.sensitivity = sensitivity
        self.thresholds = THRESHOLDS_BY_SENSITIVITY[sensitivity]
        
        # Smoothed metrics (Exponential Moving Average)
        self.metrics = PostureMetrics()
        self._is_first_frame = True
        
        # Baseline reference for upright height (calibrates naturally during good posture)
        self._baseline_head_sh_dy: Optional[float] = None
        
        # Temporal state tracking
        self.current_state = PostureState.UNKNOWN
        self.candidate_bad_state = PostureState.GOOD
        self.bad_state_start_time: float = 0.0
        self.good_state_start_time: float = 0.0
        self.unknown_start_time: float = 0.0
        self.candidate_shift_start_time: float = 0.0
        self.state_since_time: float = time.time()
        self._bad_state_history: deque = deque(maxlen=8)
        
        self.warning_active: bool = False

    def set_sensitivity(self, sensitivity: Sensitivity):
        self.sensitivity = sensitivity
        self.thresholds = THRESHOLDS_BY_SENSITIVITY[sensitivity]

    def _update_smoothed_metrics(self, raw: PostureMetrics):
        if self._is_first_frame:
            self.metrics = raw
            self._is_first_frame = False
            return
            
        a = SMOOTHING_ALPHA
        # EMA smoothing on continuous values
        self.metrics.head_pitch_deg = (1 - a) * self.metrics.head_pitch_deg + a * raw.head_pitch_deg
        self.metrics.head_roll_deg = (1 - a) * self.metrics.head_roll_deg + a * raw.head_roll_deg
        self.metrics.head_yaw_deg = (1 - a) * self.metrics.head_yaw_deg + a * raw.head_yaw_deg
        self.metrics.shoulder_tilt_deg = (1 - a) * self.metrics.shoulder_tilt_deg + a * raw.shoulder_tilt_deg
        self.metrics.torso_recline_deg = (1 - a) * self.metrics.torso_recline_deg + a * raw.torso_recline_deg
        self.metrics.neck_flexion_deg = (1 - a) * self.metrics.neck_flexion_deg + a * raw.neck_flexion_deg
        self.metrics.head_shoulder_offset_x = (1 - a) * self.metrics.head_shoulder_offset_x + a * raw.head_shoulder_offset_x
        self.metrics.head_shoulder_offset_z = (1 - a) * self.metrics.head_shoulder_offset_z + a * raw.head_shoulder_offset_z
        self.metrics.chin_shoulder_ratio = (1 - a) * self.metrics.chin_shoulder_ratio + a * raw.chin_shoulder_ratio
        self.metrics.head_shoulder_ratio = (1 - a) * self.metrics.head_shoulder_ratio + a * raw.head_shoulder_ratio
        self.metrics.slouch_ratio = (1 - a) * self.metrics.slouch_ratio + a * raw.slouch_ratio
        self.metrics.proximity_ratio = (1 - a) * self.metrics.proximity_ratio + a * raw.proximity_ratio
        self.metrics.confidence = (1 - a) * self.metrics.confidence + a * raw.confidence

    def _compute_raw_metrics(self, bundle: LandmarkBundle) -> PostureMetrics:
        # 1. Head orientation (Pitch, Roll, Yaw)
        pitch, roll, yaw = compute_head_angles(
            nose=bundle.nose,
            left_eye=bundle.left_eye,
            right_eye=bundle.right_eye,
            left_ear=bundle.left_ear,
            right_ear=bundle.right_ear,
            chin=bundle.chin,
        )
        
        # 2. Shoulder tilt
        shoulder_tilt = angle_with_horizontal_deg(
            (bundle.left_shoulder[0], bundle.left_shoulder[1]),
            (bundle.right_shoulder[0], bundle.right_shoulder[1]),
        )
        
        # 3. Torso recline
        torso_recline = compute_torso_recline_angle_deg(
            bundle.shoulder_center,
            bundle.hip_center,
        )
        
        # 4. Neck flexion
        neck_flexion = compute_neck_flexion_deg(pitch, torso_recline)
        
        # 5. Normalized offsets
        sh_dist = max(bundle.inter_shoulder_dist, 0.10)
        # Lateral offset of head center from shoulder center, normalized by shoulder span
        offset_x = (bundle.head_center[0] - bundle.shoulder_center[0]) / sh_dist
        
        # Z-offset: Head z relative to shoulder center z (negative z is closer to camera)
        offset_z = (bundle.shoulder_center[2] - bundle.head_center[2]) / sh_dist
        
        # Chin and head vertical distance to shoulder line (normalized by shoulder span)
        eye_mid_y = (bundle.left_eye[1] + bundle.right_eye[1]) * 0.5
        chin_y = bundle.chin[1] if bundle.chin else (bundle.nose[1] + max(0.02, bundle.nose[1] - eye_mid_y))
        chin_sh_dist = (bundle.shoulder_center[1] - chin_y) / sh_dist
        head_sh_dist = (bundle.shoulder_center[1] - bundle.head_center[1]) / sh_dist
        
        # Slouch vertical distance (head center y to shoulder center y)
        vertical_dist = max(0.01, bundle.shoulder_center[1] - bundle.head_center[1])
        norm_vert = vertical_dist / sh_dist
        
        if self._baseline_head_sh_dy is None:
            self._baseline_head_sh_dy = norm_vert
        else:
            # Gradually update baseline if user is upright and happy
            if abs(roll) < 10 and abs(pitch) < 14 and abs(offset_x) < 0.15:
                if norm_vert > self._baseline_head_sh_dy:
                    self._baseline_head_sh_dy = 0.95 * self._baseline_head_sh_dy + 0.05 * norm_vert
                else:
                    self._baseline_head_sh_dy = 0.995 * self._baseline_head_sh_dy + 0.005 * norm_vert
                
        slouch_ratio = norm_vert / max(0.05, self._baseline_head_sh_dy)
        
        return PostureMetrics(
            head_pitch_deg=pitch,
            head_roll_deg=roll,
            head_yaw_deg=yaw,
            shoulder_tilt_deg=shoulder_tilt,
            torso_recline_deg=torso_recline,
            neck_flexion_deg=neck_flexion,
            head_shoulder_offset_x=offset_x,
            head_shoulder_offset_z=offset_z,
            chin_shoulder_ratio=chin_sh_dist,
            head_shoulder_ratio=head_sh_dist,
            slouch_ratio=slouch_ratio,
            proximity_ratio=bundle.face_width_ratio,
            confidence=bundle.confidence,
        )

    def _classify_raw_state(self, m: PostureMetrics) -> PostureState:
        th = self.thresholds
        
        # If confidence is too low or person not clearly visible -> UNKNOWN
        if m.confidence < 0.45:
            return PostureState.UNKNOWN
            
        # 1. TOO CLOSE check (highest priority safety)
        if m.proximity_ratio > th.proximity_face_ratio:
            return PostureState.TOO_CLOSE
            
        # 2. RECLINED + BENT NECK
        # Torso is reclined into chair (recline > threshold), but neck is flexed forward to see laptop
        if m.torso_recline_deg > th.torso_recline_angle_deg and m.neck_flexion_deg > th.neck_flexion_deg:
            return PostureState.RECLINED_BENT_NECK

        # 3. OBVIOUS LATERAL LEANING
        # Evaluated BEFORE forward neck and slouch so leaning is never misclassified!
        is_lean_left = (
            m.head_shoulder_offset_x < -0.18 or
            m.shoulder_tilt_deg < -7.0 or
            (m.head_shoulder_offset_x < -0.12 and m.shoulder_tilt_deg < -4.5)
        )
        is_lean_right = (
            m.head_shoulder_offset_x > 0.18 or
            m.shoulder_tilt_deg > 7.0 or
            (m.head_shoulder_offset_x > 0.12 and m.shoulder_tilt_deg > 4.5)
        )
        if is_lean_left:
            return PostureState.LEANING_LEFT
        if is_lean_right:
            return PostureState.LEANING_RIGHT

        # 4. SLOUCHING
        # Whole upper body vertical collapse downwards toward screen
        # Evaluated BEFORE forward neck so torso collapse is never misclassified as forward neck!
        if m.slouch_ratio < th.slouch_compression_ratio and m.head_pitch_deg > 10.0:
            return PostureState.SLOUCHING

        # 5. FORWARD NECK & FORWARD/DOWNWARD HEAD BENDING
        # Genuine forward/downward neck bending toward laptop with upright torso:
        is_forward_neck = (
            (m.head_pitch_deg > 16.5 and m.chin_shoulder_ratio < 0.33) or
            (m.head_pitch_deg > 20.0) or
            (m.chin_shoulder_ratio < 0.26 and m.head_pitch_deg > 15.0)
        )
        if is_forward_neck:
            return PostureState.FORWARD_NECK

        # 6. HEAD TILT
        # Roll angle of head exceeding tilt threshold while body is not heavily leaning
        if abs(m.head_roll_deg) > th.head_tilt_roll_deg:
            return PostureState.HEAD_TILT

        # 7. NORMAL LAPTOP USAGE (DEFAULT)
        # Looking down slightly to type, slight shoulder difference, natural head movement -> GOOD!
        return PostureState.GOOD

    def _log_state_change(self, old_state: PostureState, new_state: PostureState):
        if old_state != new_state:
            print(f"[UsefulDebug] state: {old_state.value} -> {new_state.value}")

    def process(self, bundle: Optional[LandmarkBundle]) -> PostureEvaluation:
        now = time.time()
        
        if bundle is None or not bundle.is_valid:
            # Low visibility or missing person -> UNKNOWN
            # CRITICAL RULE: UNKNOWN NEVER TRIGGERS A WARNING!
            raw_state = PostureState.UNKNOWN
            self.metrics.confidence = 0.0
            
            # Guard against 1-2 frame tracking drops: only clear after sustained absence (>= 0.8s)
            if self.unknown_start_time == 0.0:
                self.unknown_start_time = now
            
            if (now - self.unknown_start_time) >= 0.8:
                self.bad_state_start_time = 0.0
                self.good_state_start_time = 0.0
                if self.current_state != PostureState.UNKNOWN:
                    self._log_state_change(self.current_state, PostureState.UNKNOWN)
                    self.current_state = PostureState.UNKNOWN
                    self.state_since_time = now
                self.warning_active = False
            
            time_in_state = now - self.state_since_time
            return PostureEvaluation(
                state=self.current_state,
                raw_state=PostureState.UNKNOWN,
                metrics=self.metrics,
                confidence=0.0,
                time_in_state=time_in_state,
                warning_active=self.warning_active,
            )

        # Valid landmarks present:
        self.unknown_start_time = 0.0

        # 1. Compute raw measurements and update EMA
        raw_metrics = self._compute_raw_metrics(bundle)
        self._update_smoothed_metrics(raw_metrics)
        
        # 2. Classify raw posture state
        raw_state = self._classify_raw_state(self.metrics)
        
        # 3. Temporal Hysteresis & Persistence Filter
        if raw_state == PostureState.GOOD:
            self._bad_state_history.clear()
            # User is in good posture
            if self.good_state_start_time == 0.0:
                self.good_state_start_time = now
                
            good_duration = now - self.good_state_start_time
            # Only reset bad posture timer if good posture held for >= 0.35s
            # (Prevents 1-frame tracking jitter from wiping out sustained bad posture)
            if good_duration >= 0.35:
                self.bad_state_start_time = 0.0
                
            # If good posture sustained for STABLE_GOOD_POSTURE_SEC, clear active warning
            if good_duration >= STABLE_GOOD_POSTURE_SEC:
                if self.current_state != PostureState.GOOD:
                    self._log_state_change(self.current_state, PostureState.GOOD)
                    self.current_state = PostureState.GOOD
                    self.state_since_time = now
                self.warning_active = False
                
        elif raw_state == PostureState.UNKNOWN:
            self._bad_state_history.clear()
            # Confidence drop with landmarks
            if self.unknown_start_time == 0.0:
                self.unknown_start_time = now
            if (now - self.unknown_start_time) >= 0.8:
                self.bad_state_start_time = 0.0
                self.good_state_start_time = 0.0
                if self.current_state != PostureState.UNKNOWN:
                    self._log_state_change(self.current_state, PostureState.UNKNOWN)
                    self.current_state = PostureState.UNKNOWN
                    self.state_since_time = now
                self.warning_active = False
            
        else:
            # User is in a bad posture category (SLOUCHING, LEANING_LEFT, etc.)
            self.good_state_start_time = 0.0
            
            # Initialize or accumulate continuous bad posture duration
            if self.bad_state_start_time == 0.0:
                self.bad_state_start_time = now
                self.candidate_bad_state = raw_state
                self.candidate_shift_start_time = now
                
            bad_duration = now - self.bad_state_start_time
            
            if not self.warning_active:
                # Warning not active yet: track dominant candidate bad posture
                if raw_state == self.candidate_bad_state:
                    self.candidate_shift_start_time = now
                elif (now - self.candidate_shift_start_time) >= 0.35:
                    self.candidate_bad_state = raw_state
                    self.candidate_shift_start_time = now
                
                # Check if bad posture has been sustained for required duration
                if bad_duration >= SUSTAINED_BAD_POSTURE_SEC:
                    if self.current_state != self.candidate_bad_state:
                        self._log_state_change(self.current_state, self.candidate_bad_state)
                        self.current_state = self.candidate_bad_state
                        self.state_since_time = now
                    self.warning_active = True
            else:
                # Warning is ALREADY active: debounce state changes between bad postures
                self._bad_state_history.append(raw_state)
                if raw_state == self.current_state:
                    self.candidate_bad_state = raw_state
                    self.candidate_shift_start_time = now
                else:
                    if raw_state != self.candidate_bad_state:
                        self.candidate_bad_state = raw_state
                        self.candidate_shift_start_time = now

                    recent_count = sum(1 for s in self._bad_state_history if s == self.candidate_bad_state)
                    time_sustained = now - self.candidate_shift_start_time

                    # Transition if sustained >= 0.30s OR majority in rolling window (>= 5 of last 8)
                    if time_sustained >= 0.30 or recent_count >= 5:
                        if self.current_state != self.candidate_bad_state:
                            self._log_state_change(self.current_state, self.candidate_bad_state)
                            self.current_state = self.candidate_bad_state
                            self.state_since_time = now
                            self.bad_state_start_time = now
                            self._bad_state_history.clear()

        time_in_state = now - self.state_since_time

        return PostureEvaluation(
            state=self.current_state,
            raw_state=raw_state,
            metrics=self.metrics,
            confidence=self.metrics.confidence,
            time_in_state=time_in_state,
            warning_active=self.warning_active,
        )
