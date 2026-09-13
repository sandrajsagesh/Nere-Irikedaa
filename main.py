"""
Useless 3.0 — Posture Glass
Main application entry point. Coordinates webcam capture, computer vision,
posture classification engine, PyQt6 glass overlay, system tray, and debug HUD.
Features:
- Single authoritative AppMode with strict precedence:
  Explicit CLI flag > Saved user preference > Default (Useful)
- 100% thread-safe signal bridge for background tray & worker threads
- Instant mode switching with zero camera or posture engine reinitialization
- Non-blocking GUI event loop and orderly clean shutdown on Ctrl+Shift+Q
"""
import argparse
import sys
import threading
import time
from typing import Optional
import cv2
import numpy as np

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from config import (
    AppMode,
    PostureState,
    Sensitivity,
    USELESS_MODE_TRIGGER_SEC,
    load_saved_mode,
    save_mode,
)
from camera import CameraWorker
from vision import VisionDetector, LandmarkBundle
from posture_engine import PostureEngine, PostureEvaluation
from overlay import ScreenBlurOverlay
from debug_window import DebugVisualizer
from tray import SystemTrayManager
from app_window import MainWindow


class AppBridge(QObject):
    """Thread-safe signal dispatcher marshaling background events to the Qt main thread."""
    request_set_mode = pyqtSignal(object)
    request_show_window = pyqtSignal()
    request_stop = pyqtSignal()
    camera_ready = pyqtSignal(bool)
    request_warning = pyqtSignal(object, object)
    request_clear_warning = pyqtSignal()


