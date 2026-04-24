"""
file_share.py  — Jarvis File Sharing Module (Fixed & Improved)

Flow when user says "share this file to Didi on WhatsApp":
  1. detect_share_destination()  → platform="whatsapp", contact="Didi"
  2. If user named a file  → find_file_smart()
  3. Else → get_active_file_path() (COM / psutil)
  4. Else → gemini_detect_open_file_on_screen()  ← VISION FALLBACK
  5. Convert if needed, then send.
"""

import os
import re
import time
import subprocess
import threading
import glob
import io
import base64
import json

import pyautogui
import pygetwindow as gw
from PIL import ImageGrab

from engine.config import LLM_KEY


# ─────────────────────────────────────────────────────────────────────────────
#  GEMINI CLIENT
# ─────────────────────────────────────────────────────────────────────────────

def _get_gemini_model():
    """Returns an initialised Gemini GenerativeModel, or None on failure."""
    try:
        import google.generativeai as genai
    except ImportError:
        subprocess.run(["pip", "install", "google-generativeai"], capture_output=True)
        import google.generativeai as genai

    if not LLM_KEY:
        print("[FileShare] No Gemini API key in LLM_KEY.")
        return None

    try:
        genai.configure(api_key=LLM_KEY)
        return genai.GenerativeModel("gemini-2.0-flash-exp")
    except Exception as e:
        print(f"[FileShare] Gemini init error: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  GEMINI VISION — identify which file is open / being worked on on screen
# ─────────────────────────────────────────────────────────────────────────────

def gemini_detect_open_file_on_screen(speak_fn=None) -> str | None:
    """
    Takes a screenshot and asks Gemini Vision:
      "What document / file is open in the foreground application?"

    Returns the *filename* (e.g. "Sales Report Q3.xlsx") that Gemini identifies,
    or None.  The caller must then resolve this name to a full path via
    find_file_smart().

    We deliberately do NOT ask Gemini for a full path — it will hallucinate
    paths that don't exist.  We only ask for the filename as visible on screen
    (title bar / tab / watermark / header).
    """
    model = _get_gemini_model()
    if model is None:
        return None

    try:
        print("[FileShare] Capturing screen for Gemini Vision analysis...")
        screenshot = ImageGrab.grab()

        buf = io.BytesIO()
        screenshot.save(buf, format="PNG")
        img_b64 = base64.b64encode(buf.getvalue()).decode()

        prompt = """Look at this screenshot carefully.

Your task: identify the NAME of the file/document that is currently OPEN and
in the FOREGROUND (i.e., the active/focused window the user is working on).

Look for clues in:
- The title bar of the foreground window (e.g. "Sales_Report.xlsx - Microsoft Excel")
- Browser tabs (e.g. a PDF open in Chrome)
- The document header/watermark
- Any visible filename near the top of the active window

Return ONLY a JSON object — no markdown, no explanation:
{
  "filename": "exact filename with extension as shown on screen",
  "confidence": 0.95,
  "app": "application name, e.g. Microsoft Excel / Adobe Acrobat / Word"
}

If you cannot identify any open file with reasonable confidence, return:
{"filename": null, "confidence": 0, "app": null}"""

        response = model.generate_content([
            {"mime_type": "image/png", "data": img_b64},
            prompt,
        ])

        text = response.text.strip()
        # Strip ```json fences if present
        text = re.sub(r"```(?:json)?", "", text).strip().strip("`").strip()

        data = json.loads(text)
        filename = data.get("filename")
        confidence = data.get("confidence", 0)

        if filename and confidence >= 0.6:
            print(f"[FileShare] Gemini Vision identified: '{filename}' "
                  f"(confidence={confidence}, app={data.get('app')})")
            return filename
        else:
            print(f"[FileShare] Gemini Vision: no file identified (confidence={confidence})")
            return None

    except json.JSONDecodeError as e:
        print(f"[FileShare] Gemini returned non-JSON: {e}\nRaw: {text!r}")
    except Exception as e:
        print(f"[FileShare] Gemini Vision error: {e}")

    return None


# ─────────────────────────────────────────────────────────────────────────────
#  SMART FILE FINDER — resolves a filename to a full path
# ─────────────────────────────────────────────────────────────────────────────

_SEARCH_DIRS = [
    os.path.expanduser("~\\Desktop"),
    os.path.expanduser("~\\Documents"),
    os.path.expanduser("~\\Downloads"),
    os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive"),
    os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive", "Documents"),
    os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive", "Desktop"),
]


def find_file_smart(filename: str, speak_fn=None) -> str | None:
    """
    Intelligently locate *filename* on disk.

    Priority:
      1. Check currently active Office file (exact name match)
      2. Exact-name walk across common directories
      3. Partial-name walk
      4. PowerShell fallback (Windows file indexing)
    """
    filename_lower = filename.lower().strip()
    if not filename_lower:
        return None

    # 1. Quick check: is the active file this one?
    active = get_active_file_path()
    if active and os.path.basename(active).lower() == filename_lower:
        print(f"[FileShare] Active file matches query: {active}")
        return active

    search_dirs = [os.getcwd()] + [d for d in _SEARCH_DIRS if os.path.isdir(d)]

    # 2. Exact-name match
    for base in search_dirs:
        for root, _dirs, files in os.walk(base):
            for f in files:
                if f.lower() == filename_lower:
                    full = os.path.join(root, f)
                    print(f"[FileShare] Exact match: {full}")
                    return full

    # 3. Partial-name match (filename_lower is a substring)
    for base in search_dirs:
        for root, _dirs, files in os.walk(base):
            for f in files:
                if filename_lower in f.lower():
                    full = os.path.join(root, f)
                    print(f"[FileShare] Partial match: {full}")
                    return full

    # 4. PowerShell search (uses Windows Search index)
    try:
        ps = (
            f'Get-ChildItem -Path $env:USERPROFILE -Recurse '
            f'-Filter "*{filename}*" -ErrorAction SilentlyContinue '
            f'| Select-Object -First 1 -ExpandProperty FullName'
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=15,
        )
        found = result.stdout.strip()
        if result.returncode == 0 and found and os.path.exists(found):
            print(f"[FileShare] PowerShell found: {found}")
            return found
    except Exception as e:
        print(f"[FileShare] PowerShell search failed: {e}")

    print(f"[FileShare] Could not find: {filename}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  ACTIVE FILE DETECTION (COM / psutil / window title)
# ─────────────────────────────────────────────────────────────────────────────

_CACHE_IGNORE = [
    "inetcache", "localappdata\\microsoft\\windows",
    "\\appdata\\local\\temp", "\\appdata\\roaming\\microsoft",
    "\\$recycle", "\\~$", "appdata\\locallow",
]

_FILE_IGNORE_PATTERNS = [
    "_adapthist", ".pma", ".db-journal", "cache", "~$",
    "thumbs.db", "desktop.ini", ".lnk", ".tmp",
]


def _is_cache_path(path: str) -> bool:
    pl = path.lower()
    return any(p in pl for p in _CACHE_IGNORE)


def _get_active_file_psutil(process_name: str, extensions: list[str]) -> str | None:
    try:
        import psutil
        for proc in psutil.process_iter(["name"]):
            if not proc.info["name"]:
                continue
            if process_name.lower() not in proc.info["name"].lower():
                continue
            try:
                best = None
                for f in proc.open_files():
                    if not any(f.path.lower().endswith(ext) for ext in extensions):
                        continue
                    if "~$" in f.path or _is_cache_path(f.path):
                        continue
                    # Prefer user-facing directories
                    pl = f.path.lower()
                    if any(k in pl for k in ("desktop", "documents", "downloads", "onedrive")):
                        print(f"[FileShare] psutil (user dir): {f.path}")
                        return f.path
                    best = best or f.path
                if best:
                    print(f"[FileShare] psutil: {best}")
                    return best
            except Exception:
                pass
    except Exception:
        pass
    return None


def _title_to_path(title_fragment: str, extensions: list[str]) -> str | None:
    """Search common dirs for a filename extracted from a window title."""
    frag = title_fragment.strip()
    if not frag:
        return None
    for base in _SEARCH_DIRS:
        if not os.path.isdir(base):
            continue
        # Exact
        for root, _, files in os.walk(base):
            for f in files:
                if f.lower() == frag.lower():
                    return os.path.join(root, f)
        # Try adding known extensions
        if not any(frag.lower().endswith(e) for e in extensions):
            for ext in extensions:
                matches = glob.glob(
                    os.path.join(base, "**", frag + ext), recursive=True
                )
                if matches:
                    return matches[0]
    return None


def get_active_excel_path() -> str | None:
    # 1. COM
    try:
        import win32com.client
        xl = win32com.client.GetActiveObject("Excel.Application")
        wb = xl.ActiveWorkbook
        if wb and wb.FullName and os.path.exists(wb.FullName):
            print(f"[FileShare] Excel COM: {wb.FullName}")
            return wb.FullName
    except Exception:
        pass

    # 2. psutil
    path = _get_active_file_psutil("excel.exe", [".xlsx", ".xls", ".xlsm", ".csv"])
    if path:
        return path

    # 3. Window title
    try:
        for win in gw.getWindowsWithTitle("Excel"):
            name = win.title.split(" - ")[0].strip()
            path = _title_to_path(name, [".xlsx", ".xls", ".xlsm", ".csv"])
            if path:
                return path
    except Exception:
        pass
    return None


def get_active_word_path() -> str | None:
    try:
        import win32com.client
        word = win32com.client.GetActiveObject("Word.Application")
        doc = word.ActiveDocument
        if doc and doc.FullName and os.path.exists(doc.FullName):
            return doc.FullName
    except Exception:
        pass

    path = _get_active_file_psutil("winword.exe", [".docx", ".doc"])
    if path:
        return path

    try:
        for win in gw.getWindowsWithTitle("Word"):
            name = win.title.split(" - ")[0].strip()
            path = _title_to_path(name, [".docx", ".doc"])
            if path:
                return path
    except Exception:
        pass
    return None


def get_active_ppt_path() -> str | None:
    try:
        import win32com.client
        ppt = win32com.client.GetActiveObject("PowerPoint.Application")
        pres = ppt.ActivePresentation
        if pres and pres.FullName and os.path.exists(pres.FullName):
            return pres.FullName
    except Exception:
        pass

    return _get_active_file_psutil("powerpnt.exe", [".pptx", ".ppt"])


def get_active_file_path() -> str | None:
    """
    Returns path of currently open file (Excel → Word → PPT → foreground window).
    """
    for fn in (get_active_excel_path, get_active_word_path, get_active_ppt_path):
        path = fn()
        if path:
            return path

    # Foreground window title fallback
    try:
        active_win = gw.getActiveWindow()
        if active_win:
            match = re.search(
                r"([a-zA-Z0-9_\- ]+\.(pdf|docx|xlsx|pptx|png|jpg|txt|csv|xlsm))",
                active_win.title,
                re.IGNORECASE,
            )
            if match:
                fname = match.group(1).strip()
                for base in _SEARCH_DIRS:
                    candidate = os.path.join(base, fname)
                    if os.path.exists(candidate):
                        return candidate
    except Exception:
        pass

    return None


# ─────────────────────────────────────────────────────────────────────────────
#  EXCEL → PDF CONVERTER
# ─────────────────────────────────────────────────────────────────────────────

def _find_libreoffice() -> str | None:
    candidates = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    try:
        r = subprocess.run(["where", "soffice"], capture_output=True, text=True, timeout=3)
        if r.returncode == 0:
            return r.stdout.strip().split("\n")[0].strip()
    except Exception:
        pass
    return None


def convert_excel_to_pdf(excel_path: str, speak_fn) -> str | None:
    excel_path = os.path.abspath(excel_path)
    if not os.path.exists(excel_path):
        speak_fn("I couldn't find that Excel file.")
        return None

    pdf_path = os.path.splitext(excel_path)[0] + ".pdf"
    out_dir = os.path.dirname(excel_path)

    # Method 1: LibreOffice (headless)
    libre = _find_libreoffice()
    if libre:
        try:
            result = subprocess.run(
                [libre, "--headless", "--convert-to", "pdf", "--outdir", out_dir, excel_path],
                capture_output=True, timeout=60,
            )
            if result.returncode == 0 and os.path.exists(pdf_path):
                print(f"[FileShare] PDF via LibreOffice: {pdf_path}")
                return pdf_path
        except Exception as e:
            print(f"[FileShare] LibreOffice error: {e}")

    # Method 2: win32com (MS Excel)
    try:
        import win32com.client
        xl_app = win32com.client.Dispatch("Excel.Application")
        xl_app.Visible = False
        wb = xl_app.Workbooks.Open(excel_path)
        wb.ExportAsFixedFormat(0, pdf_path)   # 0 = xlTypePDF
        wb.Close(False)
        xl_app.Quit()
        if os.path.exists(pdf_path):
            print(f"[FileShare] PDF via win32com: {pdf_path}")
            return pdf_path
    except Exception as e:
        print(f"[FileShare] win32com error: {e}")

    speak_fn("Couldn't convert — please install LibreOffice or Microsoft Excel.")
    return None


# ─────────────────────────────────────────────────────────────────────────────
#  WHATSAPP DESKTOP SENDER
# ─────────────────────────────────────────────────────────────────────────────

def _get_whatsapp_window():
    try:
        wins = gw.getWindowsWithTitle("WhatsApp")
        for w in wins:
            if "settings" not in w.title.lower():
                return w
        if wins:
            return wins[0]
    except Exception:
        pass
    return None


def _open_whatsapp_desktop():
    wa = _get_whatsapp_window()
    if wa:
        try:
            wa.activate()
            print("[FileShare] WhatsApp already open — activated.")
            return
        except Exception:
            pass

    print("[FileShare] Launching WhatsApp Desktop...")
    # Try URI scheme first (works for Windows Store app)
    subprocess.Popen("start whatsapp://", shell=True)
    time.sleep(5)
    if _get_whatsapp_window():
        return

    # Try known exe paths
    wa_paths = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "WhatsApp", "WhatsApp.exe"),
        r"C:\Program Files\WhatsApp\WhatsApp.exe",
    ]
    for p in wa_paths:
        if os.path.exists(p):
            subprocess.Popen([p])
            time.sleep(5)
            return

    subprocess.Popen("whatsapp", shell=True)
    time.sleep(5)


