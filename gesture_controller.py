import cv2
import io
import sys as _sys
# Force UTF-8 stdout so emoji in HUD strings never crash the terminal
_sys.stdout = io.TextIOWrapper(_sys.stdout.buffer, encoding='utf-8', errors='replace')
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import pyautogui
import math
import subprocess
import time
import os
import datetime
import sys

# ──────────────────────────────────────────────
# CONSTANTS & TUNING
# ──────────────────────────────────────────────
SMOOTHENING          = 7        # Higher = smoother but slower cursor
CLICK_DIST           = 35       # Pixels: thumb-index must be closer than this to click
DOUBLE_CLICK_WINDOW  = 0.4      # Seconds: two pinches within this = double click
ACTION_COOLDOWN      = 1.8      # Seconds between app-launch gestures
SCROLL_SENSITIVITY   = 3        # Pixels of scroll per detected movement unit
VOLUME_SENSITIVITY   = 0.04     # How much hand movement triggers a volume step
HOLD_FRAMES          = 18       # Number of consecutive frames a pose must be held
                                 # to trigger an app launcher (~0.6s at 30fps)

# ──────────────────────────────────────────────
# SCREEN & PYAUTOGUI SETUP
# ──────────────────────────────────────────────
pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0          # Remove built-in delay for snappier control
screen_w, screen_h = pyautogui.size()

# ──────────────────────────────────────────────
# OPTIONAL: BRIGHTNESS CONTROL
# ──────────────────────────────────────────────
try:
    import screen_brightness_control as sbc
    BRIGHTNESS_SUPPORTED = True
except Exception:
    BRIGHTNESS_SUPPORTED = False
    print("[INFO] screen_brightness_control not available – brightness gestures disabled.")

# ──────────────────────────────────────────────
# MEDIAPIPE SETUP (Tasks API – works on Python 3.11+)
# ──────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'hand_landmarker.task')
if not os.path.exists(MODEL_PATH):
    import urllib.request
    print("[INFO] Downloading hand_landmarker.task …")
    urllib.request.urlretrieve(
        'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',
        MODEL_PATH
    )

_base    = python.BaseOptions(model_asset_path=MODEL_PATH)
_options = vision.HandLandmarkerOptions(_base, num_hands=1,
                                         min_hand_detection_confidence=0.6,
                                         min_hand_presence_confidence=0.6,
                                         min_tracking_confidence=0.6)
detector = vision.HandLandmarker.create_from_options(_options)

# MediaPipe connections for drawing skeleton
HAND_CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (9,10),(10,11),(11,12),
    (13,14),(14,15),(15,16),
    (17,18),(18,19),(19,20),
    (0,17),(5,9),(9,13),(13,17)
]

# ──────────────────────────────────────────────
# STATE VARIABLES
# ──────────────────────────────────────────────
plocX, plocY        = 0, 0
clocX, clocY        = 0, 0

last_click_time     = 0
was_pinching_left   = False
was_pinching_right  = False
last_action_time    = 0

hand_positions      = []   # wrist (x,y) history for swipe detection
MAX_POSITIONS       = 15

is_recording        = False
video_writer        = None

# Gesture hold counter – prevents accidental app launches
gesture_hold_name   = None
gesture_hold_count  = 0

# HUD message
hud_text            = ""
hud_color           = (0, 255, 0)
hud_until           = 0

# ──────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────
def dist_px(p1, p2, fw, fh):
    return math.hypot((p1.x - p2.x) * fw, (p1.y - p2.y) * fh)

def get_finger_status(lm):
    """Returns (thumb, index, middle, ring, pinky) as booleans."""
    # Thumb: tip farther from pinky base than thumb MCP
    d_tip = math.hypot(lm[4].x - lm[17].x, lm[4].y - lm[17].y)
    d_mcp = math.hypot(lm[2].x - lm[17].x, lm[2].y - lm[17].y)
    thumb = d_tip > d_mcp

    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]
    others = [lm[t].y < lm[p].y for t, p in zip(tips, pips)]
    return (thumb, *others)

def detect_swipe(positions, threshold=0.18):
    if len(positions) < MAX_POSITIONS:
        return None
    dx = positions[-1][0] - positions[0][0]
    if   dx >  threshold: return "RIGHT"
    elif dx < -threshold: return "LEFT"
    return None

def draw_skeleton(img, lm):
    fh, fw = img.shape[:2]
    pts = [(int(p.x * fw), int(p.y * fh)) for p in lm]
    for a, b in HAND_CONNECTIONS:
        cv2.line(img, pts[a], pts[b], (80, 200, 120), 2)
    for i, pt in enumerate(pts):
        r = 6 if i in (4, 8, 12, 16, 20) else 4
        cv2.circle(img, pt, r, (255, 255, 255), cv2.FILLED)
        cv2.circle(img, pt, r, (80, 200, 120), 1)

