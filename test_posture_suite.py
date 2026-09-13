"""
Comprehensive Posture Suite: Verifies TEST A through TEST F.
"""
import sys
from config import PostureState, Sensitivity
from posture_engine import PostureEngine, PostureMetrics

def run_suite():
    print("=" * 70)
    print("RUNNING COMPREHENSIVE POSTURE VERIFICATION SUITE (TESTS A - F)")
    print("=" * 70)
    
    engine = PostureEngine(Sensitivity.NORMAL)
    
    # -------------------------------------------------------------
    # TEST A: Sit normally upright and look at laptop.
    # Expected: GOOD
    # -------------------------------------------------------------
    upright_metrics = PostureMetrics(
        head_pitch_deg=11.5,       # Normal laptop gaze
        head_roll_deg=1.5,         # Natural slight head levelness
        head_yaw_deg=-2.0,         # Normal gaze
        shoulder_tilt_deg=1.0,     # Level shoulders
        torso_recline_deg=4.0,     # Normal upright chair contact
        neck_flexion_deg=11.5,     # Natural neck
        head_shoulder_offset_x=0.02,# Centered
        head_shoulder_offset_z=1.03,# Standard camera distance
        chin_shoulder_ratio=0.42,  # Chin well above shoulders
        head_shoulder_ratio=0.80,  # Head high
        slouch_ratio=0.98,         # Full height
        proximity_ratio=0.22,
        confidence=0.95,
    )
    res_a = engine._classify_raw_state(upright_metrics)
    assert res_a == PostureState.GOOD, f"TEST A FAILED: Expected GOOD, got {res_a}"
    print("[PASS] TEST A: Normal upright sitting classified as GOOD.")
    
    # -------------------------------------------------------------
    # TEST B: Keep shoulders approximately normal but bend neck forward/down toward laptop.
    # Expected: FORWARD_NECK
    # -------------------------------------------------------------
    forward_neck_metrics = PostureMetrics(
        head_pitch_deg=18.5,       # Pitched down toward keyboard/screen
        head_roll_deg=0.5,         # Not tilted sideways
        shoulder_tilt_deg=1.5,     # Normal shoulders
        head_shoulder_offset_x=0.01,# Centered laterally
        chin_shoulder_ratio=0.26,  # Chin compressed toward chest
        head_shoulder_ratio=0.64,  # Head lowered toward shoulders
        slouch_ratio=0.94,         # Torso not collapsed
        confidence=0.95,
    )
    res_b = engine._classify_raw_state(forward_neck_metrics)
    assert res_b == PostureState.FORWARD_NECK, f"TEST B FAILED: Expected FORWARD_NECK, got {res_b}"
    print("[PASS] TEST B: Forward/downward neck bending classified as FORWARD_NECK.")

    # -------------------------------------------------------------
    # TEST C: Lean the whole upper body left.
    # Expected: LEANING_LEFT
    # -------------------------------------------------------------
    lean_left_metrics = PostureMetrics(
        head_pitch_deg=11.0,
        head_shoulder_offset_x=-0.26, # Shifted to the left past 0.22 threshold
        shoulder_tilt_deg=-10.5,      # Shoulder tilted left
        chin_shoulder_ratio=0.40,
        confidence=0.95,
    )
    res_c = engine._classify_raw_state(lean_left_metrics)
    assert res_c == PostureState.LEANING_LEFT, f"TEST C FAILED: Expected LEANING_LEFT, got {res_c}"
    print("[PASS] TEST C: Upper body leaning left classified as LEANING_LEFT.")

    # -------------------------------------------------------------
    # TEST D: Lean the whole upper body right.
    # Expected: LEANING_RIGHT
    # -------------------------------------------------------------
    lean_right_metrics = PostureMetrics(
        head_pitch_deg=11.0,
        head_shoulder_offset_x=0.27,  # Shifted to the right past 0.22 threshold
        shoulder_tilt_deg=11.0,       # Shoulder tilted right
        chin_shoulder_ratio=0.40,
        confidence=0.95,
    )
    res_d = engine._classify_raw_state(lean_right_metrics)
    assert res_d == PostureState.LEANING_RIGHT, f"TEST D FAILED: Expected LEANING_RIGHT, got {res_d}"
    print("[PASS] TEST D: Upper body leaning right classified as LEANING_RIGHT.")

    # -------------------------------------------------------------
    # TEST E: Recline backward while bending neck forward/down toward laptop.
    # Expected: RECLINED_BENT_NECK
    # -------------------------------------------------------------
    recline_metrics = PostureMetrics(
        head_pitch_deg=12.0,       # Head flexed to see screen
        torso_recline_deg=22.0,    # Torso reclined back into chair (> 16 deg)
        neck_flexion_deg=24.0,     # Total neck flexion relative to torso (> 20 deg)
        confidence=0.95,
    )
    res_e = engine._classify_raw_state(recline_metrics)
    assert res_e == PostureState.RECLINED_BENT_NECK, f"TEST E FAILED: Expected RECLINED_BENT_NECK, got {res_e}"
    print("[PASS] TEST E: Reclining backward while bending neck forward classified as RECLINED_BENT_NECK.")

    # -------------------------------------------------------------
    # TEST F: Move slightly or change position without clearly bad posture.
    # Expected: GOOD or UNKNOWN, never a false alert.
    # -------------------------------------------------------------
    # F1: Natural slight head turn (yaw), slight pitch movement
    slight_move_metrics = PostureMetrics(
        head_pitch_deg=13.0,       # Slight gaze shift
        head_roll_deg=4.0,         # Slight natural tilt
        head_yaw_deg=15.0,         # Turned head to read side of screen
        shoulder_tilt_deg=3.0,     # Slight shoulder asymmetry
        head_shoulder_offset_x=0.06,# Small head movement
        chin_shoulder_ratio=0.38,  # Chin remains uncompressed
        head_shoulder_ratio=0.76,  # Head high
        slouch_ratio=0.93,         # No slouch
        confidence=0.92,
    )
    res_f1 = engine._classify_raw_state(slight_move_metrics)
    assert res_f1 == PostureState.GOOD, f"TEST F1 FAILED: Expected GOOD, got {res_f1}"
    
    # F2: Low visibility or missing landmarks
    low_vis_metrics = PostureMetrics(
        confidence=0.25,           # Landmark detection uncertain
    )
    res_f2 = engine._classify_raw_state(low_vis_metrics)
    assert res_f2 == PostureState.UNKNOWN, f"TEST F2 FAILED: Expected UNKNOWN, got {res_f2}"
    print("[PASS] TEST F: Natural slight movements and low-confidence frames result in GOOD or UNKNOWN (never false alert).")

    print("=" * 70)
    print("ALL TESTS (TEST A - TEST F) PASSED WITH ZERO ERRORS!")
    print("=" * 70)

if __name__ == "__main__":
    run_suite()