def _focus_whatsapp():
    wa = _get_whatsapp_window()
    if wa:
        try:
            wa.activate()
        except Exception:
            pyautogui.click(wa.left + wa.width // 2, wa.top + wa.height // 2)
        time.sleep(0.5)
    return wa


def send_whatsapp_file(contact_name: str, file_path: str, speak_fn) -> bool:
    """
    Opens WhatsApp Desktop → searches contact → attaches file via the
    native file-picker dialog (opened with Ctrl+Shift+A or the clip icon)
    → sends.
    """
    import pyperclip

    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        speak_fn("The file doesn't exist. Cannot send.")
        return False

    speak_fn(f"Opening WhatsApp and searching for {contact_name}.")

    # ── Step 1: Open WhatsApp ──────────────────────────────────────────────
    _open_whatsapp_desktop()
    time.sleep(3)

    wa = _focus_whatsapp()
    if not wa:
        speak_fn("Could not open WhatsApp Desktop. Is it installed?")
        return False

    # ── Step 2: Search for contact ─────────────────────────────────────────
    print(f"[FileShare] Searching contact: {contact_name}")
    pyautogui.hotkey("ctrl", "f")
    time.sleep(1.0)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.2)
    pyperclip.copy(contact_name)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(2.5)      # let search results populate
    pyautogui.press("enter")
    time.sleep(2.0)      # let chat open

    # ── Step 3: Open attach dialog (Ctrl+Shift+A is WhatsApp's shortcut) ──
    print("[FileShare] Opening attachment dialog...")
    _focus_whatsapp()
    pyautogui.hotkey("ctrl", "shift", "a")
    time.sleep(2.0)

    # If the native file picker didn't open, try clicking the paperclip
    # (visual coordinates are approximate — works best maximised)
    # As a fallback we just type the path into the Windows open-file dialog
    # which has an address bar we can reach with Ctrl+L.

    # ── Step 4: Type file path into the Windows Open dialog ───────────────
    # The Windows open-file dialog's address bar is accessible via Ctrl+L
    # (same as Explorer). We send the full absolute path and press Enter.
    print(f"[FileShare] Typing file path: {file_path}")
    time.sleep(0.5)

    # Try to focus the filename box directly first (works on most dialogs)
    pyperclip.copy(file_path)

    # Navigate the filename field
    pyautogui.hotkey("ctrl", "l")          # focus address/file bar
    time.sleep(0.4)
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.2)
    pyautogui.hotkey("ctrl", "v")          # paste full path
    time.sleep(0.3)
    pyautogui.press("enter")               # confirm selection
    time.sleep(2.5)                        # wait for attachment preview

    # ── Step 5: Send ──────────────────────────────────────────────────────
    print("[FileShare] Sending...")
    _focus_whatsapp()
    pyautogui.press("enter")
    time.sleep(3)

    speak_fn(f"File sent to {contact_name} on WhatsApp!")
    print(f"[FileShare] ✓ Sent '{os.path.basename(file_path)}' to {contact_name}")
    return True


