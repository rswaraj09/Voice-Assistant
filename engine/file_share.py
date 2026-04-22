import os
import re
import time
import subprocess
import threading
import pyautogui
import pygetwindow as gw
from pathlib import Path

# ════════════════════════════════════════════════════════════════════════════
#  EXCEL → PDF CONVERTER
# ════════════════════════════════════════════════════════════════════════════
def convert_excel_to_pdf(excel_path: str, speak_fn) -> str | None:
    """
    Converts .xlsx to .pdf using LibreOffice (silent, fastest method).
    Falls back to win32com (MS Office) if LibreOffice not found.
    Returns pdf_path or None.
    """
    excel_path = os.path.abspath(excel_path)
    if not os.path.exists(excel_path):
        speak_fn("I couldn't find that Excel file. Please check the path.")
        return None

    pdf_path = os.path.splitext(excel_path)[0] + ".pdf"
    out_dir  = os.path.dirname(excel_path)

    # ── Method 1: LibreOffice (silent, no UI) ────────────────────────────
    libre = _find_libreoffice()
    if libre:
        try:
            print(f"[FileShare] Converting via LibreOffice: {excel_path}")
            result = subprocess.run([
                libre,
                "--headless", "--convert-to", "pdf",
                "--outdir", out_dir, excel_path
            ], capture_output=True, timeout=30)
            if result.returncode == 0 and os.path.exists(pdf_path):
                print(f"[FileShare] PDF ready: {pdf_path}")
                return pdf_path
        except Exception as e:
            print(f"[FileShare] LibreOffice error: {e}")

    # ── Method 2: win32com (MS Excel must be installed) ──────────────────
    try:
        import win32com.client
        print(f"[FileShare] Converting via MS Excel COM...")
        excel_app = win32com.client.Dispatch("Excel.Application")
        excel_app.Visible = False
        wb = excel_app.Workbooks.Open(excel_path)
        wb.ExportAsFixedFormat(0, pdf_path)  # 0 = xlTypePDF
        wb.Close(False)
        excel_app.Quit()
        if os.path.exists(pdf_path):
            print(f"[FileShare] PDF ready: {pdf_path}")
            return pdf_path
    except Exception as e:
        print(f"[FileShare] win32com error: {e}")

    speak_fn("I couldn't convert the Excel file. Please make sure LibreOffice or Microsoft Excel is installed.")
    return None


def _find_libreoffice() -> str | None:
    candidates = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    # Try PATH
    try:
        result = subprocess.run(["where", "soffice"], capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0].strip()
    except:
        pass
    return None


# ════════════════════════════════════════════════════════════════════════════
#  DETECT ACTIVE EXCEL FILE — finds the currently open workbook
# ════════════════════════════════════════════════════════════════════════════
def get_active_excel_path() -> str | None:
    """Finds the path of the currently open Excel file via COM, psutil or title."""
    # 1. Try COM (Most reliable for focus detection)
    try:
        import win32com.client
        xl = win32com.client.GetActiveObject("Excel.Application")
        wb = xl.ActiveWorkbook
        if wb and wb.FullName and os.path.exists(wb.FullName):
            print(f"[FileShare] Excel COM found: {wb.FullName}")
            return wb.FullName
    except:
        pass

    # 2. Try psutil (Robust for finding what files are actually open by the process)
    path = _get_active_file_from_psutil("excel.exe", [".xlsx", ".xls", ".xlsm", ".csv"])
    if path: return path

    # 3. Try Window Title matching + Search
    try:
        import pygetwindow as gw
        for win in gw.getWindowsWithTitle("Excel"):
            title = win.title
            filename = title.split(" - ")[0].strip()
            if not filename: continue

            # Search common locations recursively
            search_dirs = [
                os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive"),
                os.path.expanduser("~\\Documents"),
                os.path.expanduser("~\\Desktop"),
                os.path.expanduser("~\\Downloads"),
            ]
            
            exts = [".xlsx", ".xls", ".xlsm", ".csv"]
            for d in search_dirs:
                if not os.path.exists(d): continue
                # Search recursively for this filename
                import glob
                matches = glob.glob(os.path.join(d, "**", filename), recursive=True)
                if matches: return matches[0]
                
                # Try adding extensions if missing
                if not any(filename.lower().endswith(e) for e in exts):
                    for ext in exts:
                        matches = glob.glob(os.path.join(d, "**", filename + ext), recursive=True)
                        if matches: return matches[0]
    except Exception as e:
        print(f"[FileShare] get_active_excel_path error: {e}")
    return None


