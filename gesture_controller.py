import io
import sys as _sys
_sys.stdout = io.TextIOWrapper(_sys.stdout.buffer, encoding='utf-8', errors='replace')

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import pyautogui
import math
import subprocess
import time
import os
import json
import datetime

# ──────────────────────────────────────────────────────────────
#  LOAD CONFIG
# ──────────────────────────────────────────────────────────────
_cfg_path = os.path.join(os.path.dirname(__file__), 'config.json')
with open(_cfg_path) as _f:
    CFG = json.load(_f)

SMOOTHENING             = CFG['smoothening']
CLICK_DIST              = CFG['click_distance']
DOUBLE_CLICK_WINDOW     = CFG['double_click_window']
ACTION_COOLDOWN         = CFG['action_cooldown']
SCROLL_SENSITIVITY      = CFG['scroll_sensitivity']
VOLUME_SENSITIVITY      = CFG['volume_sensitivity']
BRIGHTNESS_SENSITIVITY  = CFG['brightness_sensitivity']
HOLD_FRAMES             = CFG['hold_frames']
DRAG_THRESH             = CFG['drag_move_threshold']
SWIPE_H                 = CFG['swipe_threshold']
SWIPE_V                 = CFG['swipe_vertical_threshold']
CAM_W                   = CFG['webcam_width']
CAM_H                   = CFG['webcam_height']
MARGIN                  = CFG['active_zone_margin']
CAM_IDX                 = CFG['camera_index']
DETECT_CONF             = CFG['min_detection_confidence']
TRACK_CONF              = CFG['min_tracking_confidence']

# ──────────────────────────────────────────────────────────────
#  PYAUTOGUI
# ──────────────────────────────────────────────────────────────
pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0
screen_w, screen_h = pyautogui.size()

# ──────────────────────────────────────────────────────────────
#  OPTIONAL: BRIGHTNESS
# ──────────────────────────────────────────────────────────────
try:
    import screen_brightness_control as sbc
    BRIGHTNESS_OK = True
except Exception:
    BRIGHTNESS_OK = False
    print("[INFO] screen_brightness_control unavailable – brightness disabled.")

# ──────────────────────────────────────────────────────────────
#  MEDIAPIPE (Tasks API)
# ──────────────────────────────────────────────────────────────
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'hand_landmarker.task')
if not os.path.exists(MODEL_PATH):
    import urllib.request
    print("[INFO] Downloading hand_landmarker.task …")
    urllib.request.urlretrieve(
        'https://storage.googleapis.com/mediapipe-models/hand_landmarker/'
        'hand_landmarker/float16/1/hand_landmarker.task',
        MODEL_PATH
    )

_base_opts = python.BaseOptions(model_asset_path=MODEL_PATH)
_mp_opts   = vision.HandLandmarkerOptions(
    _base_opts,
    num_hands=1,
    min_hand_detection_confidence=DETECT_CONF,
    min_hand_presence_confidence=DETECT_CONF,
    min_tracking_confidence=TRACK_CONF
)
detector = vision.HandLandmarker.create_from_options(_mp_opts)

# Hand skeleton connection pairs
CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (9,10),(10,11),(11,12),
    (13,14),(14,15),(15,16),
    (17,18),(18,19),(19,20),
    (0,17),(5,9),(9,13),(13,17)
]
# Finger colour groups for drawing (thumb, index, middle, ring, pinky)
FINGER_COLORS = [
    (255,180,0),(0,220,255),(0,255,120),(255,100,255),(255,80,80)
]
FINGER_BONES = [
    [(0,1),(1,2),(2,3),(3,4)],
    [(0,5),(5,6),(6,7),(7,8)],
    [(9,10),(10,11),(11,12)],
    [(13,14),(14,15),(15,16)],
    [(17,18),(18,19),(19,20)],
]

# ──────────────────────────────────────────────────────────────
#  STATE
# ──────────────────────────────────────────────────────────────
plocX, plocY         = 0.0, 0.0
clocX, clocY         = 0.0, 0.0