class PostureGlassApp:
    def __init__(self, mode: Optional[AppMode] = None, show_debug: bool = False, camera_idx: int = 0):
        # 1. Authoritative Mode Initialization:
        # Precedence: Explicit CLI parameter > saved user preference > default (USEFUL)
        if mode is not None:
            self.mode = mode
            save_mode(mode)
        else:
            self.mode = load_saved_mode()

        self.show_debug = show_debug
        self.camera_idx = camera_idx
        self.is_monitoring = True
        self.is_running = True

        # 2. Thread-safe Qt Application & Signal Bridge
        self.qt_app = QApplication.instance() or QApplication(sys.argv)
        self.bridge = AppBridge()
        self.bridge.request_set_mode.connect(self._do_set_mode)
        self.bridge.request_show_window.connect(self._do_show_window)
        self.bridge.request_stop.connect(self._do_stop)
        self.bridge.camera_ready.connect(self._on_camera_ready)
        self.bridge.request_warning.connect(self._do_trigger_warning)
        self.bridge.request_clear_warning.connect(self._do_clear_warning)

        # 3. Core Vision & Posture Engine
        self.camera = CameraWorker(camera_index=self.camera_idx)
        self.vision = VisionDetector()
        self.engine = PostureEngine(Sensitivity.NORMAL)
        self.visualizer = DebugVisualizer()

        # 4. Windows & Overlay
        self.overlay = ScreenBlurOverlay()
        self.main_window = MainWindow(initial_mode=self.mode)

        # Wire Main Window Signals (fast, zero pipeline restart)
        self.main_window.mode_changed.connect(self.set_mode)
        self.main_window.retry_camera_requested.connect(self.retry_camera)
        self.main_window.quit_requested.connect(self.stop)

        # 5. System tray & global emergency hotkey (Ctrl + Shift + Q)
        self.tray = SystemTrayManager(
            on_toggle_mode=self.set_mode,
            on_toggle_monitoring=self.set_monitoring,
            on_toggle_debug=self.toggle_debug,
            on_change_sensitivity=self.set_sensitivity,
            on_exit=self.stop,
            on_show_window=self.show_main_window,
        )
        self.tray.current_mode = self.mode

        # State tracking for Useless mode comedy
        self.useless_good_start_time: float = 0.0
        self.useless_active = False

        # Background processing thread
        self.proc_thread: Optional[threading.Thread] = None

    def show_main_window(self):
        """Thread-safe request to restore and activate main window."""
        if threading.current_thread() is threading.main_thread():
            self._do_show_window()
        else:
            self.bridge.request_show_window.emit()

    def _do_show_window(self):
        self.main_window.showNormal()
        self.main_window.activateWindow()

    def _do_trigger_warning(self, state: PostureState, mode: AppMode):
        """Dispatched safely to the Qt GUI main thread."""
        self.overlay.trigger_warning(state, mode)

    def _do_clear_warning(self):
        """Dispatched safely to the Qt GUI main thread."""
        self.overlay.clear_warning()

    def set_mode(self, mode: AppMode):
        """Thread-safe request to switch active mode without restarting camera or detector."""
        if threading.current_thread() is threading.main_thread():
            self._do_set_mode(mode)
        else:
            self.bridge.request_set_mode.emit(mode)

    def _do_set_mode(self, mode: AppMode):
        print(f"[App] Mode switched to: {mode.value.upper()}")
        self.mode = mode
        save_mode(mode)  # Persist selection immediately
        self.overlay.clear_warning()
        self.useless_active = False
        self.useless_good_start_time = 0.0
        self.main_window.set_mode(mode)
        self.tray.current_mode = mode

    def set_monitoring(self, enabled: bool):
        print(f"[App] Monitoring {'Resumed' if enabled else 'Paused'}")
        self.is_monitoring = enabled
        if not enabled:
            self.overlay.clear_warning()

    def toggle_debug(self):
        self.show_debug = not self.show_debug
        if not self.show_debug:
            self.visualizer.close()
        print(f"[App] Debug HUD: {'ON' if self.show_debug else 'OFF'}")

    def set_sensitivity(self, sens: Sensitivity):
        print(f"[App] Sensitivity set to: {sens.value.upper()}")
        self.engine.set_sensitivity(sens)

    def retry_camera(self):
        """Attempts to reconnect to webcam on demand without restarting the app."""
        print("[App] Attempting camera reconnection...")
        if self.camera.start():
            print("[App] Camera connected successfully!")
            self.main_window.set_camera_status(True)
            if not self.proc_thread or not self.proc_thread.is_alive():
                self.proc_thread = threading.Thread(target=self._processing_loop, daemon=True)
                self.proc_thread.start()
        else:
            print("[App] Camera connection retry failed.")
            self.main_window.set_camera_status(False, "Camera not found. Retry?")

    def start(self):
        print("=" * 60)
        print("  NERE IRIKEDAA — USELESS 3.0")
        print("  Computer Vision Upper-Body Posture Engine")
        print(f"  Active Mode: {self.mode.value.upper()}")
        print("  Emergency Exit: Press Ctrl + Shift + Q at any time")
        print("=" * 60)

        # 1. Start system tray in background (registers Ctrl+Shift+Q emergency hotkey immediately)
        self.tray.start()

        # 2. Launch Startup Intro Animation for Main Desktop Window
        self.main_window.play_opening_animation()

        # 3. Asynchronously start camera so startup intro animation is never blocked or delayed
        threading.Thread(target=self._async_start_camera, daemon=True).start()

        # 4. Run Qt Event Loop on main thread immediately
        try:
            self.qt_app.exec()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def _async_start_camera(self):
        """Initializes camera worker asynchronously so the UI event loop and startup intro remain fluid."""
        camera_ok = self.camera.start()
        self.bridge.camera_ready.emit(camera_ok)

    def _on_camera_ready(self, camera_ok: bool):
        self.main_window.set_camera_status(camera_ok)
        if camera_ok:
            if not self.proc_thread or not self.proc_thread.is_alive():
                self.proc_thread = threading.Thread(target=self._processing_loop, daemon=True)
                self.proc_thread.start()
        else:
            print("[App] Notice: Camera currently unavailable. Click [Retry] in the UI once connected.")

    def _processing_loop(self):
        """Dedicated background loop for computer vision and posture analysis."""
        current_warning_state = None

        while self.is_running:
            if not self.is_monitoring:
                time.sleep(0.1)
                continue

            has_frame, frame, fps = self.camera.get_frame()
            if not has_frame or frame is None:
                time.sleep(0.01)
                continue

            # 1. Computer Vision detection
            bundle = self.vision.process_frame(frame)

            # 2. Posture classification & hysteresis
            evaluation = self.engine.process(bundle)
            now = time.time()

            # 3. Useful vs Useless Mode Logic
            if self.mode == AppMode.USEFUL:
                # Useful mode: warn on sustained bad posture
                is_bad_posture = (
                    evaluation.warning_active
                    and evaluation.state not in (PostureState.GOOD, PostureState.UNKNOWN)
                )
                if is_bad_posture:
                    if current_warning_state != evaluation.state:
                        print(f"[UsefulDebug] alert condition satisfied: {evaluation.state.value}")
                        self.bridge.request_warning.emit(evaluation.state, self.mode)
                        current_warning_state = evaluation.state
                else:
                    if current_warning_state is not None:
                        print(f"[UsefulDebug] alert cleared (recovered to {evaluation.state.value})")
                        self.bridge.request_clear_warning.emit()
                        current_warning_state = None

            elif self.mode == AppMode.USELESS:
                # Useless mode: Blurs screen when posture is GOOD!
                # If user slouches, the screen clears!
                if evaluation.raw_state == PostureState.GOOD and bundle is not None and bundle.is_valid:
                    if self.useless_good_start_time == 0.0:
                        self.useless_good_start_time = now
                    elif (now - self.useless_good_start_time) >= USELESS_MODE_TRIGGER_SEC:
                        if not self.useless_active:
                            self.bridge.request_warning.emit(PostureState.GOOD, self.mode)
                            self.useless_active = True
                else:
                    self.useless_good_start_time = 0.0
                    if self.useless_active:
                        self.bridge.request_clear_warning.emit()
                        self.useless_active = False

            # 4. Debug HUD rendering
            if self.show_debug:
                debug_canvas = self.visualizer.render(frame, bundle, evaluation, self.mode, fps)
                self.visualizer.show(debug_canvas)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    self.stop()
                    break
                elif key == ord('m'):
                    new_mode = AppMode.USELESS if self.mode == AppMode.USEFUL else AppMode.USEFUL
                    self.set_mode(new_mode)
                elif key == ord('d'):
                    self.toggle_debug()

            time.sleep(0.01)

    def stop(self):
        """Thread-safe request to perform orderly shutdown."""
        if not self.is_running:
            return
        if threading.current_thread() is threading.main_thread():
            self._do_stop()
        else:
            self.bridge.request_stop.emit()

    def _do_stop(self):
        """Orderly shutdown releasing all resources safely."""
        if not self.is_running:
            return
        self.is_running = False
        print("\n[App] Shutting down Posture Glass...")

        # 1. Release UI windows
        try:
            self.main_window.close()
        except Exception:
            pass
        try:
            self.visualizer.close()
        except Exception:
            pass
        try:
            self.overlay.clear_warning()
            self.overlay.close()
        except Exception:
            pass

        # 2. Release hardware & background workers
        try:
            self.camera.stop()
        except Exception:
            pass
        try:
            self.vision.close()
        except Exception:
            pass
        try:
            self.tray.stop()
        except Exception:
            pass

        # 3. Quit Qt Application
        try:
            self.qt_app.quit()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="Useless 3.0 — Posture Glass")
    parser.add_argument("--debug", action="store_true", help="Start with developer debug HUD window")
    parser.add_argument("--mode", choices=["useful", "useless"], default=None, help="Initial mode (useful | useless)")
    parser.add_argument("--camera", type=int, default=0, help="Camera device index")
    args = parser.parse_args()

    mode = None
    if args.mode:
        mode = AppMode.USELESS if args.mode.lower() == "useless" else AppMode.USEFUL

    app = PostureGlassApp(mode=mode, show_debug=args.debug, camera_idx=args.camera)
    app.start()


if __name__ == "__main__":
    main()
