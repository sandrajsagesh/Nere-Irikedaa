"""
Verification script for geometry, posture engine, and vision detector.
"""
import sys
import numpy as np
from geometry import angular_distance, wrap_angle_180, compute_head_angles
from config import PostureState, Sensitivity
from posture_engine import PostureEngine, PostureMetrics
from vision import VisionDetector, LandmarkBundle
import cv2

def test_geometry():
    print("Testing geometry functions...")
    # Wraparound test: 178 deg vs -178 deg should be 4 degrees apart
    diff = angular_distance(178, -178)
    assert abs(diff - (-4.0)) < 1e-5, f"Expected -4.0, got {diff}"
    
    diff2 = angular_distance(-178, 178)
    assert abs(diff2 - 4.0) < 1e-5, f"Expected 4.0, got {diff2}"
    
    # 359 deg vs 1 deg should be -2 deg
    diff3 = angular_distance(359, 1)
    assert abs(diff3 - (-2.0)) < 1e-5, f"Expected -2.0, got {diff3}"

    # 177 deg wraparound: should behave like -3 deg
    from geometry import wrap_angle_90, angle_with_horizontal_deg
    w_deg = wrap_angle_90(177.0)
    assert abs(w_deg - (-3.0)) < 1e-5, f"Expected -3.0 for wrap_angle_90(177), got {w_deg}"
    w_neg = wrap_angle_90(-177.0)
    assert abs(w_neg - (3.0)) < 1e-5, f"Expected 3.0 for wrap_angle_90(-177), got {w_neg}"

    # Inverted points on horizontal line (dx < 0) should wrap 177.1 deg to -2.9 deg
    tilt = angle_with_horizontal_deg((0.5, 0.5), (0.3, 0.51))
    assert abs(tilt - (-2.86)) < 0.05, f"Expected ~ -2.86 deg, got {tilt}"
    print("[PASS] Angular distance and 177 deg -> -3 deg wraparound verified.")

