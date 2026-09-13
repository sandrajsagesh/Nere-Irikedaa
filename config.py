"""
Configuration and constants for Useless 3.0 — Posture Glass
"""
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Paths (supports PyInstaller frozen execution and normal Python script execution)
if getattr(sys, "frozen", False):
    BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)).resolve()
    APP_DIR = Path(sys.executable).parent.resolve()
else:
    BASE_DIR = Path(__file__).parent.resolve()
    APP_DIR = BASE_DIR

ASSETS_DIR = BASE_DIR / "assets"
ASSETS_DIR.mkdir(exist_ok=True)

def _find_resource(filename: str) -> Path:
    """Finds resource file in bundle directory or next to executable."""
    p1 = BASE_DIR / filename
    if p1.exists():
        return p1
    p2 = APP_DIR / filename
    if p2.exists():
        return p2
    return p1

POSE_MODEL_PATH = _find_resource("pose_landmarker_lite.task")
FACE_MODEL_PATH = _find_resource("face_landmarker.task")

# Application Modes
class AppMode(str, Enum):
    USEFUL = "useful"
    USELESS = "useless"

SETTINGS_FILE = APP_DIR / "user_settings.json"

def load_saved_mode() -> AppMode:
    """Reads saved application mode from user_settings.json (defaults to USEFUL)."""
    try:
        if SETTINGS_FILE.exists():
            import json
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            saved = data.get("mode")
            if saved == "useless":
                return AppMode.USELESS
            elif saved == "useful":
                return AppMode.USEFUL
    except Exception as e:
        print(f"[Settings] Error loading saved mode: {e}")
    return AppMode.USEFUL

def save_mode(mode: AppMode):
    """Persists application mode to user_settings.json."""
    try:
        import json
        data = {"mode": mode.value}
        SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[Settings] Error saving mode: {e}")

# Posture States
class PostureState(str, Enum):
    GOOD = "GOOD"
    FORWARD_NECK = "FORWARD_NECK"
    SLOUCHING = "SLOUCHING"
    LEANING_LEFT = "LEANING_LEFT"
    LEANING_RIGHT = "LEANING_RIGHT"
    HEAD_TILT = "HEAD_TILT"
    RECLINED_BENT_NECK = "RECLINED_BENT_NECK"
    TOO_CLOSE = "TOO_CLOSE"
    UNKNOWN = "UNKNOWN"

# Display names for UI
POSTURE_DISPLAY_NAMES = {
    PostureState.GOOD: "Good Posture",
    PostureState.FORWARD_NECK: "Forward Neck",
    PostureState.SLOUCHING: "Slouching",
    PostureState.LEANING_LEFT: "Leaning Left",
    PostureState.LEANING_RIGHT: "Leaning Right",
    PostureState.HEAD_TILT: "Head Tilt",
    PostureState.RECLINED_BENT_NECK: "Reclined & Bent Neck",
    PostureState.TOO_CLOSE: "Too Close to Screen",
    PostureState.UNKNOWN: "Unknown / Low Visibility",
}

