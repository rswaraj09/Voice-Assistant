import time
import re
import subprocess
import os
import pyautogui
import pyperclip
import pygetwindow as gw
import google.generativeai as genai
from engine.config import LLM_KEY
from engine.command import speak, takecommand

genai.configure(api_key=LLM_KEY)

CHROME_PATH       = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
GMAIL_COMPOSE_URL = "https://mail.google.com/mail/#compose"

pyautogui.FAILSAFE = True
pyautogui.PAUSE    = 0.5

#   EXACT CALIBRATED COORDINATES (1920x1080)
# Calibrated using calibrate_email.py on your actual Gmail compose window
TO_X      = 1265
TO_Y      = 454

SUBJECT_X = 1255
SUBJECT_Y = 512

BODY_X    = 1244
BODY_Y    = 572

SEND_X    = 1166
SEND_Y    = 1037


#  HELPER: Paste text via clipboard

def type_text(text: str):
    pyperclip.copy(text)
    time.sleep(0.4)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.6)


#   HELPER: Focus Chrome window
def focus_chrome():
    time.sleep(0.5)
    try:
        for keyword in ['Gmail', 'Chrome', 'Google']:
            windows = gw.getWindowsWithTitle(keyword)
            if windows:
                win = windows[0]
                win.restore()
                time.sleep(0.3)
                win.activate()
                time.sleep(0.8)
                win.maximize()
                time.sleep(0.5)
                print(f"[Email] Focused: {keyword}")
                return True
    except Exception as e:
        print(f"[Email] Focus error: {e}")
    return False


#   HELPER: Expand the compose window (click the expand icon)

def expand_compose_window():
    """
    The compose window opens minimized as 'New Message' bar at bottom-right.
    We need to click the expand (⤢) icon to make it full size.
    The expand icon is at top-right of the 'New Message' bar.
    On 1920x1080: New Message bar is at bottom-right ~(1135, 756)
    Expand icon is at ~(1351, 756)
    """
    print("[Email] Expanding compose window...")

    # First click the 'New Message' bar to open it
    # The bar title area is roughly at:
    new_msg_x = 1200  # center of New Message bar
    new_msg_y = 756   # y position of the bar

    print(f"[Email] Clicking New Message bar at ({new_msg_x}, {new_msg_y})")
    pyautogui.click(new_msg_x, new_msg_y)
    time.sleep(1)

    # Now click the expand/maximize icon (⤢) on the compose window
    # It's the arrow icon next to minimize/close at top of compose popup
    # On 1920x1080 when compose popup is open: expand is at ~(1351, 756)
    expand_x = 1351
    expand_y = 756
    print(f"[Email] Clicking expand icon at ({expand_x}, {expand_y})")
    pyautogui.click(expand_x, expand_y)
    time.sleep(2)

    speak("Compose window expanded.")


#   STEP 1: Ask for email address

def ask_email_address() -> str:
    speak("What is the recipient's email address? Say it like: example at gmail dot com")
    for attempt in range(3):
        raw = takecommand()
        print(f"[Email] Raw spoken: {raw}")
        if not raw:
            speak("I didn't catch that. Please say it again.")
            continue
        email = raw.strip().lower()
        email = email.replace(" at the rate of ", "@")
        email = email.replace(" at the rate ", "@")
        email = email.replace(" at ", "@")
        email = email.replace(" dot com", ".com")
        email = email.replace(" dot in", ".in")
        email = email.replace(" dot org", ".org")
        email = email.replace(" dot ", ".")
        email = email.replace(" ", "")
        email = re.sub(r'@+', '@', email)
        email = re.sub(r'\.+', '.', email)
        print(f"[Email] Cleaned email: {email}")
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            speak(f"Got it. Sending to {email}")
            return email
        else:
            speak("That doesn't look right. Please try again.")
    speak("Couldn't get a valid email. Cancelling.")
    return ""


#   STEP 2: Ask for subject

def ask_subject() -> str:
    speak("What is the subject of the email?")
    subject = takecommand()
    if not subject or subject.strip() == "":
        speak("Didn't catch the subject. Cancelling.")
        return ""
    speak(f"Subject is: {subject}")
    return subject.strip()


#   STEP 3: Generate email body using Gemini AI

