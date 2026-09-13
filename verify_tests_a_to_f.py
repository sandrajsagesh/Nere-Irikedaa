"""
Comprehensive automated validation of Stabilization Requirements: TEST A through TEST F.
"""
import sys
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from config import AppMode, PostureState, load_saved_mode, save_mode
from main import PostureGlassApp

def run_stabilization_suite():
    print("=" * 80)
    print("RUNNING STABILIZATION SUITE (TESTS A - F)")
    print("=" * 80)

    # -------------------------------------------------------------
    # TEST A: Launch with explicit Useful mode
    # -------------------------------------------------------------
    print("\n[TEST A] Run with --mode useful")
    app_a = PostureGlassApp(mode=AppMode.USEFUL, show_debug=False)
    app_a.main_window.play_opening_animation()
    for _ in range(25):
        time.sleep(0.02)
        app_a.qt_app.processEvents()

    assert app_a.mode == AppMode.USEFUL, f"Mode should be USEFUL, got {app_a.mode}"
    assert app_a.main_window.current_mode == AppMode.USEFUL, "MainWindow should be USEFUL"
    assert "USEFUL" in app_a.main_window.app_glyph.text(), f"Title badge should say USEFUL, got {app_a.main_window.app_glyph.text()}"
    assert app_a.main_window.toggle.thumb_progress < 0.1, "Toggle thumb should be on USEFUL (left)"
    assert "Actually trying to help" in app_a.main_window.lbl_mode_title.text()
    print("  [PASS] TEST A: Main UI says USEFUL, toggle is at Useful position, initial mode is USEFUL.")
    app_a.stop()
    for _ in range(15):
        time.sleep(0.02)
        app_a.qt_app.processEvents()

    # -------------------------------------------------------------
    # TEST B: Launch with explicit Useless mode
    # -------------------------------------------------------------
    print("\n[TEST B] Run with --mode useless")
    app_b = PostureGlassApp(mode=AppMode.USELESS, show_debug=False)
    app_b.main_window.play_opening_animation()
    for _ in range(25):
        time.sleep(0.02)
        app_b.qt_app.processEvents()

    assert app_b.mode == AppMode.USELESS, f"Mode should be USELESS, got {app_b.mode}"
    assert app_b.main_window.current_mode == AppMode.USELESS, "MainWindow should be USELESS"
    assert "USELESS" in app_b.main_window.app_glyph.text(), f"Title badge should say USELESS, got {app_b.main_window.app_glyph.text()}"
    assert app_b.main_window.toggle.thumb_progress > 0.9, "Toggle thumb should be on USELESS (right)"
    assert "Helping was never" in app_b.main_window.lbl_mode_title.text()
    print("  [PASS] TEST B: Main UI says USELESS, toggle is at Useless position, initial mode is USELESS.")
    app_b.stop()
    for _ in range(15):
        time.sleep(0.02)
        app_b.qt_app.processEvents()

    # -------------------------------------------------------------
    # TEST C & D: Toggle switching without restarting camera
    # -------------------------------------------------------------
    print("\n[TEST C & D] Toggle Useful -> Useless -> Useful without camera restart")
    app_c = PostureGlassApp(mode=AppMode.USEFUL, show_debug=False)
    app_c.main_window.play_opening_animation()
    cam_started = app_c.camera.start()
    app_c.main_window.set_camera_status(cam_started)
    for _ in range(20):
        time.sleep(0.02)
        app_c.qt_app.processEvents()

    initial_camera_obj = app_c.camera
    initial_cap = app_c.camera.cap
    initial_thread = app_c.camera._thread

    # TEST C: Toggle to USELESS
    print("  -> Toggling to USELESS...")
    app_c.main_window.toggle.set_mode(AppMode.USELESS)
    for _ in range(20):
        time.sleep(0.02)
        app_c.qt_app.processEvents()

    assert app_c.mode == AppMode.USELESS, "Mode must switch to USELESS"
    assert app_c.main_window.toggle.thumb_progress > 0.85, "Thumb must slide to right"
    assert "USELESS" in app_c.main_window.app_glyph.text()
    assert app_c.camera is initial_camera_obj, "Camera worker instance must NOT change"
    assert app_c.camera.cap is initial_cap, "Camera capture handle must NOT be reopened"
    assert app_c.camera._thread is initial_thread, "Camera thread must NOT be recreated"
    print("  [PASS] TEST C: Successfully toggled to USELESS. Pill slid right, runtime changed, camera NOT restarted.")

    # TEST D: Toggle back to USEFUL
    print("  -> Toggling back to USEFUL...")
    app_c.main_window.toggle.set_mode(AppMode.USEFUL)
    for _ in range(20):
        time.sleep(0.02)
        app_c.qt_app.processEvents()

    assert app_c.mode == AppMode.USEFUL, "Mode must switch back to USEFUL"
    assert app_c.main_window.toggle.thumb_progress < 0.15, "Thumb must slide back to left"
    assert "USEFUL" in app_c.main_window.app_glyph.text()
    assert app_c.camera.cap is initial_cap, "Camera capture handle must NOT be reopened"
    print("  [PASS] TEST D: Successfully toggled back to USEFUL. Pill slid left, runtime changed, camera NOT restarted.")

    # -------------------------------------------------------------
    # TEST E: Repeated Useless Mode Triggers (Stress Test / Zero Freeze)
    # -------------------------------------------------------------
    print("\n[TEST E] Repeated Useless Mode triggers stress test")
    app_c.set_mode(AppMode.USELESS)
    
    for cycle in range(1, 6):
        start_cycle_t = time.time()
        # Trigger Useless alert (good posture troll)
        app_c.overlay.trigger_warning(PostureState.GOOD, AppMode.USELESS)
        for _ in range(15):
            time.sleep(0.02)
            app_c.qt_app.processEvents()

        assert app_c.overlay.isVisible(), f"Overlay must be visible in cycle {cycle}"
        
        # Slouch / Clear
        app_c.overlay.clear_warning()
        for _ in range(20):
            time.sleep(0.02)
            app_c.qt_app.processEvents()

        assert not app_c.overlay.isVisible(), f"Overlay must be hidden in cycle {cycle}"
        elapsed = time.time() - start_cycle_t
        print(f"  -> Useless mode cycle {cycle}/5 completed in {elapsed:.2f}s (GUI completely responsive)")

    print("  [PASS] TEST E: Useless mode executed multiple alert-clear cycles with zero GUI freeze or stalls.")

    # -------------------------------------------------------------
    # TEST F: Clean Shutdown (Ctrl + Shift + Q / stop)
    # -------------------------------------------------------------
    print("\n[TEST F] Emergency Clean Shutdown")
    app_c.stop()
    for _ in range(15):
        time.sleep(0.02)
        app_c.qt_app.processEvents()

    assert not app_c.is_running, "is_running must be False"
    assert not app_c.camera._running, "Camera worker must be stopped"
    assert app_c.camera.cap is None, "Camera handle must be None"
    assert not app_c.main_window.isVisible(), "MainWindow must be closed"
    assert not app_c.overlay.isVisible(), "Overlay must be closed"
    print("  [PASS] TEST F: Complete clean shutdown executed. All resources safely released.")

    print("\n" + "=" * 80)
    print("ALL TESTS (TEST A THROUGH TEST F) PASSED WITH FLYING COLORS!")
    print("=" * 80)

if __name__ == "__main__":
    run_stabilization_suite()
