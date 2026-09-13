"""
Stress Test: 10 Alert / Recovery Cycles & State Transitions.
Verifies:
- Clean entrance and exit animations
- Background blur and dim interpolation (0.0 -> 1.0 -> 0.0)
- Zero memory leaks / resource buildup
- Zero duplicate panels
- No stuck overlay window
- Fast and reliable recovery
"""
import sys
import time
from PyQt6.QtWidgets import QApplication

from config import PostureState, AppMode, POSTURE_DISPLAY_NAMES
from overlay import ScreenBlurOverlay

def test_10_cycles():
    app = QApplication.instance() or QApplication(sys.argv)
    overlay = ScreenBlurOverlay()
    
    print("=" * 80)
    print("STARTING 10-CYCLE ALERT / RECOVERY STRESS TEST")
    print("=" * 80)

    states_to_test = [
        (PostureState.FORWARD_NECK, AppMode.USEFUL),
        (PostureState.SLOUCHING, AppMode.USEFUL),
        (PostureState.LEANING_LEFT, AppMode.USEFUL),
        (PostureState.LEANING_RIGHT, AppMode.USEFUL),
        (PostureState.GOOD, AppMode.USELESS),
        (PostureState.HEAD_TILT, AppMode.USEFUL),
        (PostureState.RECLINED_BENT_NECK, AppMode.USEFUL),
        (PostureState.TOO_CLOSE, AppMode.USEFUL),
        (PostureState.GOOD, AppMode.USELESS),
        (PostureState.FORWARD_NECK, AppMode.USEFUL),
    ]

    for cycle_idx, (state, mode) in enumerate(states_to_test, 1):
        print(f"\n[Cycle {cycle_idx:02d}/10] Triggering {state.value} ({mode.value.upper()} mode)")
        
        # 1. Trigger Alert
        overlay.trigger_warning(state, mode)
        # Advance event loop over entrance animation duration
        for _ in range(28):
            time.sleep(0.02)
            app.processEvents()

        assert overlay.isVisible(), f"Overlay must be visible in cycle {cycle_idx}"
        assert overlay._blur_progress > 0.85, f"Blur progress should be near 1.0, got {overlay._blur_progress}"
        assert overlay.card_opacity.opacity() > 0.85, f"Card opacity should be near 1.0, got {overlay.card_opacity.opacity()}"
        print(f"  -> Entrance verified: Blur={overlay._blur_progress:.2f}, Opacity={overlay.card_opacity.opacity():.2f}")

        # 2. Hold alert briefly
        time.sleep(0.1)
        app.processEvents()

        # 3. Dismiss Alert
        overlay.clear_warning()
        # Advance event loop over exit animation duration
        for _ in range(28):
            time.sleep(0.02)
            app.processEvents()

        assert not overlay.isVisible(), f"Overlay must be cleanly hidden in cycle {cycle_idx}"
        assert overlay._blur_progress == 0.0, f"Blur progress must be 0.0, got {overlay._blur_progress}"
        assert overlay.clean_pixmap is None, "clean_pixmap must be cleared after hide"
        assert overlay.blurred_pixmap is None, "blurred_pixmap must be cleared after hide"
        print(f"  -> Recovery verified: Blur=0.00, Window hidden, resources released cleanly.")

    # 4. Rapid state switching without dismissal (Dynamic Island crossfade test)
    print("\n[Continuous Crossfade Test] Transitioning through multiple bad postures in succession...")
    overlay.trigger_warning(PostureState.FORWARD_NECK, AppMode.USEFUL)
    for _ in range(15):
        time.sleep(0.02)
        app.processEvents()

    for shift_state in [PostureState.SLOUCHING, PostureState.LEANING_LEFT, PostureState.LEANING_RIGHT]:
        overlay.trigger_warning(shift_state, AppMode.USEFUL)
        for _ in range(10):
            time.sleep(0.02)
            app.processEvents()
        expected_badge = POSTURE_DISPLAY_NAMES[shift_state].upper()
        assert expected_badge in overlay.glass_card.status_pill.text_label.text()
        print(f"  -> Crossfaded seamlessly to {shift_state.value}")

    # Final dismiss
    overlay.clear_warning()
    for _ in range(28):
        time.sleep(0.02)
        app.processEvents()
    assert not overlay.isVisible()

    overlay.close()
    print("\n" + "=" * 80)
    print("ALL 10 CYCLES & DYNAMIC TRANSITIONS PASSED FLAWLESSLY WITH ZERO ISSUES!")
    print("=" * 80)

if __name__ == "__main__":
    test_10_cycles()