def _get_active_file_from_psutil(process_name, extensions):
    """Lists open files for a process and returns the first matching one."""
    try:
        import psutil
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                try:
                    for f in proc.open_files():
                        if any(f.path.lower().endswith(ext) for ext in extensions):
                            # Skip temp files or system files
                            if "~$" in f.path: continue
                            print(f"[FileShare] psutil found: {f.path}")
                            return f.path
                except: pass
    except: pass
    return None


def get_active_word_path() -> str | None:
    """Finds the path of the currently open Word document via COM, psutil or title."""
    try:
        import win32com.client
        word_app = win32com.client.GetActiveObject("Word.Application")
        doc = word_app.ActiveDocument
        if doc and doc.FullName and os.path.exists(doc.FullName):
            return doc.FullName
    except:
        pass
    
    path = _get_active_file_from_psutil("winword.exe", [".docx", ".doc"])
    if path: return path
        
    # Fallback to title
    try:
        import pygetwindow as gw
        for win in gw.getWindowsWithTitle("Word"):
            filename = win.title.split(" - ")[0].strip()
            if not filename: continue
            search_dirs = [os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive"), 
                           os.path.expanduser("~\\Documents")]
            for d in search_dirs:
                if not os.path.exists(d): continue
                import glob
                matches = glob.glob(os.path.join(d, "**", filename), recursive=True)
                if matches: return matches[0]
    except: pass
    return None


def get_active_ppt_path() -> str | None:
    """Finds the path of the currently open PowerPoint presentation via COM or psutil."""
    try:
        import win32com.client
        ppt_app = win32com.client.GetActiveObject("PowerPoint.Application")
        pres = ppt_app.ActivePresentation
        if pres and pres.FullName and os.path.exists(pres.FullName):
            return pres.FullName
    except: pass

    path = _get_active_file_from_psutil("powerpnt.exe", [".pptx", ".ppt"])
    return path


def get_active_file_path() -> str | None:
    """
    Detects any currently open file (Excel, Word, PDF, PPT) and returns its path.
    Priority: Excel -> Word -> PPT -> Foreground Window Title Match
    """
    # 1. Check Office Apps via COM (Most accurate)
    path = get_active_excel_path()
    if path: return path
    
    path = get_active_word_path()
    if path: return path
    
    path = get_active_ppt_path()
    if path: return path
    
    # 2. Fallback: Check Active Window Title for common file extensions
    try:
        import pygetwindow as gw
        active_win = gw.getActiveWindow()
        if active_win:
            title = active_win.title
            # Look for common patterns like "Filename.pdf - Adobe Acrobat" or "Image.png - Photos"
            match = re.search(r'([a-zA-Z0-9_\- ]+\.(pdf|docx|xlsx|pptx|png|jpg|txt|csv|xlsm))', title, re.IGNORECASE)
            if match:
                filename = match.group(1).strip()
                # Search common locations
                search_dirs = [
                    os.path.expanduser("~\\Desktop"),
                    os.path.expanduser("~\\Documents"),
                    os.path.expanduser("~\\Downloads"),
                    os.path.expanduser("~\\OneDrive\\Documents"),
                ]
                for d in search_dirs:
                    candidate = os.path.join(d, filename)
                    if os.path.exists(candidate):
                        return candidate
    except:
        pass
        
    return None


# ════════════════════════════════════════════════════════════════════════════
#  SEND VIA WHATSAPP DESKTOP (actual UI automation)
# ════════════════════════════════════════════════════════════════════════════
def send_whatsapp_file(contact_name: str, file_path: str, speak_fn) -> bool:
    """
    Opens WhatsApp Desktop, searches for contact, attaches file, sends.
    Uses pyautogui UI automation — WhatsApp Desktop must be installed.
    """
    import pyperclip

    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        speak_fn("The file doesn't exist. Cannot send.")
        return False

    speak_fn(f"Opening WhatsApp and searching for {contact_name}.")

    # 1. Open Explorer and select the file
    try:
        # Use a list for subprocess to handle spaces correctly
        subprocess.Popen(['explorer', '/select,', os.path.abspath(file_path)])
        time.sleep(2)
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.5)
        # Close explorer window
        pyautogui.hotkey("alt", "f4") 
    except Exception as e:
        print(f"[FileShare] Clipboard copy error: {e}")

    # ── Step 2: Open / focus WhatsApp Desktop ────────────────────────────
    _open_whatsapp()
    time.sleep(3)

    # ── Step 3: Focus the search box and find contact ────────────────────
    # In WA Desktop, Ctrl+F focuses search. 
    pyautogui.hotkey("ctrl", "f")
    time.sleep(1)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.press("backspace")
    
    pyperclip.copy(contact_name)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(2)

    # Press Enter to open the first result
    pyautogui.press("enter")
    time.sleep(2)

    # ── Step 4: Paste the file into the chat ──────────────────────────────
    # Since we copied the file earlier, Ctrl+V will attach it.
    pyautogui.hotkey("ctrl", "v")
    time.sleep(2)  # Wait for attachment preview

    # ── Step 5: Send ──────────────────────────────────────────────────────
    pyautogui.press("enter")
    time.sleep(1)

    speak_fn(f"File sent to {contact_name} on WhatsApp successfully!")
    return True

    speak_fn(f"File sent to {contact_name} on WhatsApp successfully!")
    return True


