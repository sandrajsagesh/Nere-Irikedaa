"""
Thread-safe webcam capture worker for Useless 3.0 Posture Glass.
Runs camera capture in a background thread to prevent GUI lag and ensure latest-frame delivery.
"""
import threading
import time
from typing import Optional, Tuple
import cv2
import numpy as np

class CameraWorker:
    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480, fps: int = 30):
        self.camera_index = camera_index
        self.target_width = width
        self.target_height = height
        self.target_fps = fps
        
        self.cap: Optional[cv2.VideoCapture] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        self._latest_frame: Optional[np.ndarray] = None
        self._frame_time: float = 0.0
        self._fps_actual: float = 0.0
        self._frame_count: int = 0
        self._fps_timer: float = time.time()

    def start(self) -> bool:
        """Starts camera thread."""
        if self._running:
            return True
            
        # Try opening camera (try CAP_DSHOW on Windows, fallback to default)
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.camera_index)
            
        if not self.cap.isOpened():
            print(f"[CameraWorker] Failed to open camera {self.camera_index}. Trying index 1...")
            self.cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(1)
                
        if not self.cap.isOpened():
            print("[CameraWorker] Error: No camera could be opened.")
            return False

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.target_width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.target_height)
        self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
        
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        print("[CameraWorker] Camera capture thread started successfully.")
        return True

    def _capture_loop(self):
        while self._running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue
                
            # Flip horizontally for natural mirror feel
            frame = cv2.flip(frame, 1)
            
            with self._lock:
                self._latest_frame = frame
                self._frame_time = time.time()
                self._frame_count += 1
                
                # Update FPS every second
                now = time.time()
                if now - self._fps_timer >= 1.0:
                    self._fps_actual = self._frame_count / (now - self._fps_timer)
                    self._frame_count = 0
                    self._fps_timer = now
                    
            time.sleep(0.005) # Prevent 100% CPU thread starvation

    def get_frame(self) -> Tuple[bool, Optional[np.ndarray], float]:
        """
        Returns (has_frame, frame_bgr, fps_actual).
        Safe to call from any thread.
        """
        with self._lock:
            if self._latest_frame is not None:
                return True, self._latest_frame.copy(), self._fps_actual
            return False, None, 0.0

    def stop(self):
        """Stops thread and releases webcam."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()
            self.cap = None
        print("[CameraWorker] Camera released.")