# ─────────────────────────────────────────────────────────────────────────────
#  GOOGLE DRIVE UPLOADER
# ─────────────────────────────────────────────────────────────────────────────

def upload_to_google_drive(file_path: str, speak_fn) -> bool:
    import webbrowser
    import pyperclip

    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        speak_fn("The file doesn't exist. Cannot upload.")
        return False

    speak_fn("Opening Google Drive. Please wait...")
    webbrowser.open("https://drive.google.com/drive/my-drive")
    time.sleep(6)

    # Focus browser
    for win in gw.getAllWindows():
        if "Google Drive" in win.title:
            try:
                win.activate()
            except Exception:
                pass
            break

    time.sleep(1)

    # Google Drive keyboard shortcuts: 'c' → New menu, then 'u' → Upload file
    pyautogui.press("c")
    time.sleep(1.5)
    pyautogui.press("u")
    time.sleep(2.5)  # wait for file picker

    # Paste file path into the picker
    pyperclip.copy(file_path)
    pyautogui.hotkey("ctrl", "l")      # focus address bar of Open dialog
    time.sleep(0.4)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.3)
    pyautogui.press("enter")
    time.sleep(5)   # wait for upload

    speak_fn(f"File uploaded to Google Drive successfully!")
    return True


# ─────────────────────────────────────────────────────────────────────────────
#  EMAIL SENDER
# ─────────────────────────────────────────────────────────────────────────────