last_click_time      = 0.0
was_pinching_left    = False
was_pinching_right   = False
last_action_time     = 0.0
last_scroll_time     = 0.0
last_volume_time     = 0.0

# Drag state
is_dragging          = False

# Swipe / position history
hand_positions       = []           # list of (wrist_x, wrist_y)
MAX_POS              = 18

# Recording
is_recording         = False
video_writer         = None

# Mute state
is_muted             = False

# Gestures are globally paused
is_paused            = False

# Hold-gesture tracker
hold_name            = None
hold_count           = 0

# HUD
hud_text             = ""
hud_color            = (0, 255, 120)
hud_until            = 0.0

# Mode label shown permanently in corner
current_mode         = "---"
mode_color           = (180, 180, 180)

# ──────────────────────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────────────────────
def px_dist(p1, p2, fw, fh):
    return math.hypot((p1.x - p2.x)*fw, (p1.y - p2.y)*fh)

def angle_3pts(a, b, c):
    """Angle at vertex b formed by vectors ba and bc (degrees)."""
    ax, ay = a.x - b.x, a.y - b.y
    cx, cy = c.x - b.x, c.y - b.y
    dot    = ax*cx + ay*cy
    mag    = math.hypot(ax,ay) * math.hypot(cx,cy)
    if mag == 0:
        return 180.0
    return math.degrees(math.acos(max(-1.0, min(1.0, dot/mag))))

def get_fingers(lm):
    """Returns (thumb, index, middle, ring, pinky) as booleans using angle-based bend detection."""
    # Thumb: distance-based (more reliable across hand orientations)
    d_tip = math.hypot(lm[4].x-lm[17].x, lm[4].y-lm[17].y)
    d_mcp = math.hypot(lm[2].x-lm[17].x, lm[2].y-lm[17].y)
    thumb  = d_tip > d_mcp

    # Other fingers: angle at PIP joint – if < 155°, finger is bent
    tip_pip_mcp = [(8,7,6),(12,11,10),(16,15,14),(20,19,18)]
    extended    = []
    for tip, pip, mcp in tip_pip_mcp:
        ang = angle_3pts(lm[tip], lm[pip], lm[mcp])
        extended.append(ang > 155)

    return (thumb, *extended)

def hand_stable(positions, n=8, threshold=0.012):
    """True if the last n wrist positions are within threshold (no movement)."""
    if len(positions) < n:
        return False
    xs = [p[0] for p in positions[-n:]]
    ys = [p[1] for p in positions[-n:]]
    return (max(xs)-min(xs)) < threshold and (max(ys)-min(ys)) < threshold

def detect_swipe(positions, h_thresh=None, v_thresh=None):
    """Returns direction string or None from position history."""
    if len(positions) < MAX_POS:
        return None
    dx = positions[-1][0] - positions[0][0]
    dy = positions[-1][1] - positions[0][1]
    ht = h_thresh if h_thresh else SWIPE_H
    vt = v_thresh if v_thresh else SWIPE_V
    if   abs(dx) > abs(dy) and dx >  ht: return "RIGHT"
    elif abs(dx) > abs(dy) and dx < -ht: return "LEFT"
    elif abs(dy) > abs(dx) and dy < -vt: return "UP"
    elif abs(dy) > abs(dx) and dy >  vt: return "DOWN"
    return None

def check_hold(name):
    global hold_name, hold_count
    if hold_name == name:
        hold_count += 1
    else:
        hold_name  = name
        hold_count = 1
    return hold_count == HOLD_FRAMES

def reset_hold():
    global hold_name, hold_count
    hold_name  = None
    hold_count = 0

def set_hud(text, color=(0,255,120), dur=1.3):
    global hud_text, hud_color, hud_until
    hud_text  = text
    hud_color = color
    hud_until = time.time() + dur
    print(f"[GESTURE] {text}")

def set_mode(label, color=(0,220,255)):
    global current_mode, mode_color
    current_mode = label
    mode_color   = color

