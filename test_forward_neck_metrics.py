"""
Forward Neck Multi-Metric Live Evaluator.
Computes:
1. Head pitch from ear-mid to nose angle
2. Chin-to-shoulder vertical distance ratio
3. Face vertical compression (forehead to chin ratio)
4. Head-to-shoulder offset Z (protrusion)
5. Combined Forward Neck Score
"""
import time
import math
from camera import CameraWorker
from vision import VisionDetector

def evaluate_metrics():
    cam = CameraWorker(camera_index=0)
    if not cam.start():
        print("Camera start failed")
        return

    detector = VisionDetector()
    start_t = time.time()
    
    print("=" * 80)
    print("LIVE FORWARD NECK MULTI-METRIC TEST (Running for 8 seconds)")
    print("=" * 80)
    
    frame_idx = 0
    while time.time() - start_t < 8.0:
        has_frame, frame, fps = cam.get_frame()
        if not has_frame or frame is None:
            time.sleep(0.01)
            continue
            
        bundle = detector.process_frame(frame)
        frame_idx += 1
        if bundle is not None and frame_idx % 6 == 0:
            sh_dist = max(bundle.inter_shoulder_dist, 0.1)
            
            # 1. Ear-mid to nose vector angle
            ear_mid_x = (bundle.left_ear[0] + bundle.right_ear[0]) * 0.5
            ear_mid_y = (bundle.left_ear[1] + bundle.right_ear[1]) * 0.5
            dy_nose_ear = bundle.nose[1] - ear_mid_y
            inter_ear = max(abs(bundle.left_ear[0] - bundle.right_ear[0]), 0.05)
            pitch_angle = math.degrees(math.atan2(dy_nose_ear, inter_ear))
            
            # 2. Chin to shoulder distance normalized by shoulder span
            chin_y = bundle.chin[1] if bundle.chin else bundle.nose[1]
            chin_sh_dist = (bundle.shoulder_center[1] - chin_y) / sh_dist
            
            # 3. Head center to shoulder distance normalized
            head_sh_dist = (bundle.shoulder_center[1] - bundle.head_center[1]) / sh_dist
            
            # 4. Z protrusion
            z_offset = (bundle.shoulder_center[2] - bundle.head_center[2]) / sh_dist
            
            # 5. Eye-to-chin distance vs inter-eye distance (face vertical compression)
            inter_eye = math.hypot(bundle.left_eye[0] - bundle.right_eye[0], bundle.left_eye[1] - bundle.right_eye[1]) + 1e-6
            eye_mid_y = (bundle.left_eye[1] + bundle.right_eye[1]) * 0.5
            face_h_ratio = abs(chin_y - eye_mid_y) / inter_eye

            print(f"[{time.time()-start_t:4.1f}s] "
                  f"PitchAng: {pitch_angle:+5.1f}° | "
                  f"Chin-Sh: {chin_sh_dist:5.2f} | "
                  f"Head-Sh: {head_sh_dist:5.2f} | "
                  f"Z-Offset: {z_offset:5.2f} | "
                  f"FaceH/Eye: {face_h_ratio:5.2f}")
                  
        time.sleep(0.02)
        
    cam.stop()
    detector.close()

if __name__ == "__main__":
    evaluate_metrics()
