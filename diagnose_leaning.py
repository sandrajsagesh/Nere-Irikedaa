"""
Live diagnostic script to measure real leaning metrics.
"""
import time
import math
from camera import CameraWorker
from vision import VisionDetector
from geometry import angle_with_horizontal_deg

def test_lean():
    cam = CameraWorker(camera_index=0)
    if not cam.start():
        print("Camera start failed")
        return
    detector = VisionDetector()
    start_t = time.time()
    
    print("=" * 70)
    print("LEAN DIAGNOSTIC (Running for 8 seconds)")
    print("Alternate: UPRIGHT -> LEAN LEFT -> LEAN RIGHT")
    print("=" * 70)
    
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
            offset_x = (bundle.head_center[0] - bundle.shoulder_center[0]) / sh_dist
            
            # Shoulder tilt
            sh_tilt = angle_with_horizontal_deg(
                (bundle.left_shoulder[0], bundle.left_shoulder[1]),
                (bundle.right_shoulder[0], bundle.right_shoulder[1]),
            )
            
            # Shoulder center x in frame
            sh_cx = bundle.shoulder_center[0]
            
            # Hip center if available
            hip_angle = 0.0
            if bundle.hip_center:
                dx = bundle.shoulder_center[0] - bundle.hip_center[0]
                dy = bundle.shoulder_center[1] - bundle.hip_center[1]
                hip_angle = math.degrees(math.atan2(dx, -dy))
                
            print(f"[{time.time()-start_t:4.1f}s] "
                  f"Offset_X: {offset_x:+5.2f} | "
                  f"Sh_Tilt: {sh_tilt:+5.1f}° | "
                  f"Sh_Cx: {sh_cx:5.3f} | "
                  f"Hip_Angle: {hip_angle:+5.1f}°")
                  
        time.sleep(0.02)
        
    cam.stop()
    detector.close()

if __name__ == "__main__":
    test_lean()