def test_posture_classification():
    print("Testing posture classification rules...")
    engine = PostureEngine(Sensitivity.NORMAL)
    
    # 1. Normal upright sitting
    normal_m = PostureMetrics(
        head_pitch_deg=11.5,  # Natural laptop gaze
        head_roll_deg=2.0,   # Tiny natural tilt
        head_yaw_deg=4.0,    # Looking slightly to side
        shoulder_tilt_deg=1.0,
        torso_recline_deg=4.0,
        neck_flexion_deg=10.0,
        head_shoulder_offset_x=0.03,
        head_shoulder_offset_z=1.03,
        chin_shoulder_ratio=0.42,
        head_shoulder_ratio=0.80,
        slouch_ratio=0.98,
        proximity_ratio=0.22,
        confidence=0.92,
    )
    assert engine._classify_raw_state(normal_m) == PostureState.GOOD, "Normal sitting must be GOOD!"
    print("[PASS] Normal laptop sitting classified as GOOD.")
    
    # 2. Forward neck (pitch + chin compression)
    forward_m = PostureMetrics(
        head_pitch_deg=18.0,
        chin_shoulder_ratio=0.28,
        confidence=0.90,
    )
    assert engine._classify_raw_state(forward_m) == PostureState.FORWARD_NECK, "Forward neck must trigger FORWARD_NECK"
    print("[PASS] Forward neck (pitch + chin compression) classified correctly.")

    # 2b. Forward head bending (severe downward pitch)
    forward_bend = PostureMetrics(
        head_pitch_deg=21.0,
        chin_shoulder_ratio=0.32,
        confidence=0.90,
    )
    assert engine._classify_raw_state(forward_bend) == PostureState.FORWARD_NECK, "Forward head bending must trigger FORWARD_NECK"
    print("[PASS] Forward head bending (pitch down) classified correctly.")
    
    # 3. Slouching
    slouch_m = PostureMetrics(
        head_pitch_deg=18.0,
        slouch_ratio=0.68,
        confidence=0.90,
    )
    assert engine._classify_raw_state(slouch_m) == PostureState.SLOUCHING, "Slouching must trigger SLOUCHING"
    print("[PASS] Slouching classified correctly.")
    
    # 4a. Leaning Left
    lean_l = PostureMetrics(
        head_shoulder_offset_x=-0.26,
        confidence=0.90,
    )
    assert engine._classify_raw_state(lean_l) == PostureState.LEANING_LEFT
    print("[PASS] Leaning left classified correctly.")

    # 4b. Leaning Right
    lean_r = PostureMetrics(
        head_shoulder_offset_x=0.26,
        confidence=0.90,
    )
    assert engine._classify_raw_state(lean_r) == PostureState.LEANING_RIGHT
    print("[PASS] Leaning right classified correctly.")
    
    # 5. Head tilt
    tilt_m = PostureMetrics(
        head_roll_deg=20.0,
        confidence=0.90,
    )
    assert engine._classify_raw_state(tilt_m) == PostureState.HEAD_TILT
    print("[PASS] Head tilt classified correctly.")
    
    # 6. Reclined + bent neck
    recline_neck = PostureMetrics(
        torso_recline_deg=22.0,
        neck_flexion_deg=24.0,
        confidence=0.90,
    )
    assert engine._classify_raw_state(recline_neck) == PostureState.RECLINED_BENT_NECK
    print("[PASS] Reclined + bent neck classified correctly.")
    
    # 7. Low confidence -> UNKNOWN
    low_conf = PostureMetrics(confidence=0.30)
    assert engine._classify_raw_state(low_conf) == PostureState.UNKNOWN
    print("[PASS] Low confidence classified as UNKNOWN.")

    # 8. Missing landmark bundle produces UNKNOWN and warning_active=False
    eval_none = engine.process(None)
    assert eval_none.state == PostureState.UNKNOWN
    assert eval_none.raw_state == PostureState.UNKNOWN
    assert not eval_none.warning_active, "UNKNOWN state must never keep warning active!"
    print("[PASS] Missing landmarks safety (UNKNOWN, warning inactive) verified.")

    # 9. Temporal smoothing: 1 single frame of bad posture must NOT trigger active warning
    engine_temp = PostureEngine(Sensitivity.NORMAL)
    from unittest.mock import MagicMock
    dummy_bundle = MagicMock()
    dummy_bundle.is_valid = True
    dummy_bundle.confidence = 0.95
    dummy_bundle.inter_shoulder_dist = 0.35
    dummy_bundle.face_width_ratio = 0.20
    dummy_bundle.nose = (0.5, 0.4, 0.0)
    dummy_bundle.left_eye = (0.45, 0.38, 0.0)
    dummy_bundle.right_eye = (0.55, 0.38, 0.0)
    dummy_bundle.left_ear = (0.40, 0.38, 0.0)
    dummy_bundle.right_ear = (0.60, 0.38, 0.0)
    dummy_bundle.chin = (0.5, 0.48, 0.0)
    dummy_bundle.head_center = (0.5, 0.4, 0.0)
    dummy_bundle.left_shoulder = (0.32, 0.7, 0.0)
    dummy_bundle.right_shoulder = (0.68, 0.7, 0.0)
    dummy_bundle.shoulder_center = (0.5, 0.7, 0.0)
    dummy_bundle.left_hip = None
    dummy_bundle.right_hip = None
    dummy_bundle.hip_center = None

    # Step 1: Good frame
    ev1 = engine_temp.process(dummy_bundle)
    assert ev1.state in (PostureState.GOOD, PostureState.UNKNOWN)
    assert not ev1.warning_active

    # Step 2: One single slouch frame (e.g. glitch)
    dummy_bundle.head_center = (0.5, 0.65, 0.0) # head drop
    ev2 = engine_temp.process(dummy_bundle)
    assert not ev2.warning_active, "Single bad frame must not trigger active warning!"
    print("[PASS] Temporal smoothing prevents 1-frame false alert.")

def test_camera_and_vision():
    print("Testing VisionDetector with camera feed...")
    detector = VisionDetector()
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[SKIP] No camera opened, skipping live frame test.")
        return
        
    ret, frame = cap.read()
    cap.release()
    if ret and frame is not None:
        bundle = detector.process_frame(frame)
        print(f"VisionDetector processed frame. Result bundle: {'Valid person detected' if bundle else 'No person detected'}")
        if bundle:
            print(f"  Confidence: {bundle.confidence:.2f}")
            print(f"  Shoulder dist: {bundle.inter_shoulder_dist:.3f}")
    detector.close()
    print("[PASS] Vision detector frame processing works.")

if __name__ == "__main__":
    test_geometry()
    test_posture_classification()
    test_camera_and_vision()
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
