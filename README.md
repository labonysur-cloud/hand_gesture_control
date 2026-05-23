<div align="center">

<h1>🖐️ Hand Gesture Control for Windows</h1>

<p><strong>Control your entire Windows PC — mouse, volume, brightness, media, apps, camera, and more — using only your hand in front of a webcam. No hardware required.</strong></p>

<img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/MediaPipe-Tasks%20API-FF6F00?style=for-the-badge&logo=google&logoColor=white"/>
<img src="https://img.shields.io/badge/OpenCV-4.x-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white"/>
<img src="https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white"/>
<img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge"/>

</div>

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Gesture Reference Card](#-gesture-reference-card)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Running the Controller](#-running-the-controller)
- [How It Works — Technical Deep Dive](#-how-it-works--technical-deep-dive)
- [Tuning & Configuration](#-tuning--configuration)
- [Troubleshooting](#-troubleshooting)
- [Roadmap](#-roadmap)
- [License](#-license)

---

## 🌟 Overview

**Hand Gesture Control for Windows** is a real-time, AI-powered application that transforms your laptop webcam into a touchless input device. It uses Google's **MediaPipe Hand Landmarker** to detect and track 21 3D key-points on your hand at up to 30 fps, then intelligently maps specific hand shapes and movements to Windows OS actions.

The system is designed to be:
- **Reliable** – gesture triggers require a sustained hold to prevent accidental activations
- **Responsive** – mouse cursor movement uses exponential smoothing for jitter-free control
- **Intuitive** – gestures map naturally to their real-world counterparts (pinch to click, swipe to navigate)
- **Non-invasive** – runs entirely on your CPU with no cloud calls, no external hardware, no drivers

---

## 🚀 Features

| Category | Capabilities |
|---|---|
| 🖱️ **Mouse** | Move, Left Click, Double Click, Right Click |
| 📜 **Scrolling** | Continuous scroll up / down |
| 🔊 **Volume** | Step up / step down |
| ☀️ **Brightness** | Step up / step down (on supported laptops) |
| ⏯️ **Media** | Play / Pause toggle |
| 🌐 **Browser** | Back / Forward navigation |
| 📁 **File Explorer** | Launch with a thumbs-up |
| 🧮 **Calculator** | Launch with three fingers |
| 📹 **Video Recording** | Start & stop recording direct from webcam |
| 📸 **Photo Capture** | Snap a photo saved directly to `~/Pictures` |
| 🖼️ **Screenshot** | Full-screen screenshot saved to `~/Pictures` |

---

## 🤌 Gesture Reference Card

> **Hold gestures** (app launchers, photo, screenshot, record) require you to hold the pose steady for **~0.6 seconds**. A yellow progress bar appears at the bottom of the preview window.

### 🖱️ Mouse & Navigation

| Gesture | Shape | Action |
|---|---|---|
| **Index finger up** | ☝️ Only index extended | **Move cursor** (follows fingertip) |
| **Pinch** Index + Thumb | Touch index tip to thumb tip | **Left click** |
| **Double Pinch** | Two fast pinches | **Double click** (opens files/folders) |
| **Pinch** Middle + Thumb | Touch middle tip to thumb tip | **Right click** |
| **Two fingers up** | ✌️ Index + Middle up | **Scroll** (move hand up = scroll up) |

### ⚙️ System Controls

| Gesture | Shape | Action |
|---|---|---|
| **Shaka** sign | 🤙 Thumb + Pinky only | **Volume** (move hand up/down) |
| **Four fingers** | Index+Middle+Ring+Pinky, thumb folded | **Brightness** (move hand up/down) |

### 🎬 Media & Browser

| Gesture | Shape | Action |
|---|---|---|
| **Fist** | ✊ All fingers closed (hold ~0.6s) | **Play / Pause** media |
| **Open palm + swipe left** | 🖐 All 5 fingers, swipe left | **Browser Back** |
| **Open palm + swipe right** | 🖐 All 5 fingers, swipe right | **Browser Forward** |

### 🚀 App Launchers & Utilities (Hold ~0.6s)

| Gesture | Shape | Action |
|---|---|---|
| **Thumbs Up** | 👍 Fist with thumb pointing up | **Open File Explorer** |
| **Three fingers** | Index + Middle + Ring up | **Open Calculator** |
| **L-shape** | Thumb + Index spread wide (>90px) | **Start / Stop Video Recording** |
| **Peace sign** | ✌️ Index + Middle, thumb folded | **Take Screenshot** → `~/Pictures` |
| **OK sign** | 👌 Middle+Ring+Pinky up, thumb+index touch | **Take Photo** → `~/Pictures` |

### ⌨️ Other

| Key | Action |
|---|---|
| `Q` | Quit the controller |

---

## 🏗️ System Architecture

```
┌───────────────────────────────────────────────────────────┐
│                    gesture_controller.py                  │
│                                                           │
│  ┌─────────────┐    ┌──────────────────┐    ┌──────────┐ │
│  │  Webcam     │───▶│  MediaPipe Hand  │───▶│ Gesture  │ │
│  │  (OpenCV)   │    │  Landmarker      │    │ Engine   │ │
│  │  1280×720   │    │  21 3D keypoints │    │          │ │
│  └─────────────┘    └──────────────────┘    └────┬─────┘ │
│                                                   │       │
│         ┌─────────────────────────────────────────┤       │
│         │              Gesture Engine             │       │
│         │                                         │       │
│         │  ┌──────────┐  ┌──────────┐  ┌───────┐ │       │
│         │  │ Finger   │  │ Swipe    │  │ Hold  │ │       │
│         │  │ Status   │  │ Detector │  │ Timer │ │       │
│         │  └────┬─────┘  └────┬─────┘  └───┬───┘ │       │
│         └───────┼─────────────┼─────────────┼─────┘       │
│                 ▼             ▼             ▼             │
│         ┌───────────────────────────────────────┐         │
│         │            Action Dispatcher          │         │
│         └───┬───────┬────────┬────────┬─────────┘         │
│             ▼       ▼        ▼        ▼                   │
│        PyAutoGUI  WinAPI  OpenCV  Subprocess              │
│        (mouse,   (bright) (photo,  (explorer,             │
│        keyboard)          video)   calc, etc.)            │
└───────────────────────────────────────────────────────────┘
```

---

## 🧰 Tech Stack

| Library | Version | Purpose |
|---|---|---|
| `mediapipe` | 0.10.x | AI hand landmark detection (21 3D points per hand) |
| `opencv-python` | 4.x | Webcam capture, frame processing, skeleton overlay, video writing |
| `pyautogui` | latest | Mouse movement, keyboard simulation, screenshots |
| `screen-brightness-control` | latest | Software brightness control via WMI (Windows) |
| `numpy` | latest | Array operations for coordinate math |

**AI Model:** `hand_landmarker.task` (float16, ~7.5 MB) — downloaded automatically on first run from Google's MediaPipe model repository.

---

## 📁 Project Structure

```
hand_gesture_control/
│
├── gesture_controller.py   # Main application entry point
├── requirements.txt        # Python dependency list
├── .gitignore              # Excludes model file, captured media, caches
└── README.md               # This file
```

> **Note:** `hand_landmarker.task` is **not committed** (it is in `.gitignore`). It is downloaded automatically to the project directory on the first run.

---

## ⚙️ Installation

### Prerequisites

| Requirement | Notes |
|---|---|
| **Python 3.11 or 3.12** | Python 3.13 is supported. Tested on 3.11+. |
| **Webcam** | Built-in laptop webcam works perfectly. |
| **Windows 10 / 11** | Required for brightness & OS integrations. |
| **Git** | For cloning the repository. |

### Step 1 — Clone the Repository

```bash
git clone https://github.com/labonysur-cloud/hand_gesture_control.git
cd hand_gesture_control
```

### Step 2 — (Recommended) Create a Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

This installs: `opencv-python`, `mediapipe`, `pyautogui`, `numpy`, `screen-brightness-control`.

---

## ▶️ Running the Controller

```bash
python gesture_controller.py
```

**On the first run**, the script will automatically download `hand_landmarker.task` (~7.5 MB) from Google's servers. This happens only once.

A **camera preview window** will open titled `"Hand Gesture Controller"`. Hold your hand in front of the camera to start controlling your PC.

**Press `Q`** inside the preview window at any time to exit cleanly.

---

## 🔬 How It Works — Technical Deep Dive

### 1. Hand Landmark Detection (MediaPipe Tasks API)

The script uses the **MediaPipe Tasks API** (the modern, Python 3.11+ compatible API), not the deprecated `mp.solutions` API. The `HandLandmarker` model outputs **21 normalized 3D landmarks** per hand, where each coordinate `(x, y, z)` is normalized to `[0.0, 1.0]` relative to the frame dimensions.

```
Key Landmark Indices:
  0  = Wrist
  4  = Thumb tip
  8  = Index finger tip
  12 = Middle finger tip
  16 = Ring finger tip
  20 = Pinky tip
  17 = Pinky MCP (base knuckle)
```

### 2. Finger Status Detection (`get_finger_status`)

Each finger is independently classified as **up** or **down**:

- **Thumb:** Compares the Euclidean distance from the thumb tip (`#4`) to the pinky base (`#17`) against the distance from the thumb MCP (`#2`) to the pinky base (`#17`). If the tip is farther away, the thumb is extended.
- **Other fingers (Index, Middle, Ring, Pinky):** Compares the Y-coordinate of the tip landmark vs. the PIP (Proximal Interphalangeal) joint. Since Y increases downward, a tip `y < pip y` means the finger is pointing upward (extended).

### 3. Mouse Control & Exponential Smoothing

The active tracking zone is defined as the **central 70% of the frame** (15% margin on each side). The index fingertip position within this zone is linearly mapped to the full screen resolution.

Raw pixel positions are smoothed using exponential interpolation:
```python
clocX = plocX + (target_x - plocX) / SMOOTHENING
```
Where `SMOOTHENING = 7`. Higher values give smoother but slower cursor response.

### 4. Click Detection via Pinch Distance

A **left click** is triggered when the Euclidean pixel distance between the thumb tip (`#4`) and index tip (`#8`) falls below `CLICK_DIST = 35` pixels.

**Double-click** is detected by tracking the time between two successive pinch-down events. If the gap is less than `DOUBLE_CLICK_WINDOW = 0.4s`, a `doubleClick()` is fired instead.

A `was_pinching` boolean prevents repeated clicks from a single sustained pinch.

### 5. Swipe Detection for Browser Navigation

The last `MAX_POSITIONS = 15` wrist coordinates `(x, y)` are stored in a circular buffer. The horizontal displacement `Δx = positions[-1].x - positions[0].x` is computed. If `|Δx| > 0.18` (18% of frame width), a LEFT or RIGHT swipe is fired.

### 6. Hold-to-Activate Gesture Timer

To prevent accidental app launches, launcher gestures (File Explorer, Calculator, etc.) require the same pose to be held for `HOLD_FRAMES = 18` consecutive frames (≈ 0.6 seconds at 30 fps).

A real-time **yellow progress bar** is rendered at the bottom of the preview window while a hold gesture is building up, giving immediate visual feedback.

```python
gesture_hold_count += 1
if gesture_hold_count == HOLD_FRAMES:
    # Trigger action — fires exactly once per hold
```

### 7. Video Recording & Photo Capture

Since the gesture controller already holds exclusive access to the webcam, it uses **OpenCV's `VideoWriter`** to record directly from the same webcam feed — no need to open the Windows Camera app. Clean frames (without the skeleton overlay) are written to `~/Pictures` in AVI format.

### 8. HUD Overlay

A semi-transparent status banner is blended onto the frame using `cv2.addWeighted()` and displayed for a configurable duration, providing instant feedback without cluttering the view.

---

## 🎛️ Tuning & Configuration

All tunable parameters are at the top of `gesture_controller.py`:

```python
SMOOTHENING         = 7      # Mouse smoothing (higher = smoother/slower)
CLICK_DIST          = 35     # Pinch distance threshold (pixels)
DOUBLE_CLICK_WINDOW = 0.4    # Seconds between two pinches for double-click
ACTION_COOLDOWN     = 1.8    # Seconds between app launches
SCROLL_SENSITIVITY  = 3      # Scroll speed multiplier
VOLUME_SENSITIVITY  = 0.04   # Hand movement required per volume step
HOLD_FRAMES         = 18     # Frames to hold a launcher pose (~0.6s @30fps)
```

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| **`AttributeError: module 'mediapipe' has no attribute 'solutions'`** | You are using MediaPipe 0.10+. This project uses the modern Tasks API — ensure you are running the latest `gesture_controller.py`. |
| **Webcam window does not open** | Another application (Teams, Zoom, etc.) may be using the camera. Close them and retry. |
| **File Explorer keeps opening randomly** | The "Thumbs Up" detection is strict — your thumb tip must point clearly upward. Try making the gesture more deliberate. |
| **Brightness control not working** | Some external monitors cannot be software-controlled via WMI. Works best on built-in laptop displays. |
| **Cursor is too jittery** | Increase `SMOOTHENING` from `7` to `10` or `12`. |
| **Gestures trigger too easily** | Increase `HOLD_FRAMES` (e.g., from `18` to `25`) and `ACTION_COOLDOWN` (e.g., from `1.8` to `2.5`). |
| **UnicodeEncodeError in terminal** | The script sets UTF-8 stdout automatically. If issues persist, run: `set PYTHONIOENCODING=utf-8` before launching. |

---

## 🗺️ Roadmap

- [ ] GUI configuration panel for gesture sensitivity
- [ ] Custom gesture-to-action mapping (user-defined)
- [ ] Two-hand support (one hand mouse, other hand shortcuts)
- [ ] Zoom in/out with pinch gesture (two-handed)
- [ ] Drag-and-drop support
- [ ] Support for Linux (X11/Wayland)
- [ ] Multi-monitor cursor mapping

---

## 📄 License

This project is licensed under the **MIT License** — free to use, modify, and distribute.

---

<div align="center">

**Made with ❤️ | Powered by Google MediaPipe & OpenCV**

⭐ Star this repo if you found it useful!

</div>
