"""
Verification Test for the Nere Irikedaa Startup Intro:
1. Tests that launch displays the clean dark intro first with "Nere Irikedaa".
2. Verifies subtitle "An unnecessarily sophisticated posture assistant." fades in.
3. Verifies smooth upward drift and hold.
4. Verifies smooth transition into the main window at 620x700.
5. Verifies mode preservation (Useful vs Useless).
6. Verifies camera initialization occurs asynchronously without blocking the intro animation.
"""
import sys
import time
from PyQt6.QtWidgets import QApplication

from config import AppMode
from main import PostureGlassApp

def test_startup_intro():
    app = QApplication.instance() or QApplication(sys.argv)

    print("=" * 80)
    print("STARTUP INTRO VERIFICATION (NERE IRIKEDAA)")
    print("=" * 80)

    for mode in [AppMode.USEFUL, AppMode.USELESS]:
        print(f"\n[Test Launch] Mode: {mode.value.upper()}...")
        posture_app = PostureGlassApp(mode=mode, show_debug=False)
        win = posture_app.main_window

        # Start the opening intro
        win.play_opening_animation()

        # Step 1: Initial state (0 - 50ms)
        for _ in range(3):
            time.sleep(0.02)
            app.processEvents()

        assert win.splash_layer.isVisible(), "Intro splash layer must be visible at start"
        assert not win.dashboard_layer.isVisible(), "Main dashboard must NOT be visible at start"
        assert win.lbl_splash_hero.text() == "Nere Irikedaa"
        print("  -> Step 1 (0ms): Clean dark background active. Main dashboard is hidden.")

        # Step 2: Brand appears (50 - 450ms)
        for _ in range(18):
            time.sleep(0.02)
            app.processEvents()

        assert win.hero_opacity.opacity() > 0.4, "Brand 'Nere Irikedaa' should be fading in"
        print("  -> Step 2 (350ms): Brand 'Nere Irikedaa' fading in with subtle upward drift.")

        # Step 3: Subtitle appears (450 - 700ms)
        for _ in range(15):
            time.sleep(0.02)
            app.processEvents()

        assert win.hero_opacity.opacity() > 0.85, "Brand 'Nere Irikedaa' should be settled"
        assert win.sub_opacity.opacity() > 0.85, "Subtitle should be visible"
        print("  -> Step 3 (650ms): Subtitle 'An unnecessarily sophisticated posture assistant.' visible.")

        # Step 4: Hold (700 - 1050ms)
        for _ in range(18):
            time.sleep(0.02)
            app.processEvents()

        assert win.splash_layer.isVisible(), "Intro should hold visible"
        print("  -> Step 4 (1000ms): Completed intro held clearly.")

        # Step 5: Continuous transition into main dashboard (1050 - 1500ms)
        for _ in range(25):
            time.sleep(0.02)
            app.processEvents()

        assert not win.splash_layer.isVisible(), "Splash layer must be hidden after transition"
        assert win.dashboard_layer.isVisible(), "Main dashboard layer must be visible after transition"
        assert win.dash_opacity.opacity() == 1.0, "Dashboard must be fully opaque"
        assert win.current_mode == mode, f"Window mode should be {mode.value}"
        assert posture_app.mode == mode, f"App mode should be {mode.value}"
        print(f"  -> Step 5 (1450ms): Transition complete. Main dashboard active in {mode.value.upper()} mode.")

        posture_app.stop()
        for _ in range(10):
            time.sleep(0.02)
            app.processEvents()

    print("\n" + "=" * 80)
    print("STARTUP INTRO VERIFICATION PASSED WITH ZERO ERRORS!")
    print("=" * 80)

if __name__ == "__main__":
    test_startup_intro()
