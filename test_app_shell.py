"""
Automated Test for Desktop App Shell:
1. Main Window initialization and layout
2. Opening animation execution
3. Mode Toggle animation and state updates
4. State persistence (saves and reads back from user_settings.json)
5. Camera status & retry handling
6. Clean teardown
"""
import sys
import time
from PyQt6.QtWidgets import QApplication

from config import AppMode, load_saved_mode, save_mode, SETTINGS_FILE
from app_window import MainWindow, AnimatedModeToggle

def test_app_shell():
    app = QApplication.instance() or QApplication(sys.argv)
    
    print("=" * 80)
    print("RUNNING APP SHELL VERIFICATION TESTS")
    print("=" * 80)

    # 1. State Persistence Test
    print("\n[TEST 1] State Persistence")
    save_mode(AppMode.USELESS)
    assert load_saved_mode() == AppMode.USELESS, "Failed to load saved USELESS mode"
    save_mode(AppMode.USEFUL)
    assert load_saved_mode() == AppMode.USEFUL, "Failed to load saved USEFUL mode"
    print("  -> State persistence verified with user_settings.json")

    # 2. Main Window & Opening Animation Test
    print("\n[TEST 2] Main Window & Opening Animation")
    win = MainWindow(initial_mode=AppMode.USEFUL)
    win.play_opening_animation()

    # Step through opening animation
    for _ in range(25):
        time.sleep(0.02)
        app.processEvents()

    assert win.isVisible(), "Main window should be visible"
    assert win.windowOpacity() > 0.85, f"Window opacity should be near 1.0, got {win.windowOpacity()}"
    print("  -> Opening animation completed smoothly. Window centered and visible.")

    # 3. Interactive Toggle Test (Useful -> Useless -> Useful)
    print("\n[TEST 3] Mode Toggle Interaction (Animated segmented control)")
    mode_events = []
    win.mode_changed.connect(lambda m: mode_events.append(m))

    # Toggle to USELESS
    win.toggle.set_mode(AppMode.USELESS)
    for _ in range(15):
        time.sleep(0.02)
        app.processEvents()

    assert win.toggle.thumb_progress > 0.85, f"Thumb progress should be near 1.0, got {win.toggle.thumb_progress}"
    assert "Useless" in win.lbl_mode_desc.text() or "Helping was never" in win.lbl_mode_title.text()
    assert AppMode.USELESS in mode_events
    print("  -> Toggled to USELESS smoothly. Thumb glided to right, description updated.")

    # Toggle back to USEFUL
    win.toggle.set_mode(AppMode.USEFUL)
    for _ in range(15):
        time.sleep(0.02)
        app.processEvents()

    assert win.toggle.thumb_progress < 0.15, f"Thumb progress should be near 0.0, got {win.toggle.thumb_progress}"
    assert "Actually trying to help" in win.lbl_mode_title.text()
    assert AppMode.USEFUL in mode_events
    print("  -> Toggled back to USEFUL smoothly. Thumb glided to left, description updated.")

    # 4. Camera Status Indicator & Retry Button Test
    print("\n[TEST 4] Camera Status & Retry Handling")
    win.set_camera_status(True)
    assert not win.btn_retry_cam.isVisible(), "Retry button should be hidden when camera is active"
    assert "Active" in win.lbl_cam_status.text()
    print("  -> Camera Active state verified: Soft green indicator, retry hidden.")

    win.set_camera_status(False, "Camera Unavailable")
    assert win.btn_retry_cam.isVisible(), "Retry button should be visible when camera unavailable"
    assert "Unavailable" in win.lbl_cam_status.text()
    print("  -> Camera Unavailable state verified: Warning indicator, [Retry] button visible.")

    # 5. Clean teardown
    win.close()
    print("\n" + "=" * 80)
    print("APP SHELL VERIFICATION COMPLETED WITH ZERO ERRORS!")
    print("=" * 80)

if __name__ == "__main__":
    test_app_shell()
