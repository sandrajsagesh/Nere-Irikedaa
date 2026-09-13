"""
Diagnostic script: Inspects actual live MediaPipe landmark geometry
to diagnose forward neck metrics and head pitch.
"""
import time
import math
import numpy as np
from camera import CameraWorker
from vision import VisionDetector

def diagnose():
    print("=" * 70)
    print("Starting forward neck diagnostic for 6 seconds...")
    print("Please alternate between: UPRIGHT SITTING and BENDING NECK FORWARD/DOWN")
    print("=" * 70)

    cam = CameraWorker(camera_index=0)
    if not cam.start():
        print("Failed to start camera")
        return

    detector = VisionDetector()
    start_t = time.time()
    frame_idx = 0

    while time.time() - start_t < 6.0:
        has_frame, frame, fps = cam.get_frame()
        if not has_frame or frame is None:
            time.sleep(0.01)
            continue

        bundle = detector.process_frame(frame)
        frame_idx += 1
        if bundle is not None and frame_idx % 8 == 0:
            # 1. Ear to eye dy
            eye_mid_y = (bundle.left_eye[1] + bundle.right_eye[1]) * 0.5
            ear_mid_y = (bundle.left_ear[1] + bundle.right_ear[1]) * 0.5
            inter_eye = math.hypot(bundle.left_eye[0] - bundle.right_eye[0], bundle.left_eye[1] - bundle.right_eye[1]) + 1e-6
            ear_eye_dy = (ear_mid_y - eye_mid_y) / inter_eye

            # 2. Chin relative to nose and shoulders
            sh_dist = bundle.inter_shoulder_dist
            sh_y = bundle.shoulder_center[1]
            head_y = bundle.head_center[1]
            chin_y = bundle.chin[1] if bundle.chin else bundle.nose[1]
            
            # Chin to shoulder vertical distance (normalized by shoulder span)
            chin_to_sh_dy = (sh_y - chin_y) / sh_dist
            
            # Head to shoulder vertical distance (normalized)
            head_to_sh_dy = (sh_y - head_y) / sh_dist
            
            # Z depth: head relative to shoulder
            z_offset = (bundle.shoulder_center[2] - bundle.head_center[2]) / sh_dist

            # Face height vs face width (aspect compression)
            # Forehead/eye to chin distance
            face_h = abs(chin_y - eye_mid_y) / sh_dist

            print(f"[{time.time()-start_t:4.1f}s] "
                  f"EarEye_dy: {ear_eye_dy:+.3f} | "
                  f"Chin-Sh_dy: {chin_to_sh_dy:+.3f} | "
                  f"Head-Sh_dy: {head_to_sh_dy:+.3f} | "
                  f"Z-offset: {z_offset:+.3f} | "
                  f"FaceH: {face_h:+.3f}")

        time.sleep(0.03)

    cam.stop()
    detector.close()
    print("Diagnosis complete.")

if __name__ == "__main__":
    diagnose()
