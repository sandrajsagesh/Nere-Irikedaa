"""
Live webcam verification test for Posture Glass.
Runs the camera and engine for 4 seconds, prints real-time metrics and evaluations.
"""
import time
from camera import CameraWorker
from vision import VisionDetector
from posture_engine import PostureEngine
from config import Sensitivity, PostureState

def test_live_webcam():
    print("=" * 60)
    print("Testing live webcam and posture pipeline for 4 seconds...")
    print("=" * 60)
    
    cam = CameraWorker(camera_index=0)
    if not cam.start():
        print("[FAIL] Could not start camera 0.")
        return False
        
    detector = VisionDetector()
    engine = PostureEngine(Sensitivity.NORMAL)
    
    start_time = time.time()
    frames_processed = 0
    states_observed = {}
    
    while time.time() - start_time < 4.0:
        has_frame, frame, fps = cam.get_frame()
        if not has_frame or frame is None:
            time.sleep(0.01)
            continue
            
        bundle = detector.process_frame(frame)
        evaluation = engine.process(bundle)
        frames_processed += 1
        
        st = evaluation.raw_state.value
        states_observed[st] = states_observed.get(st, 0) + 1
        
        if frames_processed % 15 == 0:
            m = evaluation.metrics
            print(f"[Frame {frames_processed}] State: {evaluation.state.value} | Raw: {evaluation.raw_state.value} | "
                  f"Pitch: {m.head_pitch_deg:+.1f}° | Roll: {m.head_roll_deg:+.1f}° | "
                  f"Recline: {m.torso_recline_deg:+.1f}° | OffsetX: {m.head_shoulder_offset_x:+.2f} | "
                  f"SlouchRatio: {m.slouch_ratio:.2f} | Conf: {evaluation.confidence*100:.1f}%")
                  
        time.sleep(0.02)
        
    cam.stop()
    detector.close()
    
    print("-" * 60)
    print(f"Total frames processed: {frames_processed}")
    print(f"Observed states distribution: {states_observed}")
    print("Live webcam posture verification completed successfully.")
    return True

if __name__ == "__main__":
    test_live_webcam()