def show_hud(img, text, color=(0, 255, 120)):
    """Draw semi-transparent HUD bar at the top."""
    fh, fw = img.shape[:2]
    overlay = img.copy()
    cv2.rectangle(overlay, (0, 0), (fw, 55), (20, 20, 20), cv2.FILLED)
    cv2.addWeighted(overlay, 0.55, img, 0.45, 0, img)
    cv2.putText(img, text, (15, 38), cv2.FONT_HERSHEY_DUPLEX, 1.0, color, 2)

def set_hud(text, color=(0, 255, 120), duration=1.2):
    global hud_text, hud_color, hud_until
    hud_text  = text
    hud_color = color
    hud_until = time.time() + duration

def check_gesture_hold(name):
    """Returns True the first frame a gesture has been held HOLD_FRAMES consecutive frames."""
    global gesture_hold_name, gesture_hold_count
    if gesture_hold_name == name:
        gesture_hold_count += 1
    else:
        gesture_hold_name  = name
        gesture_hold_count = 1
    return gesture_hold_count == HOLD_FRAMES  # trigger exactly once

def reset_hold():
    global gesture_hold_name, gesture_hold_count
    gesture_hold_name  = None
    gesture_hold_count = 0

# ──────────────────────────────────────────────
# WEBCAM
# ──────────────────────────────────────────────
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
if not cap.isOpened():
    print("Error: Could not open webcam.")
    sys.exit(1)

# ──────────────────────────────────────────────
# GESTURE REFERENCE CARD (shown in terminal)
# ──────────────────────────────────────────────
GUIDE = """
+--------------------------------------------------+
|     HAND GESTURE CONTROLLER  -  GUIDE           |
+--------------------------------------------------+
|  MOUSE                                           |
|   [1 finger]  Index only        -> Move cursor   |
|   Pinch thumb+index             -> Left click    |
|   Double pinch                  -> Double click  |
|   Pinch thumb+middle            -> Right click   |
+--------------------------------------------------+
|  SCROLL                                          |
|   [2 fingers] Index+Middle up   -> Move up/down  |
+--------------------------------------------------+
|  SYSTEM                                          |
|   Shaka (thumb+pinky) move up/down  -> Volume    |
|   4 fingers (thumb in) move up/down -> Brightness|
+--------------------------------------------------+
|  MEDIA & BROWSER                                 |
|   [0 fingers] Fist              -> Play/Pause    |
|   [5 fingers] Open palm + swipe -> Back/Forward  |
+--------------------------------------------------+
|  APP LAUNCHERS  (hold pose ~0.6s)                |
|   Thumbs Up           -> File Explorer           |
|   Index+Middle+Ring   -> Calculator              |
|   L-shape thumb+index -> Start/Stop Recording    |
|   OK sign             -> Take Photo              |
|   V/Peace sign        -> Screenshot              |
+--------------------------------------------------+
|  Press  Q  in preview window to quit             |
+--------------------------------------------------+
"""
print(GUIDE)

