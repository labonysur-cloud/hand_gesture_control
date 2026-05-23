<div align="center">

<h1>🖐️ Hand Gesture Control for Windows</h1>

<p><strong>Control your entire Windows PC — mouse, drag & drop, volume, brightness, media, windows, apps, camera and more — using only your hand in front of a webcam. No extra hardware required.</strong></p>

<img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Version-2.0-FF6F00?style=for-the-badge"/>
<img src="https://img.shields.io/badge/MediaPipe-Tasks%20API-FF6F00?style=for-the-badge&logo=google&logoColor=white"/>
<img src="https://img.shields.io/badge/OpenCV-4.x-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white"/>
<img src="https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6?style=for-the-badge&logo=windows&logoColor=white"/>
<img src="https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge"/>

</div>

---

## 📌 Table of Contents

- [Overview](#-overview)
- [What's New in v2.0](#-whats-new-in-v20)
- [Features](#-features)
- [Full Gesture Reference](#-full-gesture-reference)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Running the Controller](#-running-the-controller)
- [Configuration](#-configuration-configjson)
- [How It Works — Technical Deep Dive](#-how-it-works--technical-deep-dive)
- [Troubleshooting](#-troubleshooting)
- [Roadmap](#-roadmap)
- [License](#-license)

---

## 🌟 Overview

**Hand Gesture Control for Windows** is a real-time, AI-powered application that turns your laptop webcam into a touchless input device. It uses Google's **MediaPipe Hand Landmarker** (Tasks API) to detect 21 3D key-points on your hand at up to 30 fps, then maps specific hand shapes and movements to Windows OS actions.

Design goals:
- **Reliable** — gestures require a sustained hold to prevent accidental activations
- **Responsive** — exponential cursor smoothing + angle-based finger detection
- **Comprehensive** — 20+ distinct gesture actions covering every day workflow
- **Configurable** — all tuning parameters in a single `config.json`
- **Private** — runs 100% offline on your CPU, no cloud calls, no drivers

---

## 🆕 What's New in v2.0

| Feature | Description |
|---|---|
| **Drag & Drop** | Pinch + move to drag files, windows, and UI elements |
| **Angle-based finger detection** | More accurate bent-finger detection using PIP joint angles |
| **Mute Toggle** | Pinky-only gesture instantly mutes/unmutes system audio |
| **Minimize Window** | Ring + Pinky gesture minimizes the active window |
| **Maximize / Restore** | Middle + Ring + Pinky maximizes or restores the active window |
| **Show Desktop** | Open palm swipe UP → Win+D |
| **Task View** | Thumb + Index + Pinky → Win+Tab |
| **Virtual Desktop Switch** | Open palm swipe DOWN → next virtual desktop |
| **Lock Screen** | Stationary open palm held for 1.2s → Win+L |
| **Pause / Resume ALL** | Hold a fist for 1.2s to freeze/unfreeze the entire controller |
| **Proportional Scrolling** | Scroll speed is proportional to how fast you move |
| **Screenshot via stability** | Two-finger peace sign: moving = scroll, stationary = screenshot |
| **`config.json`** | All sensitivity values in one file — no code editing needed |
| **Coloured skeleton overlay** | Each finger is drawn in its own colour, extended vs bent |
| **Mode badge** | Corner badge always shows current gesture mode |
| **Hold progress bar** | Yellow bar fills as you hold a launcher gesture |

---

## 🚀 Features

| Category | Capabilities |
|---|---|
| 🖱️ **Mouse** | Move, Left Click, Double Click, Right Click, **Drag & Drop** |
| 📜 **Scroll** | Proportional continuous scroll up / down |
| 🔊 **Volume** | Step up / step down |
| 🔇 **Mute** | Toggle mute with pinky gesture |
| ☀️ **Brightness** | Step up / step down (supported laptops) |
| ⏯️ **Media** | Play / Pause toggle |
| 🌐 **Browser** | Back / Forward navigation |
| 🖥️ **Window Management** | Minimize, Maximize/Restore, Show Desktop, Task View |
| 🗂️ **Virtual Desktops** | Switch to next virtual desktop |
| 🔒 **Lock Screen** | Lock Windows instantly |
| 📁 **File Explorer** | Open with thumbs-up |
| 🧮 **Calculator** | Open with three fingers |
| 📹 **Video Recording** | Start/stop recording from webcam — saved to `~/Pictures` |
| 📸 **Photo Capture** | OK sign → photo saved to `~/Pictures` |
| 🖼️ **Screenshot** | Peace sign (stationary) → screenshot saved to `~/Pictures` |
| ⏸️ **Pause Mode** | Hold fist to freeze all gestures when you need your hands free |

---

## 🤌 Full Gesture Reference

> **Hold gestures** require the pose held steady for **~0.6 s** (`HOLD_FRAMES = 18` frames).  
> A **yellow progress bar** appears at the bottom of the preview window while building up.

### 🖱️ Mouse & Navigation

| Gesture | Hand Shape | Action |
|---|---|---|
| **Move cursor** | ☝ Index finger only | Cursor follows fingertip smoothly |
| **Left click** | Pinch index + thumb | Quick pinch-release |
| **Double click** | Two fast pinches | Second pinch within 0.4 s |
| **Drag & Drop** | Pinch + move hand | Hold pinch and move to drag |
| **Drop** | Release pinch | Releases drag |
| **Right click** | Pinch middle + thumb | Single pinch |
| **Scroll** | ✌ Index + Middle, hand moving | Move hand up = scroll up |

### ⚙️ System Controls

| Gesture | Hand Shape | Action |
|---|---|---|
| **Volume** | 🤙 Shaka (Thumb + Pinky) | Move hand up = louder |
| **Brightness** | 4 fingers (thumb folded) | Move hand up = brighter |
| **Mute Toggle** | 🤙 Pinky only (hold ~0.6s) | Toggles system mute |

### 🖥️ Window Management

| Gesture | Hand Shape | Action |
|---|---|---|
| **Minimize** | Ring + Pinky only (hold) | Win + Down |
| **Maximize / Restore** | Middle + Ring + Pinky (hold) | Win + Up |
| **Show Desktop** | 🖐 Open palm, swipe UP | Win + D |
| **Task View** | Thumb + Index + Pinky (hold) | Win + Tab |
| **Next Virtual Desktop** | 🖐 Open palm, swipe DOWN | Ctrl + Win + Right |

### 🎬 Media & Browser

| Gesture | Hand Shape | Action |
|---|---|---|
| **Play / Pause** | ✊ Fist (hold ~0.6s) | Media play/pause key |
| **Browser Back** | 🖐 Open palm, swipe LEFT | Alt + Left |
| **Browser Forward** | 🖐 Open palm, swipe RIGHT | Alt + Right |

### 🚀 App Launchers & Utilities (Hold ~0.6s)

| Gesture | Hand Shape | Action |
|---|---|---|
| **File Explorer** | 👍 Thumb pointing UP | Opens Explorer |
| **Calculator** | Index + Middle + Ring | Opens Calc |
| **Record / Stop** | L-shape (thumb + index wide) | Toggles webcam recording |
| **Screenshot** | ✌ Peace sign, hand **still** | Saves PNG to `~/Pictures` |
| **Take Photo** | 👌 OK sign | Saves JPG to `~/Pictures` |
| **Lock Screen** | 🖐 Open palm, **held completely still** (1.2s) | Win + L |

### 🔧 System

| Gesture / Key | Action |
|---|---|
| **Hold Fist for 1.2s** | Pause / Resume ALL gestures |
| **Press `Q`** in preview window | Quit the controller cleanly |

---

## 🏗️ System Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│                     gesture_controller.py  v2.0                   │
│                                                                   │
│  ┌──────────────┐    ┌──────────────────┐    ┌────────────────┐  │
│  │  Webcam Feed │───▶│  MediaPipe Hand  │───▶│  Finger Status │  │
│  │  (OpenCV)    │    │  Landmarker      │    │  (angle-based) │  │
│  │  1280×720    │    │  21 3D keypoints │    └───────┬────────┘  │
│  └──────────────┘    └──────────────────┘            │           │
│                                                       ▼           │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                     Gesture Engine                         │  │
│  │                                                            │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │  Pinch   │  │  Swipe   │  │  Hold    │  │ Stable   │  │  │
│  │  │ Detector │  │ Detector │  │  Timer   │  │ Checker  │  │  │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │  │
│  └───────┼─────────────┼─────────────┼──────────────┼─────────┘  │
│          ▼             ▼             ▼              ▼             │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                   Action Dispatcher                       │    │
│  └────┬──────────┬──────────┬──────────┬──────────┬─────────┘    │
│       ▼          ▼          ▼          ▼          ▼              │
│  PyAutoGUI   WMI/SBC    OpenCV     Subprocess   Win32 Keys       │
│  (mouse,    (bright-  (photo,    (explorer,   (Win+D/L/Tab       │
│  keyboard,   ness)     video)     calc, etc)   Alt+Left etc)     │
│  screenshot)                                                      │
└───────────────────────────────────────────────────────────────────┘
```

---

## 🧰 Tech Stack

| Library | Purpose |
|---|---|
| `mediapipe 0.10.x` | AI hand landmark detection (21 3D points, Tasks API) |
| `opencv-python 4.x` | Webcam capture, frame processing, skeleton drawing, video writing |
| `pyautogui` | Mouse, keyboard, screenshot control |
| `screen-brightness-control` | Software brightness via WMI (Windows laptop displays) |
| `numpy` | Coordinate math |

**AI Model:** `hand_landmarker.task` (float16 ≈ 7.5 MB) — downloaded automatically on first run.

---

## 📁 Project Structure

```
hand_gesture_control/
│
├── gesture_controller.py   # Main application (v2.0)
├── config.json             # All tunable parameters
├── requirements.txt        # Python dependencies
├── .gitignore              # Excludes model, captured media, caches
├── LICENSE                 # MIT
└── README.md               # This file
```

> `hand_landmarker.task` is excluded from git (large binary). It auto-downloads on first run.

---

## ⚙️ Installation

### Prerequisites

| Requirement | Notes |
|---|---|
| **Python 3.11 / 3.12 / 3.13** | Tested on all three |
| **Webcam** | Built-in laptop webcam works perfectly |
| **Windows 10 / 11** | Required for Win32 shortcuts |
| **Git** | To clone the repo |

### Step 1 — Clone

```bash
git clone https://github.com/labonysur-cloud/hand_gesture_control.git
cd hand_gesture_control
```

### Step 2 — Virtual Environment (Recommended)

```bash
python -m venv venv
venv\Scripts\activate
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ Running the Controller

```bash
python gesture_controller.py
```

On **first run** the script downloads `hand_landmarker.task` (~7.5 MB) automatically — this is a one-time step.

A **camera preview window** titled `Hand Gesture Controller | Q = Quit` will open.  
Hold your hand in front of the camera to begin controlling your PC.  
Press **`Q`** inside the preview window to exit cleanly.

---

## 🎛️ Configuration (`config.json`)

All tuning is done in `config.json` — no code editing needed:

```jsonc
{
  "smoothening": 7,            // Cursor smoothing  (higher = smoother/slower)
  "click_distance": 35,        // Pinch threshold in pixels
  "double_click_window": 0.4,  // Seconds between two pinches → double click
  "action_cooldown": 1.8,      // Seconds between launcher gestures
  "scroll_sensitivity": 300,   // Scroll speed multiplier
  "volume_sensitivity": 0.035, // Hand travel per volume step
  "brightness_sensitivity": 0.04,
  "hold_frames": 18,           // Frames to hold a launcher pose (~0.6s @30fps)
  "drag_move_threshold": 2.0,  // Pixels moved to register as drag
  "swipe_threshold": 0.18,     // Horizontal swipe sensitivity (0–1)
  "swipe_vertical_threshold": 0.15,
  "webcam_width": 1280,
  "webcam_height": 720,
  "active_zone_margin": 0.15,  // Dead-zone margin around frame edge
  "camera_index": 0            // 0 = built-in webcam
}
```

---

## 🔬 How It Works — Technical Deep Dive

### 1. Hand Landmark Detection (MediaPipe Tasks API)

Uses the modern `HandLandmarker` Tasks API — compatible with Python 3.11+. Outputs **21 normalized 3D landmarks** `(x, y, z)` where values are in `[0.0, 1.0]` relative to the frame.

```
Key landmarks:
  0 = Wrist          4 = Thumb tip
  8 = Index tip     12 = Middle tip
 16 = Ring tip      20 = Pinky tip
  6 = Index PIP     10 = Middle PIP
```

### 2. Angle-Based Finger Detection

Each finger's bend is measured at the **PIP joint** using the angle between the tip, PIP, and MCP:

```python
angle = degrees( acos( dot(tip-pip, mcp-pip) / (|tip-pip| × |mcp-pip|) ) )
extended = angle > 155  # < 155° = bent finger
```

This is far more robust than simple Y-coordinate comparison, especially when the hand is tilted.

### 3. Exponential Cursor Smoothing

```python
clocX = plocX + (target_x - plocX) / SMOOTHENING
```

A smoothing factor of 7 removes ~85% of jitter per frame while maintaining sub-100ms response.

### 4. Drag & Drop

Mouse state machine:
- **Pinch down** → `pyautogui.mouseDown()`
- **Pinch held + hand moving** → `pyautogui.moveTo()` continuously
- **Pinch released** → `pyautogui.mouseUp()`

A `was_pinching` flag prevents repeated `mouseDown` calls during a sustained hold.

### 5. Stability Detector (Scroll vs Screenshot)

The same two-finger (Index + Middle) gesture triggers **scroll** when moving and **screenshot** when stationary:

```python
def hand_stable(positions, n=8, threshold=0.012):
    xs = [p[0] for p in positions[-n:]]
    ys = [p[1] for p in positions[-n:]]
    return max(xs)-min(xs) < threshold and max(ys)-min(ys) < threshold
```

### 6. Multi-Direction Swipe

The wrist position history (last 18 frames) is analyzed for dominant direction:
```
dx = positions[-1].x - positions[0].x
dy = positions[-1].y - positions[0].y
if |dx| > |dy|  → horizontal swipe (browser back/forward)
if |dy| > |dx|  → vertical swipe   (show desktop / virtual desktop)
```

### 7. Hold-to-Activate Timer

All app launchers require `HOLD_FRAMES` consecutive identical detections — preventing the single accidental-pose problem entirely. The hold count resets the instant the pose changes.

### 8. Pause Mode

A fist held for `HOLD_FRAMES × 2` frames toggles a global `is_paused` flag. While paused, all gesture processing is skipped; only the fist-hold is monitored to resume.

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| **`AttributeError: module 'mediapipe' has no attribute 'solutions'`** | MediaPipe 0.10+ dropped the old API. This project uses Tasks API — you're on the right version. |
| **Camera window doesn't open** | Close other apps using the webcam (Teams, Zoom, etc.) |
| **File Explorer keeps opening** | The thumb must point **clearly upward**. The strict angle check (`lm[4].y < lm[3].y - 0.05`) prevents accidental triggers. |
| **Cursor is too jittery** | Increase `smoothening` in `config.json` (try 10–14) |
| **Gestures trigger too easily** | Increase `hold_frames` (try 25–30) and `action_cooldown` (try 2.5) |
| **Scroll too fast/slow** | Adjust `scroll_sensitivity` in `config.json` |
| **Brightness not working** | Only works on built-in laptop displays via WMI. External monitors typically don't support software brightness. |
| **Drag not working** | Ensure you hold the pinch for at least one frame before moving. |

---

## 🗺️ Roadmap

- [ ] Two-hand support (one hand mouse, other hand shortcuts)
- [ ] Zoom in/out with two-hand pinch
- [ ] Custom gesture-to-action mapping via `config.json`
- [ ] Linux support (X11/Wayland via `xdotool`)
- [ ] macOS support
- [ ] GUI configuration panel
- [ ] Hand gesture training for custom poses (MediaPipe GestureRecognizer)
- [ ] Multi-monitor cursor mapping
- [ ] Start Menu gesture

---

## 📄 License

This project is licensed under the **MIT License** — free to use, modify, and distribute.

---

<div align="center">

**Made with ❤️ | Powered by Google MediaPipe & OpenCV**

⭐ **Star this repo if you found it useful!**

</div>
