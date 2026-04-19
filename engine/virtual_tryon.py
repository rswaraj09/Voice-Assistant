import os
import cv2
import time
import threading
import numpy as np
import pyautogui
from datetime import datetime

# ── Paths ─────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(BASE_DIR, "..")
TMP_DIR     = os.path.join(PROJECT_DIR, "cache", "tryon_tmp")
OUT_DIR     = os.path.join(PROJECT_DIR, "tryon_captures")
os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)


# ════════════════════════════════════════════════════════════════════════════
#  MAIN ENTRY — called from command.py
# ════════════════════════════════════════════════════════════════════════════
def handleVirtualTryOn(query):
    from engine.command import speak, takecommand

    speak("Sure! I'll capture your screen to get the clothing item. Please make sure the clothing is visible on screen.")
    time.sleep(1.5)

    # ── Step 1: Screenshot ────────────────────────────────────────────────
    speak("Capturing screen now.")
    screenshot_path = _capture_screenshot()
    if not screenshot_path:
        speak("Sorry, I couldn't capture the screen. Please try again.")
        return

    # ── Step 2: Extract clothing ──────────────────────────────────────────
    speak("Extracting the clothing item from the screen.")
    cloth_path = _extract_clothing(screenshot_path)
    if not cloth_path:
        speak("I couldn't detect a clothing item on screen. Please open a clear image of the clothing and try again.")
        return

    speak("Clothing extracted successfully. Opening webcam for virtual try-on. Press R to retry, C to capture, or Q to quit.")

    # ── Step 3: Run live try-on ───────────────────────────────────────────
    _run_tryon(cloth_path)


# ════════════════════════════════════════════════════════════════════════════
#  STEP 1: SCREENSHOT
# ════════════════════════════════════════════════════════════════════════════
def _capture_screenshot():
    try:
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(TMP_DIR, f"screen_{ts}.png")
        screenshot = pyautogui.screenshot()
        screenshot.save(path)
        print(f"[TryOn] Screenshot saved: {path}")
        return path
    except Exception as e:
        print(f"[TryOn] Screenshot error: {e}")
        return None