def _open_whatsapp():
    """Opens WhatsApp Desktop if not already open."""
    wa_win = _get_whatsapp_window()
    if wa_win:
        wa_win.activate()
        return
    # Launch WhatsApp
    local = os.environ.get("LOCALAPPDATA", "")
    wa_paths = [
        os.path.join(local, "WhatsApp", "WhatsApp.exe"),
        os.path.join(local, "Programs", "WhatsApp", "WhatsApp.exe"),
    ]
    for p in wa_paths:
        if os.path.exists(p):
            subprocess.Popen([p])
            time.sleep(5)
            return
    # Try shell
    subprocess.Popen("start whatsapp:", shell=True)
    time.sleep(5)


def _get_whatsapp_window():
    try:
        wins = gw.getWindowsWithTitle("WhatsApp")
        if wins:
            return wins[0]
    except:
        pass
    return None


# ════════════════════════════════════════════════════════════════════════════
#  UPLOAD TO GOOGLE DRIVE (browser automation)
# ════════════════════════════════════════════════════════════════════════════
def upload_to_google_drive(file_path: str, speak_fn) -> bool:
    """
    Opens Google Drive in Chrome, uploads the file using drag-drop API
    via pyautogui — no OAuth needed, uses your already logged-in session.
    """
    import webbrowser
    import pyperclip

    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        speak_fn("The file doesn't exist. Cannot upload.")
        return False

    speak_fn("Opening Google Drive. Please wait while I upload the file.")

    # ── Step 1: Open Google Drive ─────────────────────────────────────────
    webbrowser.open("https://drive.google.com/drive/my-drive")
    time.sleep(5)   # wait for Drive to load

    # ── Step 2: Focus Chrome window ──────────────────────────────────────
    chrome_win = None
    for win in gw.getAllWindows():
        if "Google Drive" in win.title and ("Chrome" in win.title or "Brave" in win.title or "Edge" in win.title):
            chrome_win = win
            break
    if not chrome_win:
        # Just use the last active browser window
        time.sleep(2)
        pyautogui.hotkey("alt", "tab")
        time.sleep(1)

    # ── Step 3: Use keyboard shortcut to open file upload ─────────────────
    # Google Drive shortcut: press 'c' to open New menu, then 'u' for upload
    pyautogui.press("c")
    time.sleep(1.5)
    pyautogui.press("u")           # "Upload file"
    time.sleep(2)

    # ── Step 4: File picker dialog — paste path ───────────────────────────
    pyperclip.copy(file_path)
    pyautogui.hotkey("ctrl", "a")
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.5)
    pyautogui.press("enter")
    time.sleep(4)   # wait for upload

    speak_fn(f"File uploaded to Google Drive successfully!")
    return True


# ════════════════════════════════════════════════════════════════════════════
#  SEND VIA EMAIL
# ════════════════════════════════════════════════════════════════════════════
def send_file_via_email(contact_name: str, file_path: str, speak_fn) -> bool:
    """Send file as email attachment using your existing email_handler."""
    from engine.email_handler import send_email_with_attachment
    speak_fn(f"Sending the file to {contact_name} via email.")
    try:
        result = send_email_with_attachment(contact_name, file_path)
        if result:
            speak_fn(f"File sent to {contact_name} via email successfully!")
        else:
            speak_fn("Email could not be sent. Please check your email configuration.")
        return result
    except Exception as e:
        print(f"[FileShare] Email error: {e}")
        speak_fn("Something went wrong with the email.")
        return False


