

import os
import cv2
import time
import urllib.request
import numpy as np
import pyautogui
from datetime import datetime

#  Paths 
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(BASE_DIR, "..")
TMP_DIR     = os.path.join(PROJECT_DIR, "cache", "tryon_tmp")
OUT_DIR     = os.path.join(PROJECT_DIR, "tryon_captures")
MODEL_PATH  = os.path.join(PROJECT_DIR, "cache", "pose_landmarker.task")
os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

# Official lite model (~3MB, fast)
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_lite/float16/latest/"
    "pose_landmarker_lite.task"
)

# Landmark indices (mediapipe 0.10+ Tasks API)
IDX = {
    "left_shoulder":  11,
    "right_shoulder": 12,
    "left_hip":       23,
    "right_hip":      24,
}


#  MAIN ENTRY — called from command.py 
def handleVirtualTryOn(query):
    from engine.command import speak, takecommand

    speak("Sure! I will capture your screen to get the clothing item. Make sure the clothing is clearly visible.")
    time.sleep(1.2)

    # Download model if needed (only first time)
    if not os.path.exists(MODEL_PATH):
        speak("Downloading pose detection model for the first time. This is about 3 megabytes.")
        if not _download_model():
            speak("Sorry, model download failed. Please check your internet connection.")
            return

    speak("Capturing screen now.")
    screenshot_path = _capture_screenshot()
    if not screenshot_path:
        speak("Screen capture failed. Please try again.")
        return

    speak("Extracting the clothing item.")
    cloth_path = _extract_clothing(screenshot_path)
    if not cloth_path:
        speak("Could not detect a clothing item. Please open a clear image of the clothing and try again.")
        return

    speak("Clothing ready. Opening webcam. Stand back so your full upper body is visible. Press C to capture, R to retry, Q to quit.")
    _run_tryon(cloth_path)


#  DOWNLOAD POSE MODEL 
def _download_model():
    try:
        print(f"[TryOn] Downloading: {MODEL_URL}")
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print(f"[TryOn] Model saved: {MODEL_PATH}")
        return True
    except Exception as e:
        print(f"[TryOn] Download error: {e}")
        return False


#  SCREENSHOT

def _capture_screenshot():
    try:
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(TMP_DIR, f"screen_{ts}.png")
        pyautogui.screenshot().save(path)
        print(f"[TryOn] Screenshot: {path}")
        return path
    except Exception as e:
        print(f"[TryOn] Screenshot error: {e}")
        return None


