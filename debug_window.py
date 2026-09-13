"""
Debug HUD and skeleton visualizer for Useless 3.0 — Posture Glass.
Renders real-time telemetry HUD and landmark skeletons using OpenCV.
Displays the exact measurements used by the classifier.
"""
from typing import Optional, Tuple
import cv2
import numpy as np

from config import PostureState, AppMode, POSTURE_DISPLAY_NAMES
from vision import LandmarkBundle
from posture_engine import PostureEvaluation

class DebugVisualizer:
    def __init__(self):
        self.window_name = "Useless 3.0 — Posture Glass [Debug HUD]"
        self._window_created = False

    def render(
        self,
        frame: np.ndarray,
        bundle: Optional[LandmarkBundle],
        evaluation: PostureEvaluation,
        app_mode: AppMode,
        fps: float,
    ) -> np.ndarray:
        """
        Draws landmarks, reference lines, and exact telemetry data on frame.
        """
        canvas = frame.copy()
        h, w, _ = canvas.shape
        
        # 1. Draw skeleton and landmarks if person detected
        if bundle is not None and bundle.is_valid:
            def to_px(pt_norm: Tuple[float, float, float]) -> Tuple[int, int]:
                return (int(pt_norm[0] * w), int(pt_norm[1] * h))
                
            p_nose = to_px(bundle.nose)
            p_leye = to_px(bundle.left_eye)
            p_reye = to_px(bundle.right_eye)
            p_lear = to_px(bundle.left_ear)
            p_rear = to_px(bundle.right_ear)
            p_head = to_px(bundle.head_center)
            
            p_lsh = to_px(bundle.left_shoulder)
            p_rsh = to_px(bundle.right_shoulder)
            p_sh_c = to_px(bundle.shoulder_center)
            
            # Draw shoulder line
            cv2.line(canvas, p_lsh, p_rsh, (255, 200, 50), 3)
            # Draw neck vector (head center to shoulder center)
            cv2.line(canvas, p_sh_c, p_head, (50, 220, 255), 2)
            # Draw eye line
            cv2.line(canvas, p_leye, p_reye, (255, 100, 200), 2)
            
            # Draw points
            for pt, color in [
                (p_nose, (0, 0, 255)),
                (p_leye, (255, 0, 255)),
                (p_reye, (255, 0, 255)),
                (p_lear, (200, 150, 0)),
                (p_rear, (200, 150, 0)),
                (p_head, (0, 255, 255)),
                (p_lsh, (0, 255, 0)),
                (p_rsh, (0, 255, 0)),
                (p_sh_c, (0, 255, 128)),
            ]:
                cv2.circle(canvas, pt, 5, color, -1)
                
            # Hips & torso if visible
            if bundle.left_hip and bundle.right_hip and bundle.hip_center:
                p_lhip = to_px(bundle.left_hip)
                p_rhip = to_px(bundle.right_hip)
                p_hip_c = to_px(bundle.hip_center)
                cv2.line(canvas, p_lhip, p_rhip, (180, 180, 50), 2)
                cv2.line(canvas, p_sh_c, p_hip_c, (100, 255, 100), 2)
                cv2.circle(canvas, p_lhip, 4, (180, 180, 50), -1)
                cv2.circle(canvas, p_rhip, 4, (180, 180, 50), -1)
                cv2.circle(canvas, p_hip_c, 5, (100, 255, 100), -1)

        # 2. Draw HUD Overlay Panel (Semi-transparent dark card on the left)
        hud_w = 410
        hud_h = 405
        sub_img = canvas[10:10+hud_h, 10:10+hud_w]
        black_rect = np.zeros(sub_img.shape, dtype=np.uint8)
        # alpha blend
        res = cv2.addWeighted(sub_img, 0.30, black_rect, 0.70, 0)
        canvas[10:10+hud_h, 10:10+hud_w] = res
        cv2.rectangle(canvas, (10, 10), (10+hud_w, 10+hud_h), (80, 95, 120), 1)

        # 3. Determine state colors
        state = evaluation.state
        if state == PostureState.GOOD:
            state_color = (80, 230, 100) # Bright green
        elif state == PostureState.UNKNOWN:
            state_color = (180, 180, 180) # Gray
        else:
            state_color = (60, 90, 255) # Bright red/orange warning

        # Header
        cv2.putText(canvas, "USELESS 3.0 — POSTURE HUD", (22, 34),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
        
        mode_str = f"MODE: {app_mode.value.upper()}"
        mode_color = (255, 200, 0) if app_mode == AppMode.USEFUL else (0, 225, 255)
        cv2.putText(canvas, mode_str, (22, 58),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, mode_color, 1, cv2.LINE_AA)

        # State banner
        state_title = f"STATE: {state.value} (Raw: {evaluation.raw_state.value})"
        cv2.putText(canvas, state_title, (22, 88),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.58, state_color, 2, cv2.LINE_AA)
                    
        # Warning trigger status
        warn_status = "ALERT: ACTIVE (OVERLAY DISPLAYED)" if evaluation.warning_active else "ALERT: CLEAR (NORMAL)"
        warn_col = (60, 80, 255) if evaluation.warning_active else (130, 220, 130)
        cv2.putText(canvas, warn_status, (22, 112),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.44, warn_col, 1, cv2.LINE_AA)

        # Telemetry with Current Value, Good Range, and Bad Range
        m = evaluation.metrics
        lines = [
            f"Confidence:     {evaluation.confidence * 100:.1f}% [Valid: >45%]",
            "--- FORWARD NECK & HEAD BEND ---",
            f"Head Pitch:     {m.head_pitch_deg:+.1f} deg [Good: <14, Bad: >16.5]",
            f"Chin-Shoulder:  {m.chin_shoulder_ratio:.2f} [Good: >0.36, Bad: <0.33]",
            f"Head-Shoulder:  {m.head_shoulder_ratio:.2f} [Good: >0.75, Bad: <0.68]",
            "--- RECLINE & LATERAL LEAN ---",
            f"Torso Recline:  {m.torso_recline_deg:+.1f} deg [Good: <14, Bad: >16]",
            f"Neck Flexion:   {m.neck_flexion_deg:+.1f} deg [Good: <18, Bad: >20]",
            f"Head Lean X:    {m.head_shoulder_offset_x:+.2f} [Good: +-0.15, Bad: >0.22]",
            f"Shoulder Tilt:  {m.shoulder_tilt_deg:+.1f} deg [Good: <7, Bad: >9]",
            f"Slouch Ratio:   {m.slouch_ratio:.2f} [Good: >0.85, Bad: <0.76]",
            f"Camera FPS:     {fps:.1f}",
        ]

        y = 138
        for line in lines:
            is_sep = line.startswith("---")
            font_scale = 0.38 if is_sep else 0.40
            color = (130, 180, 220) if is_sep else (225, 230, 235)
            thickness = 1
            cv2.putText(canvas, line, (22, y),
                        cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness, cv2.LINE_AA)
            y += 21

        return canvas

    def show(self, canvas: np.ndarray):
        cv2.imshow(self.window_name, canvas)
        self._window_created = True

    def close(self):
        if self._window_created:
            try:
                cv2.destroyWindow(self.window_name)
            except Exception:
                pass
            self._window_created = False