def send_file_via_email(contact_name: str, file_path: str, speak_fn) -> bool:
    from engine.email_handler import send_email_with_attachment
    speak_fn(f"Sending the file to {contact_name} via email.")
    try:
        result = send_email_with_attachment(contact_name, file_path)
        if result:
            speak_fn(f"File sent to {contact_name} via email successfully!")
        else:
            speak_fn("Email could not be sent. Check your email configuration.")
        return bool(result)
    except Exception as e:
        print(f"[FileShare] Email error: {e}")
        speak_fn("Something went wrong with the email.")
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  DESTINATION PARSER
# ─────────────────────────────────────────────────────────────────────────────

# Words that look like contact names but are NOT
_NON_CONTACTS = {
    "file", "the", "this", "that", "please", "send", "share", "email",
    "drive", "whatsapp", "telegram", "on", "via", "through", "over", "at",
    "google", "my", "a", "an", "it",
}

_PLATFORM_WORDS = {"whatsapp", "drive", "google drive", "email", "gmail", "mail", "telegram"}


def detect_share_destination(query: str) -> dict:
    """
    Returns:
      {
        "platform": "whatsapp" | "drive" | "email" | "telegram" | None,
        "contact":  str | None,
        "filename": str | None,   ← explicit filename user mentioned
      }
    """
    ql = query.lower()
    result = {"platform": None, "contact": None, "filename": None}

    # ── Platform ──────────────────────────────────────────────────────────
    if re.search(r"\bwhatsapp\b", ql):
        result["platform"] = "whatsapp"
    elif re.search(r"\b(google\s*drive|gdrive)\b", ql):
        result["platform"] = "drive"
    elif re.search(r"\b(email|gmail|mail)\b", ql):
        result["platform"] = "email"
    elif re.search(r"\btelegram\b", ql):
        result["platform"] = "telegram"

    # ── Contact — "to <Name>" where Name is a capitalised word not in blocklist ──
    # Pattern: "to <Word>" where <Word> starts with capital or is a name
    contact_match = re.search(
        r"\bto\s+([A-Z][a-zA-Z]*)(?:\s+on|\s+via|\s+through|\s+over|\s*$)",
        query,
    )
    if contact_match:
        cand = contact_match.group(1).strip()
        if cand.lower() not in _NON_CONTACTS:
            result["contact"] = cand
    else:
        # Fallback: any capitalised word after "to" not in blocklist
        contact_match = re.search(r"\bto\s+([a-zA-Z]+)\b", query)
        if contact_match:
            cand = contact_match.group(1).strip()
            if cand.lower() not in _NON_CONTACTS:
                result["contact"] = cand

    # ── Explicit filename — user mentions a specific file ─────────────────
    # Looks for words ending in a known extension
    file_match = re.search(
        r"\b([\w\-. ]+\.(?:xlsx?|docx?|pptx?|pdf|csv|txt|png|jpg))\b",
        query,
        re.IGNORECASE,
    )
    if file_match:
        result["filename"] = file_match.group(1).strip()

    return result


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN HANDLER
# ─────────────────────────────────────────────────────────────────────────────

