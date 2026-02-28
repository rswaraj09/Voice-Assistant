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

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
GMAIL_URL   = "https://mail.google.com"

pyautogui.FAILSAFE = True
pyautogui.PAUSE    = 0.6

#  HELPER: Paste text via clipboard (safe for special characters)

def type_text(text: str):
    pyperclip.copy(text)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.5)



#  HELPER: Focus Chrome window

def focus_chrome():
    """Bring Chrome window to front and maximize it."""
    time.sleep(1)
    try:
        # Find any Chrome window
        windows = gw.getWindowsWithTitle('Chrome')
        if not windows:
            windows = gw.getWindowsWithTitle('Gmail')
        if windows:
            win = windows[0]
            win.restore()
            win.activate()
            time.sleep(1)
            win.maximize()
            time.sleep(1)
            print("[Email] Chrome window focused.")
            return True
    except Exception as e:
        print(f"[Email] Focus error: {e}")

    # Fallback: click center of screen
    pyautogui.click(pyautogui.size()[0] // 2, pyautogui.size()[1] // 2)
    time.sleep(1)
    return False

#  STEP 1: Ask for email address

def ask_email_address() -> str:
    speak("What is the recipient's email address?")
    for attempt in range(3):
        raw = takecommand()
        print(f"[Email] Raw spoken: {raw}")
        if not raw:
            speak("I didn't catch that. Please say it again.")
            continue
        email = raw.strip().lower()
        email = email.replace(" at the rate ", "@")
        email = email.replace(" at ", "@")
        email = email.replace(" dot ", ".")
        email = email.replace(" ", "")
        email = re.sub(r'@+', '@', email)
        email = re.sub(r'\.+', '.', email)
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            speak(f"Got it. Email address is {email}")
            return email
        else:
            speak("That doesn't look right. Say it like: example at gmail dot com")
    speak("Couldn't get a valid email. Cancelling.")
    return ""

#  STEP 2: Ask for subject

def ask_subject() -> str:
    speak("What is the subject of the email?")
    subject = takecommand()
    if not subject or subject.strip() == "":
        speak("Didn't catch the subject. Cancelling.")
        return ""
    speak(f"Subject is: {subject}")
    return subject.strip()


#  STEP 3: Generate email body using Gemini AI

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


#  STEP 4: Open Chrome → Gmail

def open_chrome_gmail():
    speak("Opening Gmail in Chrome. Please wait.")
    try:
        subprocess.Popen([CHROME_PATH, GMAIL_URL])
    except FileNotFoundError:
        try:
            alt = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            subprocess.Popen([alt, GMAIL_URL])
        except Exception:
            os.startfile(GMAIL_URL)

    speak("Waiting for Gmail to load.")
    time.sleep(8)  # wait for Chrome + Gmail to fully load
    focus_chrome()
    time.sleep(2)


#  STEP 5: Compose email in Gmail
def compose_email(recipient: str, subject: str, body: str) -> bool:
    try:
        speak("Opening compose window.")

        # Make sure Chrome is focused
        focus_chrome()
        time.sleep(1)

        # Click the center of the Gmail page to make sure it has keyboard focus
        screen_w, screen_h = pyautogui.size()
        pyautogui.click(screen_w // 2, screen_h // 2)
        time.sleep(1)

        # Press 'c' to open Gmail Compose window
        pyautogui.press('c')
        time.sleep(3)  # wait for compose window to open

        speak("Filling recipient.")

        # Fill To field
        # Gmail compose To field is usually top-left of compose popup
        # Use Tab navigation: compose opens with To field already focused
        type_text(recipient)
        time.sleep(0.5)
        pyautogui.press('tab')  # → moves to Subject
        time.sleep(0.5)

        # Fill Subject
        speak("Filling subject.")
        type_text(subject)
        time.sleep(0.5)
        pyautogui.press('tab')  # → moves to Body
        time.sleep(0.5)

        # Fill Body
        speak("Writing the email body.")
        type_text(body)
        time.sleep(0.5)

        speak("Email is ready on your screen. Please check the compose window.")
        return True

    except Exception as e:
        print(f"[Email] Compose error: {e}")
        import traceback
        traceback.print_exc()
        speak("Had trouble filling the email. Please try again.")
        return False


#  STEP 6: Confirm and Send
def confirm_and_send(recipient: str, subject: str):
    speak(f"Email to {recipient} with subject {subject} is ready. Should I send it?")
    confirmation = takecommand()
    print(f"[Email] Confirmation: {confirmation}")

    if confirmation and any(w in confirmation.lower() for w in
                            ["yes", "yeah", "sure", "send", "ok", "okay", "yep"]):
        speak("Sending the email now.")
        focus_chrome()
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'enter')  # Gmail send shortcut
        time.sleep(2)
        speak(f"Email sent successfully to {recipient}!")
    else:
        speak("Okay, email cancelled. The compose window is still open if you want to send manually.")



#  MAIN FUNCTION
def handleEmail():
    # Step 1
    recipient = ask_email_address()
    if not recipient:
        return

    # Step 2
    subject = ask_subject()
    if not subject:
        return

    # Step 3
    body = generate_email_body(subject)
    if not body:
        return

    # Step 4: Open Chrome + Gmail BEFORE asking confirmation
    open_chrome_gmail()

    # Step 5: Fill compose window
    success = compose_email(recipient, subject, body)
    if not success:
        return

    # Step 6: Confirm and send
    confirm_and_send(recipient, subject)