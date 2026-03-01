"""
WhatsApp Call Handler
=====================
Flow:
1. Open WhatsApp (if not already open)
2. Press Ctrl+F to open search
3. Type contact name
4. Press Enter to open the contact chat
5. Click call button → dropdown → voice/video
"""

import time
import subprocess
import pyautogui
import pygetwindow as gw
import pyperclip
from engine.command import speak

# ── CALIBRATED COORDINATES (your 1920x1080 screen) ───────────────────────────
CALL_BTN_X  = 1711
CALL_BTN_Y  = 77
VOICE_OPT_X = 1475
VOICE_OPT_Y = 211
VIDEO_OPT_X = 1673
VIDEO_OPT_Y = 210


# ════════════════════════════════════════════════════════════════════════════
#  HELPER: Open WhatsApp
# ════════════════════════════════════════════════════════════════════════════
def open_whatsapp():
    """Always open WhatsApp via URL to ensure it launches and is ready."""
    import os
    print("[WhatsApp] Opening WhatsApp...")
    # Use whatsapp:// URL to open the app
    subprocess.run('start "" "whatsapp://"', shell=True)
    speak("Opening WhatsApp.")
    time.sleep(6)  # wait for WhatsApp to fully launch


# ════════════════════════════════════════════════════════════════════════════
#  HELPER: Focus WhatsApp window
# ════════════════════════════════════════════════════════════════════════════
def focus_whatsapp():
    try:
        windows = gw.getWindowsWithTitle('WhatsApp')
        if windows:
            win = windows[0]
            win.restore()
            time.sleep(0.3)
            win.activate()
            time.sleep(0.8)
            win.maximize()
            time.sleep(0.5)
            print("[WhatsApp] Window focused.")
            return True
    except Exception as e:
        print(f"[WhatsApp] Focus error: {e}")
    return False


# ════════════════════════════════════════════════════════════════════════════
#  HELPER: Search and open contact
# ════════════════════════════════════════════════════════════════════════════
def search_and_open_contact(name: str):
    """
    Use Ctrl+F to search for contact by name,
    navigate using keyboard only — no coordinate clicking.
    Tab moves into results, Down selects first chat, Enter opens it.
    """
    print(f"[WhatsApp] Searching for contact: {name}")

    # Press Ctrl+F to open search box
    pyautogui.hotkey('ctrl', 'f')
    time.sleep(1)

    # Clear any existing search text
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.3)

    # Type contact name via clipboard
    pyperclip.copy(name)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(3)  # wait for search results to fully load

    # Press Tab twice to move focus to first chat result
    pyautogui.press('tab')
    time.sleep(0.4)
    pyautogui.press('tab')
    time.sleep(0.4)

    # Press Enter to open the chat
    pyautogui.press('enter')
    time.sleep(2)

    print(f"[WhatsApp] Opened chat for: {name}")


# ════════════════════════════════════════════════════════════════════════════
#  MAKE VOICE CALL
# ════════════════════════════════════════════════════════════════════════════
def makeWhatsAppVoiceCall(mobile_no, name):
    speak(f"Calling {name} on WhatsApp.")

    # Step 1: Open WhatsApp
    open_whatsapp()

    # Step 2: Focus window
    focus_whatsapp()
    time.sleep(1)

    # Step 3: Search and open contact
    search_and_open_contact(name)
    time.sleep(2)

    # Step 4: Re-focus WhatsApp to make sure it's active
    focus_whatsapp()
    time.sleep(1)

    # Step 5: Click main call button
    print(f"[WhatsApp] Clicking call button at ({CALL_BTN_X}, {CALL_BTN_Y})")
    pyautogui.click(CALL_BTN_X, CALL_BTN_Y)
    time.sleep(2)  # wait for dropdown to appear

    # Step 6: Click Voice call from dropdown
    print(f"[WhatsApp] Clicking voice option at ({VOICE_OPT_X}, {VOICE_OPT_Y})")
    pyautogui.click(VOICE_OPT_X, VOICE_OPT_Y)
    time.sleep(1)
    speak(f"Voice call started with {name}.")


# ════════════════════════════════════════════════════════════════════════════
#  MAKE VIDEO CALL
# ════════════════════════════════════════════════════════════════════════════
def makeWhatsAppVideoCall(mobile_no, name):
    speak(f"Starting video call with {name} on WhatsApp.")

    # Step 1: Open WhatsApp
    open_whatsapp()

    # Step 2: Focus window
    focus_whatsapp()
    time.sleep(1)

    # Step 3: Search and open contact
    search_and_open_contact(name)
    time.sleep(2)

    # Step 4: Re-focus WhatsApp to make sure it's active
    focus_whatsapp()
    time.sleep(1)

    # Step 5: Click main call button
    print(f"[WhatsApp] Clicking call button at ({CALL_BTN_X}, {CALL_BTN_Y})")
    pyautogui.click(CALL_BTN_X, CALL_BTN_Y)
    time.sleep(2)  # wait for dropdown to appear

    # Step 6: Click Video call from dropdown
    print(f"[WhatsApp] Clicking video option at ({VIDEO_OPT_X}, {VIDEO_OPT_Y})")
    pyautogui.click(VIDEO_OPT_X, VIDEO_OPT_Y)
    time.sleep(1)
    speak(f"Video call started with {name}.")