def handleFileShareCommand(query: str, speak_fn, takecommand_fn):
    """
    Full pipeline:

    "jarvis share this file to Didi on WhatsApp"
      → Gemini vision detects open file → send_whatsapp_file()

    "jarvis send report.xlsx to John on WhatsApp"
      → find_file_smart("report.xlsx") → send_whatsapp_file()

    "jarvis upload this file to Google Drive"
      → detect active file / Gemini → upload_to_google_drive()
    """
    print(f"[FileShare] Query: {query!r}")

    # ── 0. Parse intent ────────────────────────────────────────────────────
    dest = detect_share_destination(query)
    print(f"[FileShare] platform={dest['platform']!r}, "
          f"contact={dest['contact']!r}, filename={dest['filename']!r}")

    # ── 1. Resolve file path ───────────────────────────────────────────────
    file_path = None

    # 1a. User explicitly named a file (highest priority)
    if dest["filename"]:
        speak_fn(f"Looking for {dest['filename']}.")
        file_path = find_file_smart(dest["filename"], speak_fn)
        if not file_path:
            speak_fn(f"I couldn't find {dest['filename']} on your computer.")

    # 1b. "this file" / "the file" → check active Office window (fast, accurate)
    if not file_path:
        print("[FileShare] Checking active Office window...")
        file_path = get_active_file_path()
        if file_path:
            print(f"[FileShare] Active file: {file_path}")
            speak_fn(f"I see you have {os.path.basename(file_path)} open.")

    # 1c. Gemini Vision — screenshot-based detection (fallback)
    if not file_path:
        print("[FileShare] Using Gemini Vision to detect open file...")
        speak_fn("Let me look at your screen to find the file.")
        detected_name = gemini_detect_open_file_on_screen(speak_fn)
        if detected_name:
            speak_fn(f"Gemini spotted {detected_name}. Searching for it...")
            file_path = find_file_smart(detected_name, speak_fn)
            if not file_path:
                speak_fn(f"I found {detected_name} on screen but can't locate it on disk.")

    # 1d. Ask user as last resort
    if not file_path:
        speak_fn("Which file should I share? Please say the file name.")
        spoken_name = takecommand_fn()
        if spoken_name:
            file_path = find_file_smart(spoken_name.strip(), speak_fn)
            if not file_path:
                speak_fn("I couldn't find that file. Please open it first and try again.")
                return
        else:
            return

    # ── 2. Optional Excel → PDF conversion ────────────────────────────────
    needs_pdf = bool(re.search(
        r"\b(convert|turn|change)\b.{0,25}\b(excel|xlsx|spreadsheet)\b.{0,25}\bpdf\b",
        query,
        re.IGNORECASE,
    ))
    if needs_pdf and file_path.lower().endswith((".xlsx", ".xls", ".xlsm", ".csv")):
        speak_fn("Converting Excel to PDF…")
        pdf = convert_excel_to_pdf(file_path, speak_fn)
        if pdf:
            file_path = pdf
            speak_fn("Conversion done.")
        else:
            return   # error already spoken inside convert_excel_to_pdf

    print(f"[FileShare] Final file: {file_path}")
    speak_fn(f"Got it — {os.path.basename(file_path)}.")

    # ── 3. Confirm platform if still unknown ──────────────────────────────
    if not dest["platform"]:
        speak_fn("Where should I send it? Say WhatsApp, Google Drive, or Email.")
        ans = (takecommand_fn() or "").lower()
        if "whatsapp" in ans:
            dest["platform"] = "whatsapp"
        elif "drive" in ans:
            dest["platform"] = "drive"
        elif "email" in ans or "mail" in ans:
            dest["platform"] = "email"
        else:
            speak_fn("I didn't catch that. Cancelling.")
            return

    # ── 4. Get contact name if needed ──────────────────────────────────────
    if dest["platform"] in ("whatsapp", "email") and not dest["contact"]:
        speak_fn("Who should I send it to?")
        dest["contact"] = (takecommand_fn() or "").strip()
        if not dest["contact"]:
            speak_fn("No contact name given. Cancelling.")
            return

    # ── 5. Execute (in a daemon thread so Jarvis stays responsive) ────────
    def _run():
        if dest["platform"] == "whatsapp":
            send_whatsapp_file(dest["contact"], file_path, speak_fn)

        elif dest["platform"] == "drive":
            upload_to_google_drive(file_path, speak_fn)

        elif dest["platform"] == "email":
            send_file_via_email(dest["contact"], file_path, speak_fn)

        else:
            speak_fn("I don't support that platform yet.")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    # Give the thread a moment to start before returning control
    time.sleep(0.3)