# ──────────────────────────────────────────────
# MAIN LOOP
# ──────────────────────────────────────────────
while cap.isOpened():
    success, frame = cap.read()
    if not success:
        continue

    frame       = cv2.flip(frame, 1)
    clean_frame = frame.copy()
    fh, fw      = frame.shape[:2]
    rgb         = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = detector.detect(mp_img)

    current_time = time.time()
    hand_detected = bool(result.hand_landmarks)

    if hand_detected:
        lm = result.hand_landmarks[0]
        draw_skeleton(frame, lm)

        thumb, index, middle, ring, pinky = get_finger_status(lm)
        num_up = sum([thumb, index, middle, ring, pinky])

        thumb_tip  = lm[4]
        index_tip  = lm[8]
        middle_tip = lm[12]

        wrist = lm[0]
        hand_positions.append((wrist.x, wrist.y))
        if len(hand_positions) > MAX_POSITIONS:
            hand_positions.pop(0)

        # ── ACTIVE ZONE for mouse ──────────────────
        ax1, ax2 = fw * 0.15, fw * 0.85
        ay1, ay2 = fh * 0.10, fh * 0.90

        # ══════════════════════════════════════════
        # MODE 1: MOUSE MOVE  (only index finger up)
        # ══════════════════════════════════════════
        if index and not middle and not ring and not pinky and not thumb:
            cv2.rectangle(frame, (int(ax1), int(ay1)), (int(ax2), int(ay2)), (180, 0, 255), 1)

            sx = int(screen_w * (index_tip.x * fw - ax1) / (ax2 - ax1))
            sy = int(screen_h * (index_tip.y * fh - ay1) / (ay2 - ay1))
            sx = max(0, min(screen_w - 1, sx))
            sy = max(0, min(screen_h - 1, sy))

            clocX = plocX + (sx - plocX) / SMOOTHENING
            clocY = plocY + (sy - plocY) / SMOOTHENING
            if math.hypot(clocX - plocX, clocY - plocY) > 1.0:
                pyautogui.moveTo(int(clocX), int(clocY))
                plocX, plocY = clocX, clocY

            # Pinch for clicks (thumb comes close while in move mode)
            d_left  = dist_px(thumb_tip, index_tip,  fw, fh)
            d_right = dist_px(thumb_tip, middle_tip, fw, fh)

            if d_left < CLICK_DIST:
                if not was_pinching_left:
                    dt = current_time - last_click_time
                    if dt < DOUBLE_CLICK_WINDOW:
                        pyautogui.doubleClick()
                        set_hud("Double Click", (0, 255, 0))
                    else:
                        pyautogui.click()
                        set_hud("Left Click", (0, 255, 0))
                    last_click_time    = current_time
                    was_pinching_left  = True
            else:
                was_pinching_left = False

            if d_right < CLICK_DIST and not was_pinching_right and current_time - last_click_time > 0.5:
                pyautogui.click(button='right')
                set_hud("Right Click", (0, 180, 255))
                was_pinching_right = True
                last_click_time    = current_time
            elif d_right >= CLICK_DIST:
                was_pinching_right = False

            reset_hold()

        # ══════════════════════════════════════════
        # MODE 2: SCROLL  (index + middle up)
        # ══════════════════════════════════════════
        elif index and middle and not ring and not pinky:
            if len(hand_positions) >= 6:
                dy = hand_positions[-1][1] - hand_positions[-6][1]
                if abs(dy) > 0.015:
                    pyautogui.scroll(-int(dy * SCROLL_SENSITIVITY * 300))
                    set_hud("Scroll " + ("Up" if dy < 0 else "Down"), (255, 220, 0), 0.3)
            reset_hold()

        # ══════════════════════════════════════════
        # MODE 3: VOLUME  (shaka: thumb + pinky)
        # ══════════════════════════════════════════
        elif thumb and pinky and not index and not middle and not ring:
            if len(hand_positions) >= 6 and current_time - last_action_time > 0.12:
                dy = hand_positions[-1][1] - hand_positions[-6][1]
                if dy < -VOLUME_SENSITIVITY:
                    pyautogui.press('volumeup')
                    set_hud("Vol UP", (0, 230, 255), 0.4)
                    last_action_time = current_time
                elif dy > VOLUME_SENSITIVITY:
                    pyautogui.press('volumedown')
                    set_hud("Vol DOWN", (0, 200, 200), 0.4)
                    last_action_time = current_time
            reset_hold()

        # ══════════════════════════════════════════
        # MODE 4: BRIGHTNESS  (4 fingers, thumb in)
        # ══════════════════════════════════════════
        elif not thumb and index and middle and ring and pinky:
            if BRIGHTNESS_SUPPORTED and len(hand_positions) >= 6 and current_time - last_action_time > 0.25:
                dy = hand_positions[-1][1] - hand_positions[-6][1]
                if abs(dy) > VOLUME_SENSITIVITY:
                    try:
                        cur = sbc.get_brightness()[0]
                        new = max(0, min(100, cur + (-10 if dy < 0 else 10)))
                        sbc.set_brightness(new)
                        set_hud(f"Brightness {'Up' if dy < 0 else 'Down'} ({new}%)", (255, 150, 0), 0.5)
                        last_action_time = current_time
                    except Exception as e:
                        print(f"Brightness error: {e}")
            reset_hold()

        # ══════════════════════════════════════════
        # MODE 5: PLAY/PAUSE  (fist – 0 fingers)
        # ══════════════════════════════════════════
        elif num_up == 0:
            if check_gesture_hold("fist") and current_time - last_action_time > ACTION_COOLDOWN:
                pyautogui.press('playpause')
                set_hud("Play / Pause", (255, 0, 255))
                last_action_time = current_time

        # ══════════════════════════════════════════
        # MODE 6: BROWSER NAV  (open palm – 5 fingers)
        # ══════════════════════════════════════════
        elif num_up == 5:
            swipe = detect_swipe(hand_positions, 0.20)
            if swipe and current_time - last_action_time > ACTION_COOLDOWN:
                if swipe == "LEFT":
                    pyautogui.hotkey('alt', 'left')
                    set_hud("<< Browser Back", (120, 255, 120))
                else:
                    pyautogui.hotkey('alt', 'right')
                    set_hud("Browser Forward >>", (120, 255, 120))
                last_action_time = current_time
            reset_hold()

        # ══════════════════════════════════════════
        # APP LAUNCHERS  (require HOLD_FRAMES hold)
        # ══════════════════════════════════════════
        elif current_time - last_action_time > ACTION_COOLDOWN:

            # ── THUMBS UP → File Explorer ──────────
            if thumb and not index and not middle and not ring and not pinky:
                if lm[4].y < lm[3].y - 0.06:   # strict upward thumb
                    if check_gesture_hold("explorer"):
                        subprocess.Popen('explorer.exe')
                        set_hud("[+] File Explorer", (0, 120, 255))
                        last_action_time = current_time
                else:
                    reset_hold()

            # ── 3 FINGERS (index+middle+ring) → Calculator ──
            elif not thumb and index and middle and ring and not pinky:
                if check_gesture_hold("calculator"):
                    subprocess.Popen('calc.exe')
                    set_hud("[=] Calculator", (0, 120, 255))
                    last_action_time = current_time

            # ── L-SHAPE (thumb+index spread) → Record/Stop ──
            elif thumb and index and not middle and not ring and not pinky:
                d = dist_px(thumb_tip, index_tip, fw, fh)
                if d > 90:
                    if check_gesture_hold("record"):
                        if not is_recording:
                            fname = f"video_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.avi"
                            fpath = os.path.join(os.path.expanduser('~'), 'Pictures', fname)
                            fourcc = cv2.VideoWriter_fourcc(*'XVID')
                            video_writer = cv2.VideoWriter(fpath, fourcc, 20.0, (fw, fh))
                            is_recording = True
                            set_hud("[REC] Recording Started", (0, 0, 255))
                        else:
                            is_recording = False
                            if video_writer:
                                video_writer.release()
                                video_writer = None
                            set_hud("[STOP] Recording Stopped", (200, 200, 0))
                        last_action_time = current_time
                else:
                    reset_hold()

            # ── V / PEACE SIGN → Screenshot ─────────
            elif not thumb and index and middle and not ring and not pinky:
                if check_gesture_hold("screenshot"):
                    fname = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    fpath = os.path.join(os.path.expanduser('~'), 'Pictures', fname)
                    pyautogui.screenshot(fpath)
                    set_hud("[IMG] Screenshot Saved!", (0, 255, 0))
                    last_action_time = current_time

            # ── OK SIGN → Take Photo ─────────────────
            elif middle and ring and pinky:
                d_ok = dist_px(thumb_tip, index_tip, fw, fh)
                if d_ok < 45:
                    if check_gesture_hold("photo"):
                        fname = f"photo_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        fpath = os.path.join(os.path.expanduser('~'), 'Pictures', fname)
                        cv2.imwrite(fpath, clean_frame)
                        set_hud("[CAM] Photo Saved!", (0, 255, 0))
                        last_action_time = current_time
                else:
                    reset_hold()
            else:
                reset_hold()

        else:
            reset_hold()

        # ── Progress bar for hold gestures ──────────────
        if gesture_hold_count > 1 and gesture_hold_count < HOLD_FRAMES:
            pct = int((gesture_hold_count / HOLD_FRAMES) * (fw - 30))
            cv2.rectangle(frame, (15, fh - 20), (15 + pct, fh - 8), (0, 200, 255), cv2.FILLED)
            cv2.rectangle(frame, (15, fh - 20), (fw - 15, fh - 8), (80, 80, 80), 1)

    else:
        hand_positions.clear()
        reset_hold()

    # ── Recording indicator ─────────────────────────────
    if is_recording and video_writer:
        video_writer.write(clean_frame)
        cv2.circle(frame, (fw - 25, 25), 10, (0, 0, 255), cv2.FILLED)
        cv2.putText(frame, "REC", (fw - 60, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    # ── HUD overlay ────────────────────────────────────
    if hud_text and current_time < hud_until:
        show_hud(frame, hud_text, hud_color)

    # ── No-hand indicator ──────────────────────────────
    if not hand_detected:
        cv2.putText(frame, "No hand detected", (int(fw * 0.3), int(fh * 0.5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 200), 2)

    cv2.imshow('Hand Gesture Controller', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ── Cleanup ─────────────────────────────────────────────
if video_writer:
    video_writer.release()
cap.release()
cv2.destroyAllWindows()
print("Gesture controller stopped.")