# ──────────────────────────────────────────────────────────────
#  DRAWING
# ──────────────────────────────────────────────────────────────
def draw_skeleton(img, lm, fingers):
    fh, fw = img.shape[:2]
    pts    = [(int(p.x*fw), int(p.y*fh)) for p in lm]

    # Palm connections (white-grey)
    for a, b in [(0,1),(0,5),(5,9),(9,13),(13,17),(0,17)]:
        cv2.line(img, pts[a], pts[b], (80,80,90), 2)

    # Finger bones (colored by finger)
    finger_idx = [(0,[(0,1),(1,2),(2,3),(3,4)]),
                  (1,[(5,6),(6,7),(7,8)]),
                  (2,[(9,10),(10,11),(11,12)]),
                  (3,[(13,14),(14,15),(15,16)]),
                  (4,[(17,18),(18,19),(19,20)])]
    for fi, bones in finger_idx:
        col = FINGER_COLORS[fi]
        extended = [fingers[0],fingers[1],fingers[2],fingers[3],fingers[4]][fi]
        line_col = col if extended else (40,40,50)
        for a, b in bones:
            cv2.line(img, pts[a], pts[b], line_col, 2)

    # Joint dots
    for i, pt in enumerate(pts):
        r = 7 if i in (4,8,12,16,20) else 4
        fi = 0 if i<=4 else (1 if i<=8 else (2 if i<=12 else (3 if i<=16 else 4)))
        cv2.circle(img, pt, r, FINGER_COLORS[fi], cv2.FILLED)
        cv2.circle(img, pt, r, (0,0,0), 1)

def draw_hud(img):
    """Semi-transparent top bar with HUD message."""
    fh, fw = img.shape[:2]
    if hud_text and time.time() < hud_until:
        ovl = img.copy()
        cv2.rectangle(ovl, (0,0), (fw,52), (15,15,25), cv2.FILLED)
        cv2.addWeighted(ovl, 0.60, img, 0.40, 0, img)
        cv2.putText(img, hud_text, (14,36),
                    cv2.FONT_HERSHEY_DUPLEX, 1.0, hud_color, 2)