#  CLOTH EXTRACTION  (3-tier fallback) 
def _extract_clothing(screenshot_path):
    # Tier 1: rembg (best quality, needs pip install rembg)
    try:
        from rembg import remove
        from PIL import Image
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision

        ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
        out    = os.path.join(TMP_DIR, f"cloth_{ts}.png")
        screen = cv2.imread(screenshot_path)
        h, w   = screen.shape[:2]

        # ── Step A: Use Pose detection to find the torso and crop the head out ──
        # This prevents capturing the model's face if we're looking at a person
        cropped = None
        try:
            base_options = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
            options = mp_vision.PoseLandmarkerOptions(base_options=base_options, running_mode=mp_vision.RunningMode.IMAGE)
            with mp_vision.PoseLandmarker.create_from_options(options) as landmarker:
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(screen, cv2.COLOR_BGR2RGB))
                res = landmarker.detect(mp_image)

                if res.pose_landmarks and len(res.pose_landmarks) > 0:
                    lms = res.pose_landmarks[0]
                    # Get shoulder and hip landmarks to define torso
                    ls = lms[IDX["left_shoulder"]]; rs = lms[IDX["right_shoulder"]]
                    lh = lms[IDX["left_hip"]];      rh = lms[IDX["right_hip"]]
                    
                    # Calculate bounding box for torso with some padding
                    y_top = min(ls.y, rs.y) - 0.05 # Start slightly above shoulders
                    y_bot = max(lh.y, rh.y) + 0.1  # End slightly below hips
                    x_l   = min(ls.x, rs.x, lh.x, rh.x) - 0.15
                    x_r   = max(ls.x, rs.x, lh.x, rh.x) + 0.15
                    
                    # Convert to pixel coords and clip
                    y1, y2 = int(max(0, y_top) * h), int(min(1, y_bot) * h)
                    x1, x2 = int(max(0, x_l) * w),   int(min(1, x_r) * w)
                    
                    if (y2 - y1) > 100 and (x2 - x1) > 100:
                        cropped = screen[y1:y2, x1:x2]
                        print(f"[TryOn] Torso isolated via Pose detection")
        except Exception as e:
            print(f"[TryOn] Pose isolation failed: {e}")

        if cropped is None:
            # Fallback: Crop center of screen
            cx, cy = w // 2, h // 2
            cw, ch = min(w, 900), min(h, 900)
            x1, y1 = max(0, cx - cw // 2), max(0, cy - ch // 2)
            x2, y2 = min(w, cx + cw // 2), min(h, cy + ch // 2)
            cropped = screen[y1:y2, x1:x2]
            print(f"[TryOn] Falling back to center crop")

        # ── Step B: Background Removal ──
        img_pil  = Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGBA))
        result   = remove(img_pil)
        arr      = np.array(result)

        # ── Step C: Mask out Head and Hands using Landmarks ──
        # We use the pose landmarks from the original screen, but mapped to our 'cropped' coords
        try:
            ch_h, ch_w = arr.shape[:2]
            # Create a mask for 'forbidden' regions
            mask_forbidden = np.zeros((ch_h, ch_w), dtype=np.uint8)
            
            if res.pose_landmarks and len(res.pose_landmarks) > 0:
                lms = res.pose_landmarks[0]
                
                # Forbidden landmarks: Face (0-10), Hands (15-22)
                forbidden_indices = list(range(11)) + list(range(15, 23))
                
                for idx in forbidden_indices:
                    lm = lms[idx]
                    # Map back to 'cropped' pixel coords
                    px_x = int(lm.x * w) - x1
                    px_y = int(lm.y * h) - y1
                    
                    if 0 <= px_x < ch_w and 0 <= px_y < ch_h:
                        # Draw a circle on the forbidden mask
                        radius = 45 if idx < 11 else 60 # Larger for hands
                        cv2.circle(mask_forbidden, (px_x, px_y), radius, 255, -1)
            
            # Blur the mask for smooth transitions
            mask_forbidden = cv2.GaussianBlur(mask_forbidden, (41, 41), 0)
            
            # Apply: Alpha = Alpha * (1 - Forbidden)
            alpha = arr[:, :, 3].astype(np.float32)
            alpha_factor = 1.0 - (mask_forbidden.astype(np.float32) / 255.0)
            arr[:, :, 3] = (alpha * alpha_factor).astype(np.uint8)
        except Exception as e:
            print(f"[TryOn] Head/Hand masking failed: {e}")

        # ── Step D: Final Crop to non-transparent region ──
        alpha    = arr[:, :, 3]
        _, bin_  = cv2.threshold(alpha, 15, 255, cv2.THRESH_BINARY)
        cnts, _  = cv2.findContours(bin_, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not cnts:
            raise ValueError("no contours")
        largest = max(cnts, key=cv2.contourArea)
        if cv2.contourArea(largest) < 4000:
            raise ValueError("too small")

        bx, by, bw, bh = cv2.boundingRect(largest)
        pad = 5 # Reduced padding for tighter fit
        bx = max(0, bx-pad); by = max(0, by-pad)
        bw = min(arr.shape[1]-bx, bw+2*pad)
        bh = min(arr.shape[0]-by, bh+2*pad)
        Image.fromarray(arr[by:by+bh, bx:bx+bw]).save(out)
        print(f"[TryOn] rembg cloth: {out}")
        return out

    except ImportError:
        print("[TryOn] rembg not installed — using GrabCut")
        return _extract_grabcut(screenshot_path)
    except Exception as e:
        print(f"[TryOn] rembg failed ({e}) — using GrabCut")
        return _extract_grabcut(screenshot_path)


def _extract_grabcut(screenshot_path):
    try:
        ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
        out    = os.path.join(TMP_DIR, f"cloth_{ts}.png")
        screen = cv2.imread(screenshot_path)
        h, w   = screen.shape[:2]

        x1, x2 = int(w*0.28), int(w*0.72)
        y1, y2 = int(h*0.10), int(h*0.78)
        crop   = screen[y1:y2, x1:x2]
        ch, cw = crop.shape[:2]

        mask = np.zeros(crop.shape[:2], np.uint8)
        bgd  = np.zeros((1, 65), np.float64)
        fgd  = np.zeros((1, 65), np.float64)
        rect = (int(cw*0.1), int(ch*0.05), int(cw*0.8), int(ch*0.88))
        cv2.grabCut(crop, mask, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
        mask2 = np.where((mask == 2) | (mask == 0), 0, 255).astype("uint8")

        rgba  = cv2.cvtColor(crop, cv2.COLOR_BGR2BGRA)
        rgba[:, :, 3] = mask2

        cnts, _ = cv2.findContours(mask2, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            largest = max(cnts, key=cv2.contourArea)
            bx, by, bw, bh = cv2.boundingRect(largest)
            pad = 20
            bx = max(0, bx-pad); by = max(0, by-pad)
            bw = min(cw-bx, bw+2*pad); bh = min(ch-by, bh+2*pad)
            rgba = rgba[by:by+bh, bx:bx+bw]

        cv2.imwrite(out, rgba)
        print(f"[TryOn] GrabCut cloth: {out}")
        return out
    except Exception as e:
        print(f"[TryOn] GrabCut failed ({e}) — simple crop")
        return _extract_simple(screenshot_path)


def _extract_simple(screenshot_path):
    try:
        ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
        out    = os.path.join(TMP_DIR, f"cloth_{ts}.png")
        screen = cv2.imread(screenshot_path)
        h, w   = screen.shape[:2]
        crop   = screen[int(h*0.12):int(h*0.75), int(w*0.30):int(w*0.70)]
        rgba   = cv2.cvtColor(crop, cv2.COLOR_BGR2BGRA)
        cv2.imwrite(out, rgba)
        print(f"[TryOn] Simple crop: {out}")
        return out
    except Exception as e:
        print(f"[TryOn] Simple crop failed: {e}")
        return None


#  LIVE TRY-ON — mediapipe 0.10+ Tasks API 
class VoiceState:
    def __init__(self):
        self.command = None
        self.running = True

def _bg_listener(state):
    from engine.command import takecommand
    while state.running:
        try:
            query = takecommand().lower()
            if not query: continue
            print(f"[TryOn] Voice: {query}")
            if any(k in query for k in ["capture", "save", "photo", "click"]):
                state.command = 'c'
            elif any(k in query for k in ["retry", "reset", "again", "reload"]):
                state.command = 'r'
            elif any(k in query for k in ["quit", "stop", "exit", "close", "bye"]):
                state.command = 'q'
        except Exception:
            pass

def _run_tryon(cloth_path):
    import mediapipe as mp
    import threading
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    from mediapipe.tasks.python.vision import PoseLandmarkerOptions, RunningMode

    # Load cloth
    cloth_rgba = cv2.imread(cloth_path, cv2.IMREAD_UNCHANGED)
    if cloth_rgba is None:
        _speak_safe("Could not load the clothing image.")
        return
    if cloth_rgba.ndim < 3 or cloth_rgba.shape[2] == 3:
        cloth_rgba = cv2.cvtColor(cloth_rgba, cv2.COLOR_BGR2BGRA)

    # Build landmarker
    opts = PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    lander = mp_vision.PoseLandmarker.create_from_options(opts)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        _speak_safe("Webcam could not be opened.")
        lander.close()
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    WIN = "Nora Virtual Try-On  |  C=Capture  R=Retry  Q=Quit"
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN, 1280, 720)

    ts_ms       = 0
    no_body_cnt = 0

    # Start voice listener thread
    v_state = VoiceState()
    v_thread = threading.Thread(target=_bg_listener, args=(v_state,), daemon=True)
    v_thread.start()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame  = cv2.flip(frame, 1)
        h, w   = frame.shape[:2]
        output = frame.copy()

        # Pose detection
        mp_img = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        )
        ts_ms += 33
        result = lander.detect_for_video(mp_img, ts_ms)

        if result.pose_landmarks and len(result.pose_landmarks) > 0:
            no_body_cnt = 0
            lms = result.pose_landmarks[0]

            def px(idx):
                lm = lms[idx]
                return (int(lm.x * w), int(lm.y * h))

            ls = px(IDX["left_shoulder"])
            rs = px(IDX["right_shoulder"])
            lh = px(IDX["left_hip"])
            rh = px(IDX["right_hip"])

            sw = abs(rs[0] - ls[0])               # shoulder width
            th = abs(((lh[1]+rh[1])//2) - ((ls[1]+rs[1])//2))  # torso height

            # Slightly larger multipliers for a fuller fit
            cw = int(sw * 1.9)
            ch = int(th * 1.8)

            if cw < 20 or ch < 20:
                _draw_msg(output, "Move closer to camera", w, h)
            else:
                # Better centering and vertical positioning
                cx = min(ls[0], rs[0]) - int(sw * 0.45)
                cy = min(ls[1], rs[1]) - int(th * 0.15)
                output = _overlay_cloth(output, cloth_rgba, cx, cy, cw, ch)

            # Landmark dots
            for pt in [ls, rs, lh, rh]:
                cv2.circle(output, pt, 6, (0, 201, 177), -1)
                cv2.circle(output, pt, 7, (255, 255, 255), 1)
        else:
            no_body_cnt += 1
            if no_body_cnt > 25:
                _draw_msg(output, "No body detected — step back from camera", w, h)

        _draw_hud(output, w, h)
        cv2.imshow(WIN, output)

        # Check for Keyboard OR Voice commands
        key = cv2.waitKey(1) & 0xFF
        cmd = chr(key) if key != 255 else None
        
        if v_state.command:
            cmd = v_state.command
            v_state.command = None # Clear it
            print(f"[TryOn] Executing voice command: {cmd}")

        if cmd == 'q' or key == 27:
            break
        elif cmd == 'c':
            saved = _save_capture(output)
            _speak_safe("Captured and saved.")
            _draw_msg(output, "Saved!", w, h)
            cv2.imshow(WIN, output)
            cv2.waitKey(1500)
        elif cmd == 'r':
            cap.release()
            cv2.destroyAllWindows()
            lander.close()
            v_state.running = False # Stop voice thread
            _speak_safe("Retrying. Please wait.")
            handleVirtualTryOn("retry")
            return

    v_state.running = False
    cap.release()
    cv2.destroyAllWindows()
    lander.close()
    print("[TryOn] Session ended.")


#  OVERLAY + UI HELPERS 
def _overlay_cloth(frame, cloth_rgba, x, y, tw, th):
    if tw <= 0 or th <= 0:
        return frame
    try:
        cloth  = cv2.resize(cloth_rgba, (tw, th), interpolation=cv2.INTER_LINEAR)
        fh, fw = frame.shape[:2]
        x1f = max(0, x);       y1f = max(0, y)
        x2f = min(fw, x+tw);   y2f = min(fh, y+th)
        x1c = x1f - x;         y1c = y1f - y
        x2c = x1c + (x2f-x1f); y2c = y1c + (y2f-y1f)
        if x2f <= x1f or y2f <= y1f:
            return frame
        roi_c = cloth[y1c:y2c, x1c:x2c]
        roi_f = frame[y1f:y2f, x1f:x2f].astype(np.float32)
        if roi_c.shape[2] == 4:
            a       = roi_c[:, :, 3:4].astype(np.float32) / 255.0
            blended = (a * roi_c[:, :, :3].astype(np.float32) + (1-a) * roi_f).astype(np.uint8)
        else:
            blended = roi_c[:, :, :3]
        frame[y1f:y2f, x1f:x2f] = blended
    except Exception as e:
        print(f"[TryOn] Overlay error: {e}")
    return frame


def _draw_hud(frame, w, h):
    ov = frame.copy()
    cv2.rectangle(ov, (0, h-52), (w, h), (30, 39, 97), -1)
    cv2.addWeighted(ov, 0.72, frame, 0.28, 0, frame)
    f = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, "Nora Virtual Try-On", (18, h-28), f, 0.6, (0, 201, 177), 2)
    cv2.putText(frame, "Say 'Capture', 'Retry', or 'Quit' (or use keys C, R, Q)",
                (w//2-220, h-28), f, 0.5, (200, 200, 200), 1)


def _draw_msg(frame, msg, w, h):
    ov = frame.copy()
    cv2.rectangle(ov, (0, h//2-38), (w, h//2+38), (0, 0, 0), -1)
    cv2.addWeighted(ov, 0.6, frame, 0.4, 0, frame)
    f  = cv2.FONT_HERSHEY_SIMPLEX
    tw = cv2.getTextSize(msg, f, 0.8, 2)[0][0]
    cv2.putText(frame, msg, ((w-tw)//2, h//2+10), f, 0.8, (0, 201, 177), 2)


def _save_capture(frame):
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUT_DIR, f"tryon_{ts}.jpg")
    cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return path


def _speak_safe(text):
    try:
        from engine.command import speak
        speak(text)
    except Exception:
        print(f"[TryOn] {text}")