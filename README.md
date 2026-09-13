# Nere Irikedaa

> **An unnecessarily sophisticated posture assistant.**

[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)](https://github.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Version](https://img.shields.io/badge/Version-3.0.5-00C781)](https://github.com)
[![License](https://img.shields.io/badge/License-Information%20Pending-lightgrey)](https://github.com)

**Nere Irikedaa** is a modern Windows desktop application that uses your webcam and real-time computer vision to track your sitting posture—and reacts accordingly. It combines helpful ergonomic habits with satirical feedback in a refined Windows-native experience.

---

## ✨ What is Nere Irikedaa?

Traditional posture reminders use subtle system notifications that are easily dismissed. Nere Irikedaa takes a bolder stance:

> *"Your camera understands your posture. Your screen pays the price."*

When your sitting posture degrades, Nere Irikedaa progressively blurs and dims your desktop display with a frosted Gaussian veil, floating a sharp, physical liquid-glass warning card with tailored commentary.

The application features two distinct operating modes:
- **Useful Mode**: An attentive ergonomic assistant. Sit upright and your display remains crystal clear; slouch or lean too long, and your desktop gently blurs until you correct your posture.
- **Useless Mode**: An intentionally satirical inversion. Sit with flawless posture, and the app blurs your screen, demanding that you slouch to clear it.

---

## 🎯 Features

- **Continuous Webcam Monitoring**: High-efficiency, non-blocking background frame capture via OpenCV.
- **8 Posture States Classified**: Real-time 3D vector geometry for slouching, leaning, neck craning, and more.
- **Instant Mode Switching**: Switch between **Useful** and **Useless** modes via a physics-based animated toggle.
- **Progressive Screen Blur & Dimming**: Smooth Gaussian background cross-dissolve with ambient lighting.
- **Floating Liquid-Glass HUD**: Translucent acrylic card with specular edge reflections and unblurred vector text.
- **Witty, Posture-Specific Dialogues**: Context-aware observations tailored to each specific posture breakdown.
- **Jitter-Resistant State Machine**: Rolling hysteresis window that prevents false triggers and smoothly handles transitions.
- **Compact Windows UI**: Refined 520×615px dark obsidian utility interface (`#0B0F17`) with fluid startup sequence.
- **System Tray & Hotkeys**: Full background monitoring with sensitivity selection and <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>Q</kbd> emergency exit.
- **Standalone Windows Installer**: Ready-to-run package (`Nere Irikedaa Setup.exe`) requiring zero external dependencies.

---

## 🧠 How It Works

```
Webcam Feed ──► [ CameraWorker (OpenCV) ]
                      │
                      ▼
            [ VisionDetector (MediaPipe Tasks) ]
            (pose_landmarker_lite + face_landmarker)
                      │
                      ▼
            [ PostureGeometry & Metrics ]
            (Head pitch/roll/yaw, neck flexion, slouch ratio)
                      │
                      ▼
            [ PostureEngine State Machine ]
            (EMA smoothing, 8-frame rolling debounce)
                      │
                      ▼
            [ Main App & ScreenBlurOverlay ]
            (Gaussian blur backdrop + LiquidGlassCard HUD)
```

1. **Capture & Inference**: Background thread captures frames and feeds them into MediaPipe Tasks Vision on CPU.
2. **Metric Extraction**: Computes normalized head angles, shoulder tilt, torso recline, and chin-to-shoulder compression.
3. **Temporal Debouncing**: Applies Exponential Moving Average (EMA) smoothing and an 8-frame majority vote filter.
4. **Overlay Presentation**: When an alert condition is met, the fullscreen overlay captures the desktop, renders frosted blur, and pulses the glass alert card.

---

## 🧍 Supported Posture States

| Posture State | Display Badge | Description |
| :--- | :--- | :--- |
| **`GOOD`** | `POSTURE PERFECT` | Natural, balanced upright sitting posture. |
| **`SLOUCHING`** | `SLOUCHING` | Vertical torso collapse and spine compression toward the desk. |
| **`FORWARD_NECK`** | `FORWARD NECK` | Forward or downward neck protrusion toward the display. |
| **`LEANING_LEFT`** | `LEANING LEFT` | Torso and head laterally tilted or shifted toward the left. |
| **`LEANING_RIGHT`** | `LEANING RIGHT` | Torso and head laterally tilted or shifted toward the right. |
| **`HEAD_TILT`** | `HEAD TILT` | Head roll angle exceeding ergonomic limits with upright torso. |
| **`RECLINED_BENT_NECK`** | `RECLINED & BENT NECK` | Torso reclined back into chair while neck flexes forward. |
| **`TOO_CLOSE`** | `TOO CLOSE TO SCREEN` | Face proximity ratio exceeding safe viewing distance. |
| **`UNKNOWN`** | `UNKNOWN / LOW VISIBILITY` | Subject absent or landmarks obstructed (never triggers alerts). |

---

## 🖥️ Useful Mode

- **Trigger**: Continuous bad posture sustained for **2.0 seconds** (`SUSTAINED_BAD_POSTURE_SEC`).
- **Direct Bad-to-Bad Transitions**: Shifting directly between bad postures (e.g. `LEANING_RIGHT` → `TOO_CLOSE`) updates the alert and comment within **~0.25 seconds** without needing to return to good posture first.
- **Recovery**: Holding upright posture for **1.2 seconds** (`STABLE_GOOD_POSTURE_SEC`) smoothly dismisses the overlay.
- **Manual Dismiss**: Pressing <kbd>Esc</kbd> clears any active alert immediately.

---

## 🌀 Useless Mode

- In **Useless Mode**, the logic is playfully inverted.
- If you maintain upright, ergonomic posture for **2.0 seconds**, the screen blurs and a card demands that you slouch.
- Slouching or leaning out of alignment immediately restores your screen.

---

## 🪟 User Interface

- **Compact Footprint**: 520 × 615 px centered window designed as an everyday utility.
- **Physical Mode Toggle**: Custom animated pill switch with smooth easing and color shifts.
- **Live Status Cards**: Real-time camera readiness, FPS readout, and sensitivity presets (Low, Normal, High).
- **Glass Aesthetic**: Frosted mica backdrop, subtle bevel reflections, and atmospheric dimming.

---

## 📦 Installation

### Windows Installer (Recommended for End Users)

1. Download **`Nere Irikedaa Setup.exe`**.
2. Run the installer (installs to your user profile; no administrator privileges required).
3. Launch from the **Desktop** or **Start Menu** shortcut.
4. No Python installation, compilers, or extra modules are required.

---

## 💻 Running From Source

### Prerequisites
- Windows 10 or 11 (64-bit)
- Python 3.10+ (tested on Python 3.14)
- Connected webcam

### Setup Steps
```powershell
# 1. Clone the repository
git clone https://github.com/your-username/nere-irikedaa.git
cd "nere-irikedaa"

# 2. Set up virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python main.py
```

### Command-Line Arguments
```powershell
python main.py --mode useful   # Launch in Useful Mode
python main.py --mode useless  # Launch in Useless Mode
python main.py --debug         # Launch with developer HUD window
python main.py --camera 0      # Set camera index (default: 0)
```

---

## 🏗️ Project Structure

```
Nere Irikeda 2.0/
├── assets/app_icon.ico          # Application & shortcut icon
├── face_landmarker.task         # MediaPipe Face Landmarker model
├── pose_landmarker_lite.task    # MediaPipe Pose Landmarker Lite model
├── app_window.py                # Main PyQt6 desktop application window
├── camera.py                    # Threaded OpenCV camera capture worker
├── config.py                    # Enums, thresholds, paths, and witty dialogues
├── geometry.py                  # 3D vector math and angle calculation
├── main.py                      # Application bootstrap and mode coordinator
├── overlay.py                   # Gaussian blur backdrop & LiquidGlassCard
├── posture_engine.py            # Temporal classification & rolling state machine
├── tray.py                      # System tray integration & emergency hotkey
├── vision.py                    # MediaPipe detector wrapper pipeline
├── requirements.txt             # Python dependencies
├── build_exe.bat                # PyInstaller packaging script
├── build_installer.bat          # Inno Setup installer compilation script
└── installer.iss                # Inno Setup configuration
```

---

## 🔧 Building the Windows Application

1. **Compile Standalone Executable**:
   ```cmd
   build_exe.bat
   ```
   Uses PyInstaller and `nere_irikedaa.spec` to bundle dependencies into `dist\Nere Irikedaa\`.

2. **Compile Windows Installer**:
   ```cmd
   build_installer.bat
   ```
   Uses Inno Setup 6 to compile `Nere Irikedaa Setup.exe`.

---

## 🧪 Testing

Run existing automated verification suites from PowerShell:

```powershell
# Verify all 10 bad posture state transitions & anti-spam
python test_bad_posture_transitions.py

# Verify Useful Mode stability, jitter resistance, and recovery
python verify_useful_stability.py

# Verify window bounds & layout constraints
python test_layout_bounds.py

# Stress-test mode toggle animations
python test_rapid_toggle.py

# Run live webcam pipeline verification (4s)
python verify_live.py
```

---

## 🔐 Privacy

- **100% Local Processing**: All inference runs on your local CPU via MediaPipe Lite models.
- **Zero Video Storage**: Video frames are processed in-memory to compute coordinate ratios and instantly discarded.
- **Zero Telemetry**: No network connections, analytics, or data transmission of any kind.

---

## ⚠️ Limitations

- **Webcam Approximation**: Posture evaluation relies on visible 2D/3D landmarks and estimates posture ergonomically; it is not a clinical spinal measurement.
- **Camera Angle**: Best results occur when your webcam is centered near eye or upper-torso level.
- **Lighting**: Strong backlighting or very dim environments can reduce landmark confidence.

---

## 🛠️ Tech Stack

- **Language**: Python 3.10+
- **Computer Vision**: Google MediaPipe Tasks Vision, OpenCV
- **Math**: NumPy
- **GUI Framework**: PyQt6
- **System Integration**: `pystray`, `keyboard`
- **Packaging**: PyInstaller, Inno Setup 6

---

## 🚀 Future Ideas

- [ ] Multi-monitor blur support
- [ ] User-adjustable sensitivity calibration wizard
- [ ] Daily posture statistics and session analytics
- [ ] Configurable Windows startup option

---

## 🤝 Contributing

Contributions, bug reports, and suggestions are welcome! Feel free to open an issue or submit a pull request.

---

## 📄 License

License information will be added.

---

## ❤️ Credits & Acknowledgements

- [Google MediaPipe](https://developers.google.com/mediapipe) for fast on-device landmarking models.
- [OpenCV](https://opencv.org/) for real-time video capture and frame processing.
- [PyQt](https://riverbankcomputing.com/software/pyqt/) for native Windows desktop GUI components.
- [Inno Setup](https://jrsoftware.org/isinfo.php) for the Windows installer generator.

---

⭐ **Nere Irikedaa is a posture assistant that takes sitting straight way too seriously.**