def draw_mode_badge(img):
    """Colored mode pill in top-right corner."""
    fh, fw = img.shape[:2]
    text = f" MODE: {current_mode} "
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    x1 = fw - tw - 18
    ovl = img.copy()
    cv2.rectangle(ovl, (x1-4, 8), (fw-10, 38), mode_color, cv2.FILLED)
    cv2.addWeighted(ovl, 0.35, img, 0.65, 0, img)
    cv2.rectangle(img, (x1-4,8), (fw-10,38), mode_color, 2)
    cv2.putText(img, text, (x1, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)

def draw_hold_bar(img, fingers):
    """Yellow progress bar at bottom of frame."""
    fh, fw = img.shape[:2]
    if hold_count > 1 and hold_count < HOLD_FRAMES:
        pct = int((hold_count / HOLD_FRAMES) * (fw - 30))
        cv2.rectangle(img, (15,fh-18), (fw-15,fh-6), (40,40,40), cv2.FILLED)
        cv2.rectangle(img, (15,fh-18), (15+pct,fh-6), (0,220,255), cv2.FILLED)

def draw_active_zone(img):
    fh, fw = img.shape[:2]
    x1 = int(fw*MARGIN);   y1 = int(fh*MARGIN)
    x2 = int(fw*(1-MARGIN)); y2 = int(fh*(1-MARGIN))
    cv2.rectangle(img, (x1,y1), (x2,y2), (180,0,255), 1)

def draw_paused(img):
    fh, fw = img.shape[:2]
    ovl = img.copy()
    cv2.rectangle(ovl,(0,0),(fw,fh),(30,10,10),cv2.FILLED)
    cv2.addWeighted(ovl,0.4,img,0.6,0,img)
    cv2.putText(img,"-- PAUSED --",(int(fw*0.28),int(fh*0.5)),
                cv2.FONT_HERSHEY_DUPLEX,2.0,(0,0,220),3)
    cv2.putText(img,"Hold FIST 1s to resume",(int(fw*0.22),int(fh*0.62)),
                cv2.FONT_HERSHEY_SIMPLEX,0.8,(200,200,200),2)

# ──────────────────────────────────────────────────────────────
#  TERMINAL GUIDE
# ──────────────────────────────────────────────────────────────
GUIDE = """
+====================================================+
|     HAND GESTURE CONTROLLER  v2.0  -  GUIDE        |
+====================================================+
|  MOUSE                                             |
|   [1 finger] Index only       -> Move cursor       |
|   Pinch index+thumb           -> Left Click        |
|   Double pinch (fast)         -> Double Click      |
|   Pinch + move hand           -> DRAG & DROP       |
|   Pinch middle+thumb          -> Right Click       |
+----------------------------------------------------+
|  SCROLL                                            |
|   [2 fingers] Index+Middle    -> Move up/down      |
+----------------------------------------------------+
|  SYSTEM CONTROLS                                   |
|   Shaka (thumb+pinky)         -> Volume up/down    |
|   4 fingers (thumb folded)    -> Brightness        |
|   Pinky only                  -> Mute Toggle       |
+----------------------------------------------------+
|  WINDOW MANAGEMENT  (hold ~0.6s)                   |
|   Ring+Pinky only             -> Minimize Window   |
|   Middle+Ring+Pinky (no idx)  -> Maximize/Restore  |
|   Open palm SWIPE UP          -> Show Desktop      |
|   Thumb+Index+Pinky           -> Task View         |
+----------------------------------------------------+
|  MEDIA & BROWSER                                   |
|   [0 fingers] Fist (hold)     -> Play/Pause        |
|   Open palm SWIPE LEFT        -> Browser Back      |
|   Open palm SWIPE RIGHT       -> Browser Forward   |
|   Open palm SWIPE DOWN        -> Switch Vert. Desk |
+----------------------------------------------------+
|  APP LAUNCHERS  (hold ~0.6s)                       |
|   Thumbs Up                   -> File Explorer     |
|   Index+Middle+Ring           -> Calculator        |
|   L-shape (thumb+idx spread)  -> Record Toggle     |
|   V/Peace sign (stationary)   -> Screenshot        |
|   OK sign                     -> Take Photo        |
|   All 5 spread (hold 2s)      -> Lock Screen       |
+----------------------------------------------------+
|  SYSTEM                                            |
|   Hold FIST 2s                -> Pause/Resume ALL  |
|   Press Q in window           -> Quit              |
+====================================================+
"""
print(GUIDE)

# ──────────────────────────────────────────────────────────────
#  WEBCAM
# ──────────────────────────────────────────────────────────────
cap = cv2.VideoCapture(CAM_IDX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAM_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)
if not cap.isOpened():
    print("ERROR: Cannot open webcam.")
    _sys.exit(1)

# ──────────────────────────────────────────────────────────────
#  MAIN LOOP
# ──────────────────────────────────────────────────────────────
while cap.isOpened():
    ok, frame = cap.read()
    if not ok:
        continue

    frame       = cv2.flip(frame, 1)
    clean       = frame.copy()
    fh, fw      = frame.shape[:2]
    rgb         = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    mp_img  = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result  = detector.detect(mp_img)
    now     = time.time()

    # ── Active Zone ───────────────────────────────────────────
    ax1, ax2 = fw * MARGIN,       fw * (1-MARGIN)
    ay1, ay2 = fh * MARGIN,       fh * (1-MARGIN)

    hand_ok = bool(result.hand_landmarks)

    if hand_ok:
        lm = result.hand_landmarks[0]
        thumb, index, middle, ring, pinky = get_fingers(lm)
        fingers = (thumb, index, middle, ring, pinky)
        num_up  = sum(fingers)

        draw_skeleton(frame, lm, fingers)

        # Wrist history
        wrist = lm[0]
        hand_positions.append((wrist.x, wrist.y))
        if len(hand_positions) > MAX_POS:
            hand_positions.pop(0)

        thumb_tip  = lm[4]
        index_tip  = lm[8]
        middle_tip = lm[12]

        # ══════════════════════════════════════════════════════
        #  PAUSE / RESUME  –  fist held for 2× HOLD_FRAMES
        # ══════════════════════════════════════════════════════
        if num_up == 0:
            if check_hold("pause_fist") and hold_count >= HOLD_FRAMES * 2:
                is_paused = not is_paused
                if is_paused:
                    set_hud("** GESTURES PAUSED **", (0,0,220))
                else:
                    set_hud("** GESTURES RESUMED **", (0,255,0))
                    reset_hold()
                last_action_time = now

        if is_paused:
            draw_paused(frame)
            draw_hud(frame)
            cv2.imshow('Hand Gesture Controller  |  Q = Quit', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        # ══════════════════════════════════════════════════════
        #  MODE 1 – MOUSE MOVE  (only index finger up)
        # ══════════════════════════════════════════════════════
        if index and not middle and not ring and not pinky:
            set_mode("MOUSE", (0,200,255))
            draw_active_zone(frame)

            # Map finger tip to screen
            sx = int(screen_w * (index_tip.x*fw - ax1) / (ax2 - ax1))
            sy = int(screen_h * (index_tip.y*fh - ay1) / (ay2 - ay1))
            sx = max(0, min(screen_w-1, sx))
            sy = max(0, min(screen_h-1, sy))

            clocX = plocX + (sx - plocX) / SMOOTHENING
            clocY = plocY + (sy - plocY) / SMOOTHENING

            d_left  = px_dist(thumb_tip, index_tip,  fw, fh)
            d_right = px_dist(thumb_tip, middle_tip, fw, fh)

            # Left click / drag
            if d_left < CLICK_DIST:
                if not was_pinching_left:
                    dt = now - last_click_time
                    if dt < DOUBLE_CLICK_WINDOW:
                        pyautogui.doubleClick()
                        set_hud("Double Click", (0,255,0))
                        is_dragging = False
                    else:
                        pyautogui.mouseDown()
                        is_dragging = True
                    last_click_time   = now
                    was_pinching_left = True
                else:
                    # Sustained pinch = drag: move while held
                    if is_dragging and math.hypot(clocX-plocX, clocY-plocY) > DRAG_THRESH:
                        pyautogui.moveTo(int(clocX), int(clocY))
                        plocX, plocY = clocX, clocY
                        set_hud("Dragging ...", (255,140,0), 0.2)
            else:
                if was_pinching_left:
                    if is_dragging:
                        pyautogui.mouseUp()
                        set_hud("Drop!", (255,140,0))
                        is_dragging = False
                    else:
                        # It was a short press = single click
                        pyautogui.click()
                        set_hud("Left Click", (0,255,120))
                was_pinching_left = False

            # Right click
            if d_right < CLICK_DIST and not was_pinching_right and now-last_click_time>0.5:
                pyautogui.click(button='right')
                set_hud("Right Click", (0,100,255))
                was_pinching_right = True
                last_click_time    = now
            elif d_right >= CLICK_DIST:
                was_pinching_right = False

            # Move cursor (only when NOT dragging to avoid jitter-release)
            if not is_dragging and math.hypot(clocX-plocX, clocY-plocY) > 1.0:
                pyautogui.moveTo(int(clocX), int(clocY))
                plocX, plocY = clocX, clocY

            reset_hold()

        # ══════════════════════════════════════════════════════
        #  MODE 2 – SCROLL  (index + middle, stationary=screenshot)
        # ══════════════════════════════════════════════════════
        elif index and middle and not ring and not pinky and not thumb:
            stable = hand_stable(hand_positions)

            if not stable:
                # Moving = scroll
                set_mode("SCROLL", (255,220,0))
                if len(hand_positions) >= 6 and now-last_scroll_time > 0.05:
                    dy = hand_positions[-1][1] - hand_positions[-6][1]
                    if abs(dy) > 0.010:
                        scroll_amt = -int(dy * SCROLL_SENSITIVITY)
                        pyautogui.scroll(scroll_amt)
                        lbl = "Scroll Up" if scroll_amt > 0 else "Scroll Down"
                        set_hud(lbl, (255,220,0), 0.25)
                        last_scroll_time = now
                reset_hold()
            else:
                # Stationary = screenshot (hold to confirm)
                set_mode("SCREENSHOT?", (200,100,255))
                if check_hold("screenshot") and now-last_action_time > ACTION_COOLDOWN:
                    fname = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    fpath = os.path.join(os.path.expanduser('~'), 'Pictures', fname)
                    pyautogui.screenshot(fpath)
                    set_hud("[IMG] Screenshot Saved!", (200,100,255))
                    last_action_time = now

        # ══════════════════════════════════════════════════════
        #  MODE 3 – VOLUME  (shaka: thumb + pinky only)
        # ══════════════════════════════════════════════════════
        elif thumb and pinky and not index and not middle and not ring:
            set_mode("VOLUME", (0,230,255))
            if len(hand_positions) >= 5 and now-last_volume_time > 0.10:
                dy = hand_positions[-1][1] - hand_positions[-5][1]
                if dy < -VOLUME_SENSITIVITY:
                    pyautogui.press('volumeup')
                    set_hud("Vol UP", (0,230,255), 0.35)
                    last_volume_time = now
                elif dy > VOLUME_SENSITIVITY:
                    pyautogui.press('volumedown')
                    set_hud("Vol DOWN", (0,180,200), 0.35)
                    last_volume_time = now
            reset_hold()

        # ══════════════════════════════════════════════════════
        #  MODE 4 – BRIGHTNESS  (4 fingers, thumb folded)
        # ══════════════════════════════════════════════════════
        elif not thumb and index and middle and ring and pinky:
            set_mode("BRIGHTNESS", (255,150,0))
            if BRIGHTNESS_OK and len(hand_positions) >= 5 and now-last_action_time > 0.22:
                dy = hand_positions[-1][1] - hand_positions[-5][1]
                if abs(dy) > BRIGHTNESS_SENSITIVITY:
                    try:
                        cur = sbc.get_brightness()[0]
                        new = max(5, min(100, cur + (-10 if dy<0 else 10)))
                        sbc.set_brightness(new)
                        set_hud(f"Brightness {'Up' if dy<0 else 'Down'}  {new}%", (255,150,0), 0.4)
                        last_action_time = now
                    except Exception as e:
                        print(f"[BRIGHTNESS ERR] {e}")
            reset_hold()

        # ══════════════════════════════════════════════════════
        #  MODE 5 – MUTE TOGGLE  (pinky only)
        # ══════════════════════════════════════════════════════
        elif pinky and not thumb and not index and not middle and not ring:
            set_mode("MUTE", (255,60,60))
            if check_hold("mute") and now-last_action_time > ACTION_COOLDOWN:
                pyautogui.press('volumemute')
                is_muted = not is_muted
                set_hud("[MUTE] " + ("Muted" if is_muted else "Unmuted"), (255,60,60))
                last_action_time = now

        # ══════════════════════════════════════════════════════
        #  MODE 6 – MINIMIZE  (ring + pinky only)
        # ══════════════════════════════════════════════════════
        elif ring and pinky and not thumb and not index and not middle:
            set_mode("MINIMIZE", (180,180,0))
            if check_hold("minimize") and now-last_action_time > ACTION_COOLDOWN:
                pyautogui.hotkey('win', 'down')
                set_hud("Window Minimized", (180,180,0))
                last_action_time = now

        # ══════════════════════════════════════════════════════
        #  MODE 7 – MAXIMIZE / RESTORE  (middle+ring+pinky, no index)
        # ══════════════════════════════════════════════════════
        elif middle and ring and pinky and not index and not thumb:
            set_mode("MAXIMIZE", (100,255,180))
            if check_hold("maximize") and now-last_action_time > ACTION_COOLDOWN:
                pyautogui.hotkey('win', 'up')
                set_hud("Window Maximized/Restored", (100,255,180))
                last_action_time = now

        # ══════════════════════════════════════════════════════
        #  MODE  –  MIDDLE FINGER  → QUIT  (hold ~0.6s)
        # ══════════════════════════════════════════════════════
        elif middle and not index and not ring and not pinky and not thumb:
            set_mode("!! QUIT !!", (0, 0, 220))
            # Show a big red warning while holding
            fh2, fw2 = frame.shape[:2]
            ovl2 = frame.copy()
            cv2.rectangle(ovl2, (0, 0), (fw2, fh2), (0, 0, 180), cv2.FILLED)
            cv2.addWeighted(ovl2, 0.25, frame, 0.75, 0, frame)
            remaining = HOLD_FRAMES - hold_count
            cv2.putText(frame,
                        f"QUITTING IN {max(0, remaining)} frames ...",
                        (int(fw2 * 0.08), int(fh2 * 0.5)),
                        cv2.FONT_HERSHEY_DUPLEX, 1.3, (0, 0, 255), 3)

            if check_hold("middle_finger_quit"):
                set_hud("Bye! Controller stopped.", (0, 0, 255), 2.0)
                # Cleanup before exit
                if is_dragging:
                    pyautogui.mouseUp()
                if video_writer:
                    video_writer.release()
                cap.release()
                cv2.destroyAllWindows()
                print("[GESTURE] Middle finger detected – controller quit.")
                import sys
                sys.exit(0)

        # ══════════════════════════════════════════════════════
        #  MODE 8 – FIST  (0 fingers → play/pause OR pause gesture)
        # ══════════════════════════════════════════════════════
        elif num_up == 0:
            set_mode("FIST", (255,0,200))
            if check_hold("fist") and now-last_action_time > ACTION_COOLDOWN:
                pyautogui.press('playpause')
                set_hud("Play / Pause", (255,0,200))
                last_action_time = now

        # ══════════════════════════════════════════════════════
        #  MODE 9 – OPEN PALM  (all 5 = swipe gestures)
        # ══════════════════════════════════════════════════════
        elif num_up == 5:
            set_mode("PALM", (120,255,120))
            swipe = detect_swipe(hand_positions)
            if swipe and now-last_action_time > ACTION_COOLDOWN:
                if swipe == "LEFT":
                    pyautogui.hotkey('alt', 'left')
                    set_hud("<< Browser Back", (120,255,120))
                elif swipe == "RIGHT":
                    pyautogui.hotkey('alt', 'right')
                    set_hud(">> Browser Forward", (120,255,120))
                elif swipe == "UP":
                    pyautogui.hotkey('win', 'd')
                    set_hud("Show Desktop", (120,255,120))
                elif swipe == "DOWN":
                    pyautogui.hotkey('ctrl', 'win', 'right')
                    set_hud("Next Virtual Desktop", (120,255,120))
                last_action_time = now
            reset_hold()

        # ══════════════════════════════════════════════════════
        #  MODE 10 – TASK VIEW  (thumb + index + pinky)
        # ══════════════════════════════════════════════════════
        elif thumb and index and pinky and not middle and not ring:
            set_mode("TASK VIEW", (180,100,255))
            if check_hold("taskview") and now-last_action_time > ACTION_COOLDOWN:
                pyautogui.hotkey('win', 'tab')
                set_hud("Task View (Win+Tab)", (180,100,255))
                last_action_time = now

        # ══════════════════════════════════════════════════════
        #  APP LAUNCHERS & UTILITIES
        # ══════════════════════════════════════════════════════
        else:
            if now - last_action_time > ACTION_COOLDOWN:

                # ── THUMBS UP → File Explorer ──────────────────
                if thumb and not index and not middle and not ring and not pinky:
                    if lm[4].y < lm[3].y - 0.05:
                        set_mode("EXPLORER", (0,120,255))
                        if check_hold("explorer"):
                            subprocess.Popen('explorer.exe')
                            set_hud("[+] File Explorer", (0,120,255))
                            last_action_time = now
                    else:
                        reset_hold()

                # ── 3 FINGERS → Calculator ─────────────────────
                elif not thumb and index and middle and ring and not pinky:
                    set_mode("CALCULATOR", (0,200,160))
                    if check_hold("calculator"):
                        subprocess.Popen('calc.exe')
                        set_hud("[=] Calculator", (0,200,160))
                        last_action_time = now

                # ── L-SHAPE (thumb+index spread wide) → Record ─
                elif thumb and index and not middle and not ring and not pinky:
                    d = px_dist(thumb_tip, index_tip, fw, fh)
                    if d > 90:
                        set_mode("RECORD", (0,0,255))
                        if check_hold("record"):
                            if not is_recording:
                                fname = f"video_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.avi"
                                fpath = os.path.join(os.path.expanduser('~'),'Pictures',fname)
                                fourcc = cv2.VideoWriter_fourcc(*'XVID')
                                video_writer = cv2.VideoWriter(fpath, fourcc, 20.0, (fw, fh))
                                is_recording = True
                                set_hud("[REC] Recording Started", (0,0,255))
                            else:
                                is_recording = False
                                if video_writer:
                                    video_writer.release()
                                    video_writer = None
                                set_hud("[STOP] Recording Stopped", (200,200,0))
                            last_action_time = now
                    else:
                        reset_hold()

                # ── OK SIGN → Photo ─────────────────────────────
                elif middle and ring and pinky and not index:
                    d_ok = px_dist(thumb_tip, index_tip, fw, fh)
                    if d_ok < 45:
                        set_mode("PHOTO", (0,255,0))
                        if check_hold("photo"):
                            fname = f"photo_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                            fpath = os.path.join(os.path.expanduser('~'),'Pictures',fname)
                            cv2.imwrite(fpath, clean)
                            set_hud("[CAM] Photo Saved!", (0,255,0))
                            last_action_time = now
                    else:
                        reset_hold()

                # ── ALL 5 FINGERS HELD (wide) → Lock Screen ─────
                elif num_up == 5 and hand_stable(hand_positions, n=12, threshold=0.008):
                    set_mode("LOCK?", (255,40,40))
                    # Require double the hold time for safety
                    if check_hold("lockscreen") and hold_count >= HOLD_FRAMES * 2:
                        pyautogui.hotkey('win', 'l')
                        set_hud("[LOCK] Locking Screen ...", (255,40,40))
                        last_action_time = now

                else:
                    set_mode("---", (150,150,150))
                    reset_hold()
            else:
                reset_hold()

    else:
        # No hand detected
        hand_positions.clear()
        if is_dragging:
            pyautogui.mouseUp()
            is_dragging = False
        reset_hold()
        set_mode("---", (100,100,100))

    # ── Recording frame ────────────────────────────────────────
    if is_recording and video_writer:
        video_writer.write(clean)
        cv2.circle(frame, (fw-28, 28), 11, (0,0,220), cv2.FILLED)
        cv2.putText(frame, "REC", (fw-62,36),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,220), 2)

    # ── Mute indicator ─────────────────────────────────────────
    if is_muted:
        cv2.putText(frame, "[MUTED]", (14, fh-28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,200), 2)

    # ── Overlays ───────────────────────────────────────────────
    draw_hud(frame)
    draw_mode_badge(frame)
    draw_hold_bar(frame, fingers if hand_ok else (False,)*5)

    if not hand_ok:
        cv2.putText(frame, "Show your hand to the camera", (int(fw*0.18), int(fh*0.5)),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (80,80,200), 2)

    cv2.imshow('Hand Gesture Controller  |  Q = Quit', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# ── Cleanup ───────────────────────────────────────────────────
if is_dragging:
    pyautogui.mouseUp()
if video_writer:
    video_writer.release()
cap.release()
cv2.destroyAllWindows()
print("[INFO] Gesture controller stopped cleanly.")