# ════════════════════════════════════════════════════════════════════════════
#  DETECT SHARE DESTINATION FROM QUERY
# ════════════════════════════════════════════════════════════════════════════
def detect_share_destination(query: str) -> dict:
    """
    Returns: {
        'platform': 'whatsapp' | 'drive' | 'email' | 'telegram' | None,
        'contact': str | None
    }
    """
    query_lower = query.lower()
    result = {"platform": None, "contact": None}

    # Detect platform
    if re.search(r'\bwhatsapp\b', query_lower):
        result["platform"] = "whatsapp"
    elif re.search(r'\b(google\s*drive|drive)\b', query_lower):
        result["platform"] = "drive"
    elif re.search(r'\b(email|mail|gmail)\b', query_lower):
        result["platform"] = "email"
    elif re.search(r'\btelegram\b', query_lower):
        result["platform"] = "telegram"

    # Detect contact name — "send to X on" or "send to X via"
    contact_match = re.search(
        r'\b(?:send|share|forward)\b.{0,10}\bto\s+([a-zA-Z\s]+?)(?:\s+on|\s+via|\s+through|\s+over|\s*$)',
        query, re.IGNORECASE
    )
    if contact_match:
        result["contact"] = contact_match.group(1).strip()

    return result


# ════════════════════════════════════════════════════════════════════════════
#  MAIN HANDLER — called from command.py
# ════════════════════════════════════════════════════════════════════════════
def handleFileShareCommand(query: str, speak_fn, takecommand_fn):
    """
    Full pipeline:
    1. Convert Excel → PDF if requested
    2. Detect share destination (WhatsApp / Drive / Email)
    3. Get contact name if needed
    4. Execute share
    """

    # ── Step 1: Is this a convert + share request? ────────────────────────
    needs_conversion = bool(re.search(
        r'\b(convert|turn|change)\b.{0,20}\b(excel|xlsx|spreadsheet)\b.{0,20}\b(pdf)\b',
        query, re.IGNORECASE
    ))

    file_path = None

    if needs_conversion:
        speak_fn("Let me find your active Excel file.")
        excel_path = get_active_excel_path()

        if not excel_path:
            speak_fn("I couldn't detect an open Excel file. Please tell me the file name.")
            filename = takecommand_fn()
            if filename:
                search_dirs = [
                    os.path.expanduser("~\\Desktop"),
                    os.path.expanduser("~\\Documents"),
                    os.path.expanduser("~\\Downloads"),
                ]
                for d in search_dirs:
                    candidate = os.path.join(d, filename)
                    if os.path.exists(candidate):
                        excel_path = candidate
                        break

        if not excel_path:
            speak_fn("Sorry, I couldn't find the Excel file.")
            return

        speak_fn("Converting Excel to PDF now.")
        file_path = convert_excel_to_pdf(excel_path, speak_fn)
        if not file_path:
            return
        speak_fn("Conversion done.")
    else:
        # User wants to share an existing file — try to detect active one first
        speak_fn("Let me see what you're working on.")
        file_path = get_active_file_path()
        
        if not file_path:
            speak_fn("Which file should I share? Please say the file name.")
            filename = takecommand_fn()
            if filename:
                search_dirs = [
                    os.path.expanduser("~\\Desktop"),
                    os.path.expanduser("~\\Documents"),
                    os.path.expanduser("~\\Downloads"),
                ]
                for d in search_dirs:
                    # Check for exact matches and fuzzy matches
                    for f in os.listdir(d):
                        if filename.lower() in f.lower():
                            file_path = os.path.join(d, f)
                            break
                    if file_path:
                        break
        
        if not file_path:
            speak_fn("I couldn't find the file you mentioned. Please open it first or provide a full path.")
            return

        speak_fn(f"Found {os.path.basename(file_path)}.")

    # ── Step 2: Detect where to send ─────────────────────────────────────
    dest = detect_share_destination(query)

    if not dest["platform"]:
        speak_fn("Where should I send it? Say WhatsApp, Google Drive, or Email.")
        platform_query = takecommand_fn()
        if "whatsapp" in platform_query:
            dest["platform"] = "whatsapp"
        elif "drive" in platform_query:
            dest["platform"] = "drive"
        elif "email" in platform_query or "mail" in platform_query:
            dest["platform"] = "email"
        else:
            speak_fn("I didn't catch that. Cancelling.")
            return

    # ── Step 3: Get contact name if needed ────────────────────────────────
    if dest["platform"] in ["whatsapp", "email"] and not dest["contact"]:
        speak_fn("Who should I send it to?")
        dest["contact"] = takecommand_fn()

    # ── Step 4: Execute ───────────────────────────────────────────────────
    if dest["platform"] == "whatsapp":
        threading.Thread(
            target=send_whatsapp_file,
            args=(dest["contact"], file_path, speak_fn),
            daemon=True
        ).start()

    elif dest["platform"] == "drive":
        threading.Thread(
            target=upload_to_google_drive,
            args=(file_path, speak_fn),
            daemon=True
        ).start()

    elif dest["platform"] == "email":
        threading.Thread(
            target=send_file_via_email,
            args=(dest["contact"], file_path, speak_fn),
            daemon=True
        ).start()

    else:
        speak_fn("I don't support that platform yet.")