def generate_email_body(subject: str) -> str:
    speak("Writing the email for you. One moment.")
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        prompt = f"""Write a professional email body for the subject: "{subject}"
Rules:
- Write ONLY the body text, nothing else
- Start with Dear Sir/Madam or appropriate greeting
- End with Regards on a new line
- Plain text only, no markdown, no bullet points
- Concise and professional
"""
        response = model.generate_content(prompt)
        body = response.text.strip()
        body = re.sub(r'\*+', '', body)
        body = re.sub(r'#+', '', body)
        print(f"[Email] Generated body:\n{body}")
        return body
    except Exception as e:
        print(f"[Email] Gemini error: {e}")
        speak("Had trouble writing the email body.")
        return ""


#   STEP 4: Open Chrome on Gmail compose URL

def open_chrome_gmail_compose():
    speak("Opening Gmail. Please wait and don't touch anything.")
    try:
        subprocess.Popen([CHROME_PATH, GMAIL_COMPOSE_URL])
    except FileNotFoundError:
        try:
            alt = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            subprocess.Popen([alt, GMAIL_COMPOSE_URL])
        except Exception:
            os.startfile(GMAIL_COMPOSE_URL)

    speak("Waiting for Gmail to load.")
    time.sleep(10)
    focus_chrome()
    time.sleep(2)

    # ── CLICK EXPAND ICON to make compose fullscreen ──────────────────────
    # The compose opens minimized as "New Message" bar at bottom-right
    # Expand icon (⤢) position on 1920x1080:
    speak("Expanding compose window.")
    print("[Email] Clicking expand icon on New Message bar")
    pyautogui.click(1351, 756)   # expand icon (⤢)
    time.sleep(2)
    focus_chrome()
    time.sleep(1)


#   STEP 5: Fill compose window

def fill_compose_window(recipient: str, subject: str, body: str) -> bool:
    try:
        speak("Filling in the email details.")
        focus_chrome()
        time.sleep(1)

        # ── Recipients ────────────────────────────────────────────────────
        speak("Entering recipient.")
        print(f"[Email] Clicking Recipients at ({TO_X}, {TO_Y})")
        pyautogui.click(TO_X, TO_Y)
        time.sleep(1)
        type_text(recipient)
        pyautogui.press('tab')
        time.sleep(1)

        # ── Subject ───────────────────────────────────────────────────────
        speak("Entering subject.")
        print(f"[Email] Clicking Subject at ({SUBJECT_X}, {SUBJECT_Y})")
        pyautogui.click(SUBJECT_X, SUBJECT_Y)
        time.sleep(1)
        type_text(subject)
        time.sleep(0.8)

        # ── Body ──────────────────────────────────────────────────────────
        speak("Writing email body.")
        print(f"[Email] Clicking Body at ({BODY_X}, {BODY_Y})")
        pyautogui.click(BODY_X, BODY_Y)
        time.sleep(1)
        type_text(body)
        time.sleep(0.5)

        speak("Email is ready. Please check the compose window.")
        return True

    except Exception as e:
        print(f"[Email] Fill error: {e}")
        import traceback
        traceback.print_exc()
        speak("Had trouble filling the email.")
        return False


#   STEP 6: Confirm and Send

def confirm_and_send(recipient: str, subject: str):
    speak(f"Email to {recipient} with subject {subject} is ready. Should I send it?")
    confirmation = takecommand()
    print(f"[Email] Confirmation: {confirmation}")

    if confirmation and any(w in confirmation.lower() for w in
                            ["yes", "yeah", "sure", "send", "ok", "okay", "yep"]):
        speak("Sending the email now.")
        focus_chrome()
        time.sleep(0.5)
        pyautogui.click(BODY_X, BODY_Y)
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'enter')
        time.sleep(2)
        speak(f"Email sent successfully to {recipient}!")
    else:
        speak("Okay, email cancelled. The compose window is still open.")


#   MAIN FUNCTION
def handleEmail():
    recipient = ask_email_address()
    if not recipient:
        return
    subject = ask_subject()
    if not subject:
        return
    body = generate_email_body(subject)
    if not body:
        return
    open_chrome_gmail_compose()
    success = fill_compose_window(recipient, subject, body)
    if not success:
        return
    confirm_and_send(recipient, subject)