# ════════════════════════════════════════════════════════════════════════════
#  STEP 2: CLOTH EXTRACTION
#  Uses rembg to remove background, then crops the largest detected region
# ════════════════════════════════════════════════════════════════════════════
def _extract_clothing(screenshot_path):
    try:
        from rembg import remove
        from PIL import Image

        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        out  = os.path.join(TMP_DIR, f"cloth_{ts}.png")

        # Load screenshot
        screen = cv2.imread(screenshot_path)
        h, w   = screen.shape[:2]

        # Focus on center region (where clothing images usually are)
        cx, cy = w // 2, h // 2
        crop_w = min(w, 800)
        crop_h = min(h, 800)
        x1 = max(0, cx - crop_w // 2)
        y1 = max(0, cy - crop_h // 2)
        x2 = min(w, cx + crop_w // 2)
        y2 = min(h, cy + crop_h // 2)
        cropped = screen[y1:y2, x1:x2]

        # Remove background using rembg
        img_pil    = Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGBA))
        result_pil = remove(img_pil)
        result_arr = np.array(result_pil)

        # Find largest non-transparent region
        alpha = result_arr[:, :, 3]
        _, binary = cv2.threshold(alpha, 10, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            print("[TryOn] No clothing contours found")
            return None

        # Largest contour = main clothing item
        largest = max(contours, key=cv2.contourArea)
        area    = cv2.contourArea(largest)

        if area < 5000:
            print(f"[TryOn] Detected region too small: {area}px²")
            return None

        bx, by, bw, bh = cv2.boundingRect(largest)
        # Add padding
        pad = 20
        bx  = max(0, bx - pad)
        by  = max(0, by - pad)
        bw  = min(result_arr.shape[1] - bx, bw + 2*pad)
        bh  = min(result_arr.shape[0] - by, bh + 2*pad)

        cloth_crop = result_arr[by:by+bh, bx:bx+bw]
        Image.fromarray(cloth_crop).save(out)

        print(f"[TryOn] Cloth extracted: {out} ({bw}x{bh}px)")
        return out

    except ImportError:
        print("[TryOn] rembg not installed. Using fallback extraction.")
        return _extract_clothing_fallback(screenshot_path)
    except Exception as e:
        print(f"[TryOn] Cloth extraction error: {e}")
        return _extract_clothing_fallback(screenshot_path)


def _extract_clothing_fallback(screenshot_path):
    """Fallback: crop center region without background removal."""
    try:
        ts     = datetime.now().strftime("%Y%m%d_%H%M%S")
        out    = os.path.join(TMP_DIR, f"cloth_{ts}.png")
        screen = cv2.imread(screenshot_path)
        h, w   = screen.shape[:2]
        # Take center 40% of screen
        x1 = int(w * 0.3); x2 = int(w * 0.7)
        y1 = int(h * 0.15); y2 = int(h * 0.75)
        crop = screen[y1:y2, x1:x2]
        # Convert to RGBA
        rgba = cv2.cvtColor(crop, cv2.COLOR_BGR2BGRA)
        cv2.imwrite(out, rgba)
        print(f"[TryOn] Fallback cloth crop: {out}")
        return out
    except Exception as e:
        print(f"[TryOn] Fallback error: {e}")
        return None


# ════════════════════════════════════════════════════════════════════════════
#  STEP 3: LIVE TRY-ON WINDOW
# ════════════════════════════════════════════════════════════════════════════
def _run_tryon(cloth_path):
    import mediapipe as mp

    # Load cloth image (BGRA with alpha)
    cloth_rgba = cv2.imread(cloth_path, cv2.IMREAD_UNCHANGED)
    if cloth_rgba is None:
        print("[TryOn] Could not load cloth image")
        return

    # Ensure BGRA
    if cloth_rgba.shape[2] == 3:
        cloth_rgba = cv2.cvtColor(cloth_rgba, cv2.COLOR_BGR2BGRA)

    # MediaPipe Pose
    mp_pose    = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    pose       = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[TryOn] Could not open webcam")
        _speak_safe("Sorry, I couldn't access the webcam.")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    window_name = "Nora — Virtual Try-On  |  R=Retry  C=Capture  Q=Quit"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)

    cloth_rgba_current = cloth_rgba.copy()
    no_body_frames     = 0
    MAX_NO_BODY        = 30   # warn after 1s without detection

    print("[TryOn] Live try-on started.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)   # mirror for natural experience
        h, w  = frame.shape[:2]
        rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = pose.process(rgb)
        output  = frame.copy()

        if results.pose_landmarks:
            no_body_frames = 0
            lm = results.pose_landmarks.landmark

            # ── Key landmarks ─────────────────────────────────────────────
            L_SHOULDER = mp_pose.PoseLandmark.LEFT_SHOULDER
            R_SHOULDER = mp_pose.PoseLandmark.RIGHT_SHOULDER
            L_HIP      = mp_pose.PoseLandmark.LEFT_HIP
            R_HIP      = mp_pose.PoseLandmark.RIGHT_HIP

            ls = lm[L_SHOULDER.value]
            rs = lm[R_SHOULDER.value]
            lh = lm[L_HIP.value]
            rh = lm[R_HIP.value]

            # Convert normalized → pixel
            def px(landmark):
                return (int(landmark.x * w), int(landmark.y * h))

            ls_px = px(ls)
            rs_px = px(rs)
            lh_px = px(lh)
            rh_px = px(rh)

            # ── Cloth placement calculations ──────────────────────────────
            shoulder_width = abs(rs_px[0] - ls_px[0])
            body_height    = abs(((lh_px[1] + rh_px[1]) // 2) - ((ls_px[1] + rs_px[1]) // 2))

            cloth_w = int(shoulder_width * 1.6)   # wider than shoulders
            cloth_h = int(body_height    * 1.5)   # torso height

            if cloth_w < 30 or cloth_h < 30:
                _draw_overlay(output, "Move closer to camera", w, h)
            else:
                # Top-left of cloth placement
                cloth_x = min(ls_px[0], rs_px[0]) - int(shoulder_width * 0.3)
                cloth_y = min(ls_px[1], rs_px[1]) - int(body_height    * 0.1)

                output = _overlay_cloth(output, cloth_rgba_current, cloth_x, cloth_y, cloth_w, cloth_h)

            # Draw subtle pose dots (optional)
            for point in [ls_px, rs_px, lh_px, rh_px]:
                cv2.circle(output, point, 5, (0, 201, 177), -1)

        else:
            no_body_frames += 1
            if no_body_frames > MAX_NO_BODY:
                _draw_overlay(output, "No body detected — stand in front of camera", w, h)

        # ── HUD ───────────────────────────────────────────────────────────
        _draw_hud(output, w, h)

        cv2.imshow(window_name, output)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q') or key == 27:
            break
        elif key == ord('c'):
            saved = _save_capture(output)
            _speak_safe(f"Captured and saved.")
            print(f"[TryOn] Saved: {saved}")
            _draw_overlay(output, f"Saved!", w, h)
            cv2.imshow(window_name, output)
            cv2.waitKey(1500)
        elif key == ord('r'):
            _speak_safe("Retrying cloth extraction. Please wait.")
            cv2.destroyWindow(window_name)
            cap.release()
            pose.close()
            handleVirtualTryOn("retry")
            return

    cap.release()
    cv2.destroyAllWindows()
    pose.close()
    print("[TryOn] Session ended.")


# ════════════════════════════════════════════════════════════════════════════
#  CLOTH OVERLAY — alpha blend cloth onto frame
# ════════════════════════════════════════════════════════════════════════════
def _overlay_cloth(frame, cloth_rgba, x, y, target_w, target_h):
    if target_w <= 0 or target_h <= 0:
        return frame

    try:
        # Resize cloth to target size
        cloth_resized = cv2.resize(cloth_rgba, (target_w, target_h), interpolation=cv2.INTER_LINEAR)

        fh, fw = frame.shape[:2]

        # Clip to frame bounds
        x1_f = max(0, x)
        y1_f = max(0, y)
        x2_f = min(fw, x + target_w)
        y2_f = min(fh, y + target_h)

        x1_c = x1_f - x
        y1_c = y1_f - y
        x2_c = x1_c + (x2_f - x1_f)
        y2_c = y1_c + (y2_f - y1_f)

        if x2_f <= x1_f or y2_f <= y1_f:
            return frame

        cloth_roi = cloth_resized[y1_c:y2_c, x1_c:x2_c]
        frame_roi = frame[y1_f:y2_f, x1_f:x2_f]

        if cloth_roi.shape[2] == 4:
            alpha   = cloth_roi[:, :, 3:4].astype(np.float32) / 255.0
            cloth_3 = cloth_roi[:, :, :3].astype(np.float32)
            frame_3 = frame_roi.astype(np.float32)

            blended = (alpha * cloth_3 + (1 - alpha) * frame_3).astype(np.uint8)
            frame[y1_f:y2_f, x1_f:x2_f] = blended
        else:
            frame[y1_f:y2_f, x1_f:x2_f] = cloth_roi[:, :, :3]

    except Exception as e:
        print(f"[TryOn] Overlay error: {e}")

    return frame


# ════════════════════════════════════════════════════════════════════════════
#  HUD + OVERLAYS
# ════════════════════════════════════════════════════════════════════════════
def _draw_hud(frame, w, h):
    # Semi-transparent bottom bar
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h-50), (w, h), (30, 39, 97), -1)
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(frame, "Nora Virtual Try-On", (20, h-28), font, 0.6, (0, 201, 177), 2)
    cv2.putText(frame, "C = Capture  |  R = Retry  |  Q = Quit", (w//2 - 150, h-28), font, 0.55, (200, 200, 200), 1)


def _draw_overlay(frame, message, w, h):
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, h//2 - 35), (w, h//2 + 35), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_w, _ = cv2.getTextSize(message, font, 0.8, 2)[0]
    cv2.putText(frame, message, ((w - text_w) // 2, h//2 + 10), font, 0.8, (0, 201, 177), 2)


# ════════════════════════════════════════════════════════════════════════════
#  SAVE CAPTURE
# ════════════════════════════════════════════════════════════════════════════
def _save_capture(frame):
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUT_DIR, f"tryon_{ts}.jpg")
    cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return path


# ════════════════════════════════════════════════════════════════════════════
#  SAFE SPEAK (works even if eel is not active)
# ════════════════════════════════════════════════════════════════════════════
def _speak_safe(text):
    try:
        from engine.command import speak
        speak(text)
    except Exception:
        print(f"[TryOn] {text}")