# Sensitivity settings
class Sensitivity(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"

@dataclass
class PostureThresholds:
    # Angles in degrees
    head_tilt_roll_deg: float = 16.0       # Clear head roll (normal sitting is < 10 deg)
    head_turn_yaw_deg: float = 30.0        # Head turn left/right
    head_pitch_down_deg: float = 18.0      # Forward head pitch (normal gaze down is 5-12 deg)
    head_pitch_up_deg: float = -18.0       # Looking way up
    shoulder_tilt_deg: float = 9.0         # Shoulders significantly unlevel
    
    # Offsets normalized relative to inter-shoulder distance (0.0 - 1.0)
    lean_lateral_offset: float = 0.22      # Obvious torso/head shift to left/right
    forward_neck_z_offset: float = 0.24    # Head protruding forward relative to shoulder plane
    slouch_compression_ratio: float = 0.76 # Head-to-shoulder vertical distance ratio drop
    
    # Recline & Flexion
    torso_recline_angle_deg: float = 16.0  # Torso tilted backwards
    neck_flexion_deg: float = 20.0         # Neck flexed forward relative to torso axis
    
    # Proximity
    proximity_face_ratio: float = 0.38     # Face bounding box width relative to frame width

# Threshold presets by sensitivity
THRESHOLDS_BY_SENSITIVITY = {
    Sensitivity.LOW: PostureThresholds(
        head_tilt_roll_deg=20.0,
        head_pitch_down_deg=22.0,
        shoulder_tilt_deg=12.0,
        lean_lateral_offset=0.28,
        forward_neck_z_offset=0.30,
        slouch_compression_ratio=0.70,
        torso_recline_angle_deg=20.0,
        neck_flexion_deg=25.0,
        proximity_face_ratio=0.45,
    ),
    Sensitivity.NORMAL: PostureThresholds(),
    Sensitivity.HIGH: PostureThresholds(
        head_tilt_roll_deg=13.0,
        head_pitch_down_deg=15.0,
        shoulder_tilt_deg=7.0,
        lean_lateral_offset=0.18,
        forward_neck_z_offset=0.20,
        slouch_compression_ratio=0.82,
        torso_recline_angle_deg=13.0,
        neck_flexion_deg=16.0,
        proximity_face_ratio=0.32,
    ),
}

# Temporal Filtering Constants (in seconds)
SUSTAINED_BAD_POSTURE_SEC = 2.0   # 2.0 seconds continuous bad posture before warning
STABLE_GOOD_POSTURE_SEC = 1.2     # 1.2 seconds stable good posture before clearing
USELESS_MODE_TRIGGER_SEC = 2.0    # 2.0 seconds stable good posture before comedic useless blur
SMOOTHING_ALPHA = 0.3             # Exponential Moving Average factor (0.1 = slow, 0.5 = fast)

# Comedy Dialogues for Useful Mode (Lists of (title, subtitle) per posture)
USEFUL_MESSAGES = {
    PostureState.FORWARD_NECK: [
        (
            "Bro, your head is entering the laptop.",
            "Pull your head back into your zip code."
        ),
        (
            "Your neck is trying to join the laptop.",
            "The screen is not going anywhere. You can stay back."
        ),
        (
            "Please stop negotiating with the display.",
            "Retract your chin. The pixels are fully visible from here."
        ),
    ],
    PostureState.SLOUCHING: [
        (
            "You're becoming a question mark.",
            "Sit up a little. Your spine has a family."
        ),
        (
            "Your spine has officially entered relaxation mode.",
            "Sit up. Your future self will appreciate it."
        ),
        (
            "That chair is winning the posture competition.",
            "Re-engage your back muscles before gravity takes over."
        ),
    ],
    PostureState.LEANING_LEFT: [
        (
            "Why are we sitting diagonally?",
            "The earth has gravity, but you don't need to yield to the left."
        ),
        (
            "Why are we slowly migrating to the left?",
            "The center of the screen is still over there."
        ),
        (
            "Left side detected.",
            "Gravity is real, but leaning this hard is completely optional."
        ),
    ],
    PostureState.LEANING_RIGHT: [
        (
            "The laptop isn't moving right.",
            "Come back to the center."
        ),
        (
            "You appear to be drifting right.",
            "The laptop hasn't moved. You have."
        ),
        (
            "Right-side expedition detected.",
            "Recenter your torso before you fall out of frame."
        ),
    ],
    PostureState.HEAD_TILT: [
        (
            "Your head has chosen a new angle.",
            "Straighten it out before your neck locks in."
        ),
        (
            "Your head appears to be installing at an angle.",
            "Please return your head to the default orientation."
        ),
        (
            "The screen is not sideways.",
            "Level your eyes with the horizon."
        ),
    ],
    PostureState.RECLINED_BENT_NECK: [
        (
            "Your body went back, but your neck didn't get the memo.",
            "Keep your neck more neutral or sit upright."
        ),
        (
            "Reclining AND leaning forward. Pick a strategy.",
            "Your chair is going backwards while your neck goes forwards."
        ),
        (
            "This posture has too many conflicting directions.",
            "Support your back or bring your screen closer."
        ),
    ],
    PostureState.TOO_CLOSE: [
        (
            "Bro, the screen isn't going anywhere.",
            "Move back a little. The pixels can breathe."
        ),
        (
            "The pixels are already visible from here.",
            "You don't need to physically enter the display."
        ),
        (
            "Personal space applies to laptops too.",
            "Back up a few inches to save your eyesight."
        ),
    ],
}

# Comedy Dialogues for Useless Mode (Triggered on GOOD posture!)
USELESS_MESSAGES = [
    (
        "POSTURE: ABSOLUTELY PERFECT.",
        "Unfortunately, this application is useless. Screen privileges revoked."
    ),
    (
        "10/10 Posture Detected.",
        "Because you sat so correctly, we have decided to blur your screen anyway."
    ),
    (
        "Ergonomic Royalty.",
        "Your posture is flawless. Therefore, you are banned from seeing your work."
    ),
    (
        "Congratulations on Good Posture!",
        "Now enjoy our frosted glass experience while you reflect on your life choices."
    ),
    (
        "Posture Score: 100%.",
        "Computer Vision working as intended. Productivity has been disabled."
    ),
    (
        "POSTURE: PERFECT.",
        "Application usefulness: highly questionable."
    ),
    (
        "Everything is fine.",
        "We still felt an intrusive intervention was necessary."
    ),
    (
        "Congratulations!",
        "You have successfully achieved absolutely nothing."
    ),
]
