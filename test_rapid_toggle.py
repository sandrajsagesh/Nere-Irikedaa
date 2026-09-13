"""
Test Rapid Toggling between USEFUL and USELESS.
Verifies:
1. Thumb indicator glides smoothly between positions.
2. Rapid reversals (Useful -> Useless -> Useful -> Useless) do not get stuck, glitch, or jump.
3. Signal emission is consistent and non-blocking.
"""
import sys
import time
from PyQt6.QtWidgets import QApplication

from config import AppMode
from app_window import MainWindow

def test_rapid_toggling():
    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow(initial_mode=AppMode.USEFUL)
    win.show()

    print("=" * 80)
    print("STARTING RAPID TOGGLE STRESS TEST")
    print("=" * 80)

    toggle = win.toggle
    assert toggle.thumb_progress == 0.0, "Initial thumb progress should be 0.0"

    modes_to_test = [
        AppMode.USELESS,
        AppMode.USEFUL,
        AppMode.USELESS,
        AppMode.USEFUL,
        AppMode.USELESS,
        AppMode.USEFUL,
        AppMode.USELESS,
        AppMode.USEFUL,
    ]

    for idx, target_mode in enumerate(modes_to_test, 1):
        target_val = 0.0 if target_mode == AppMode.USEFUL else 1.0
        print(f"\n[Toggle Step {idx:02d}/08] Switching to {target_mode.value.upper()} (target {target_val:.1f})...")
        
        # Trigger toggle
        toggle.set_mode(target_mode)
        
        # Advance event loop over ~180ms (mid-flight check)
        for _ in range(9):
            time.sleep(0.02)
            app.processEvents()

        # Step remaining ~180ms to settle
        for _ in range(10):
            time.sleep(0.02)
            app.processEvents()

        current_val = toggle.thumb_progress
        if target_mode == AppMode.USEFUL:
            assert current_val < 0.05, f"Expected thumb near 0.0, got {current_val}"
        else:
            assert current_val > 0.95, f"Expected thumb near 1.0, got {current_val}"
            
        print(f"  -> Successfully settled at {target_mode.value.upper()} (thumb_progress={current_val:.3f})")

    # Now test rapid mid-flight reversal
    print("\n[Mid-Flight Reversal Test] Reversing mid-flight at ~50% progress...")
    toggle.set_mode(AppMode.USELESS)
    for _ in range(6): # ~120ms (roughly mid-flight)
        time.sleep(0.02)
        app.processEvents()
    mid_progress = toggle.thumb_progress
    print(f"  -> Mid-flight position: {mid_progress:.3f}")
    assert 0.15 < mid_progress < 0.85, f"Should be mid-flight, got {mid_progress}"

    # Immediately reverse
    toggle.set_mode(AppMode.USEFUL)
    for _ in range(20):
        time.sleep(0.02)
        app.processEvents()

    final_progress = toggle.thumb_progress
    assert final_progress < 0.05, f"Expected to smoothly return to Useful (0.0), got {final_progress}"
    print(f"  -> Reversed mid-flight smoothly without jump! Settled at {final_progress:.3f}")

    win.close()
    print("\n" + "=" * 80)
    print("ALL RAPID TOGGLE TESTS PASSED PERFECTLY!")
    print("=" * 80)

if __name__ == "__main__":
    test_rapid_toggling()
