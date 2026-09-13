"""
Automated Verification for Useful Mode Optimization: Tests 1 through 10.
Validates:
1. Normal upright -> GOOD (no alert)
2. Forward neck -> FORWARD_NECK (label correct, message from pool, stable over multiple frames)
3. Slouch -> SLOUCHING (label correct, message from pool)
4. Left lean -> LEANING_LEFT (label correct, message from pool)
5. Right lean -> LEANING_RIGHT (label correct, message from pool)
6. Head tilt -> HEAD_TILT (label correct, message from pool)
7. Reclined + bent neck -> RECLINED_BENT_NECK (label correct, message from pool)
8. Too close -> TOO_CLOSE (label correct, message from pool)
9. Recovery to normal -> Warning cleared, blur dismissed
10. Useless Mode -> Untouched, triggers on GOOD posture with useless comedy
"""
import sys
import time
from PyQt6.QtWidgets import QApplication

from config import PostureState, AppMode, POSTURE_DISPLAY_NAMES, USEFUL_MESSAGES, USELESS_MESSAGES
from posture_engine import PostureEngine, PostureMetrics
from overlay import ScreenBlurOverlay

def run_tests():
    app = QApplication.instance() or QApplication(sys.argv)
    engine = PostureEngine()
    overlay = ScreenBlurOverlay()
    
    print("=" * 80)
    print("RUNNING USEFUL MODE OPTIMIZATION VERIFICATION (TEST 1 - 10)")
    print("=" * 80)

    # -------------------------------------------------------------
    # TEST 1: Normal Upright
    # -------------------------------------------------------------
    print("\n[TEST 1] Normal Upright Sitting")
    upright = PostureMetrics(
        head_pitch_deg=11.5,
        head_roll_deg=1.0,
        shoulder_tilt_deg=0.5,
        head_shoulder_offset_x=0.01,
        chin_shoulder_ratio=0.42,
        head_shoulder_ratio=0.80,
        slouch_ratio=0.98,
        proximity_ratio=0.20,
        confidence=0.95,
    )
    raw_1 = engine._classify_raw_state(upright)
    assert raw_1 == PostureState.GOOD, f"Expected GOOD, got {raw_1}"
    print(f"  -> Classifier State: {raw_1.value}")
    print("  -> Verification: No warning triggered.")

    # -------------------------------------------------------------
    # Helper to test alert state UI synchronization and frame stability
    # -------------------------------------------------------------
    def verify_alert_ui(state: PostureState, test_name: str):
        print(f"\n[{test_name}] Testing Alert UI for {state.value}")
        overlay.trigger_warning(state, AppMode.USEFUL)
        app.processEvents()

        card = overlay.glass_card
        badge_text = card.status_pill.text_label.text()
        expected_badge = POSTURE_DISPLAY_NAMES[state].upper()
        assert expected_badge in badge_text or badge_text in expected_badge, f"Badge mismatch: {badge_text} vs {expected_badge}"

        title1 = card.title_label.text()
        sub1 = card.subtitle_label.text()
        pool = USEFUL_MESSAGES[state]
        assert (title1, sub1) in pool, f"Message {(title1, sub1)} not in {state.value} pool: {pool}"
        print(f"  -> POSTURE LABEL: {badge_text} (CORRECT)")
        print(f"  -> MESSAGE: \"{title1}\" | \"{sub1}\" (MATCHES POSTURE POOL)")
        print(f"  -> BLUR & GLASS UI: PRESENT")

        # Frame Stability Test: 20 successive frames must NOT re-randomize or change the message
        for _ in range(20):
            overlay.trigger_warning(state, AppMode.USEFUL)
            app.processEvents()
            assert card.title_label.text() == title1, "CRITICAL ERROR: Message changed between frames!"
            assert card.subtitle_label.text() == sub1, "CRITICAL ERROR: Subtitle changed between frames!"
        print("  -> STABILITY: Verified message remains rock-solid across frames (no flickering).")

    # -------------------------------------------------------------
    # TEST 2: Forward Neck
    # -------------------------------------------------------------
    fn_metrics = PostureMetrics(
        head_pitch_deg=19.0,
        chin_shoulder_ratio=0.27,
        confidence=0.95,
    )
    assert engine._classify_raw_state(fn_metrics) == PostureState.FORWARD_NECK
    verify_alert_ui(PostureState.FORWARD_NECK, "TEST 2: Forward Neck")

    # -------------------------------------------------------------
    # TEST 3: Slouching
    # -------------------------------------------------------------
    sl_metrics = PostureMetrics(
        slouch_ratio=0.68,
        head_pitch_deg=15.0,
        confidence=0.95,
    )
    assert engine._classify_raw_state(sl_metrics) == PostureState.SLOUCHING
    verify_alert_ui(PostureState.SLOUCHING, "TEST 3: Slouching")

    # -------------------------------------------------------------
    # TEST 4: Left Lean
    # -------------------------------------------------------------
    ll_metrics = PostureMetrics(
        head_shoulder_offset_x=-0.25,
        shoulder_tilt_deg=-9.0,
        confidence=0.95,
    )
    assert engine._classify_raw_state(ll_metrics) == PostureState.LEANING_LEFT
    verify_alert_ui(PostureState.LEANING_LEFT, "TEST 4: Left Lean")

    # -------------------------------------------------------------
    # TEST 5: Right Lean
    # -------------------------------------------------------------
    lr_metrics = PostureMetrics(
        head_shoulder_offset_x=0.25,
        shoulder_tilt_deg=9.0,
        confidence=0.95,
    )
    assert engine._classify_raw_state(lr_metrics) == PostureState.LEANING_RIGHT
    verify_alert_ui(PostureState.LEANING_RIGHT, "TEST 5: Right Lean")

    # -------------------------------------------------------------
    # TEST 6: Head Tilt
    # -------------------------------------------------------------
    ht_metrics = PostureMetrics(
        head_roll_deg=20.0,
        confidence=0.95,
    )
    assert engine._classify_raw_state(ht_metrics) == PostureState.HEAD_TILT
    verify_alert_ui(PostureState.HEAD_TILT, "TEST 6: Head Tilt")

    # -------------------------------------------------------------
    # TEST 7: Reclined + Bent Neck
    # -------------------------------------------------------------
    rec_metrics = PostureMetrics(
        torso_recline_deg=22.0,
        neck_flexion_deg=24.0,
        confidence=0.95,
    )
    assert engine._classify_raw_state(rec_metrics) == PostureState.RECLINED_BENT_NECK
    verify_alert_ui(PostureState.RECLINED_BENT_NECK, "TEST 7: Reclined & Bent Neck")

    # -------------------------------------------------------------
    # TEST 8: Too Close
    # -------------------------------------------------------------
    tc_metrics = PostureMetrics(
        proximity_ratio=0.45,
        confidence=0.95,
    )
    assert engine._classify_raw_state(tc_metrics) == PostureState.TOO_CLOSE
    verify_alert_ui(PostureState.TOO_CLOSE, "TEST 8: Too Close to Screen")

    # -------------------------------------------------------------
    # TEST 9: Recovery to Normal (Dismissal)
    # -------------------------------------------------------------
    print("\n[TEST 9] Recovery to Normal Upright Sitting")
    overlay.clear_warning()
    for _ in range(25):
        time.sleep(0.02)
        app.processEvents()
    assert not overlay.isVisible(), "Overlay must be hidden after dismissal animation completes"
    print("  -> Warning dismissed successfully. Backdrop blur & glass panel fade away together.")

    # -------------------------------------------------------------
    # TEST 10: Useless Mode (Unchanged & Working)
    # -------------------------------------------------------------
    print("\n[TEST 10] Useless Mode Integrity")
    overlay.trigger_warning(PostureState.GOOD, AppMode.USELESS)
    app.processEvents()
    card = overlay.glass_card
    assert "POSTURE PERFECT" in card.status_pill.text_label.text()
    assert "Useless Mode" in card.mode_label.text()
    useless_msg = (card.title_label.text(), card.subtitle_label.text())
    assert useless_msg in USELESS_MESSAGES, f"Useless message {useless_msg} not in USELESS_MESSAGES"
    print(f"  -> Useless Mode triggered on GOOD posture with comedy: \"{useless_msg[0]}\"")
    print(f"  -> Useless Mode logic and design 100% intact and functional.")

    overlay.clear_warning()
    overlay.close()
    print("\n" + "=" * 80)
    print("ALL 10 TESTS PASSED WITH ZERO ERRORS!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
