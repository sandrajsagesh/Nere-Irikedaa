"""
Automated Test for the Nere Irikedaa Startup Animation Sequence (Tests 5 consecutive launches).
"""
import sys
import time
from PyQt6.QtWidgets import QApplication

from config import AppMode
from app_window import MainWindow

def test_startup():
    app = QApplication.instance() or QApplication(sys.argv)

    print("=" * 80)
    print("STARTING STARTUP SEQUENCE VERIFICATION (5 CONSECUTIVE RUNS)")
    print("=" * 80)

    for run_idx in range(1, 6):
        print(f"\n[Run {run_idx}/5] Launching Nere Irikedaa startup sequence...")
        win = MainWindow(initial_mode=AppMode.USEFUL)
        win.play_startup_sequence()

        # Step 0-150ms: Initial state
        for _ in range(8):
            time.sleep(0.02)
            app.processEvents()

        assert win.splash_layer.isVisible(), "Splash layer must be visible at start"
        assert win.lbl_splash_hero.text() == "Nere Irikedaa", "Hero title must be Nere Irikedaa"
        assert win.hero_opacity.opacity() > 0.0, "Hero opacity should be fading in"
        print("  -> Step 1 (0-150ms): Splash layer active, 'Nere Irikedaa' fading in.")

        # Step 150-600ms: Settle hero & fade subtitle
        for _ in range(25):
            time.sleep(0.02)
            app.processEvents()

        assert win.hero_opacity.opacity() > 0.85, "Hero opacity should be near 1.0"
        assert win.sub_opacity.opacity() > 0.85, "Subtitle opacity should be near 1.0"
        print("  -> Step 2 (600ms): Hero settled, subtitle visible.")

        # Step 600-1550ms: Complete crossfade into dashboard
        for _ in range(48):
            time.sleep(0.02)
            app.processEvents()

        assert not win.splash_layer.isVisible(), "Splash layer must be hidden after sequence completes"
        assert win.dashboard_layer.isVisible(), "Dashboard layer must be visible"
        assert win.dash_opacity.opacity() == 1.0, "Dashboard must be fully opaque"
        print("  -> Step 3 (1500ms): Smooth transition complete, dashboard fully active.")

        win.close()
        for _ in range(10):
            time.sleep(0.02)
            app.processEvents()

    print("\n" + "=" * 80)
    print("ALL 5 STARTUP SEQUENCES PASSED FLAWLESSLY WITH ZERO ISSUES!")
    print("=" * 80)

if __name__ == "__main__":
    test_startup()
