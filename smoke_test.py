"""
Smoke test: Runs main application for 5 seconds to verify full runtime loop,
camera capture, posture engine inference, Qt event loop, and clean exit.
"""
import time
import sys
from PyQt6.QtCore import QTimer
from main import PostureGlassApp, AppMode

def run_smoke_test():
    print("[SmokeTest] Initializing PostureGlassApp...")
    app = PostureGlassApp(mode=AppMode.USEFUL, show_debug=False, camera_idx=0)
    
    # Schedule automated stop after 6 seconds
    def auto_stop():
        print("[SmokeTest] 6 seconds elapsed. Requesting graceful stop...")
        app.stop()

    QTimer.singleShot(6000, auto_stop)
    print("[SmokeTest] Starting app...")
    app.start()
    print("[SmokeTest] App exited cleanly!")

if __name__ == "__main__":
    run_smoke_test()
