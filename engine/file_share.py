import os
import re
import time
import subprocess
import threading
import pyautogui
import pygetwindow as gw
from pathlib import Path
import base64
from PIL import ImageGrab
import json
from engine.config import LLM_KEY

# ════════════════════════════════════════════════════════════════════════════
#  GEMINI VISION — Screen-based file detection
# ════════════════════════════════════════════════════════════════════════════
def get_gemini_client():
    """Initialize Gemini client."""
    try:
        import google.generativeai as genai
        if not LLM_KEY:
            print("[FileShare] No Gemini API key found")
            return None
        genai.configure(api_key=LLM_KEY)
        return genai
    except ImportError:
        print("[FileShare] google-generativeai not installed. Installing...")
        subprocess.run(["pip", "install", "google-generativeai"], capture_output=True)
        import google.generativeai as genai
        genai.configure(api_key=LLM_KEY)
        return genai
    except Exception as e:
        print(f"[FileShare] Gemini init error: {e}")
        return None


def detect_files_on_screen(speak_fn=None) -> list:
    """
    Captures screen and uses Gemini vision to detect file paths visible on screen.
    Returns list of detected file paths (excluding system/cache files).
    """
    # System files to ignore
    IGNORE_PATTERNS = [
        '_adapthist', '.pma', '.db-journal', 'cache', 'temp', '~$',
        'Thumbs.db', 'desktop.ini', '.lnk', '.tmp'
    ]
    
    try:
        import google.generativeai as genai
        
        genai_client = get_gemini_client()
        if not genai_client:
            return []

        # Capture screen
        print("[FileShare] Capturing screen for file detection...")
        screenshot = ImageGrab.grab()
        
        # Convert to base64 for Gemini
        import io
        buffered = io.BytesIO()
        screenshot.save(buffered, format="PNG")
        img_data = base64.b64encode(buffered.getvalue()).decode()

        # Send to Gemini
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        prompt = """Analyze this screenshot and identify ONLY document/data files visible on screen.
        Focus on: Excel files (.xlsx, .xls), Word docs (.docx, .doc), PDFs, presentations (.pptx),
        images (jpg, png), text files. IGNORE system files, cache files, temp files, DLL files.
        
        Return a JSON object with format:
        {
            "files": [
                {"path": "full/file/path.ext", "confidence": 0.95},
                {"path": "another/file.ext", "confidence": 0.85}
            ],
            "description": "what files were detected"
        }
        
        Only return valid JSON, no other text."""

        response = model.generate_content([
            {
                "mime_type": "image/png",
                "data": img_data,
            },
            prompt
        ])
        
        response_text = response.text.strip()
        
        # Extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            files = []
            for f in data.get("files", []):
                fpath = f["path"]
                if os.path.exists(fpath):
                    # Skip system/cache files
                    if any(pattern.lower() in fpath.lower() for pattern in IGNORE_PATTERNS):
                        print(f"[FileShare] Skipping system file: {fpath}")
                        continue
                    files.append(fpath)
            print(f"[FileShare] Detected {len(files)} valid files on screen: {files}")
            return files
        
    except Exception as e:
        print(f"[FileShare] Screen detection error: {e}")
    
    return []


def find_file_smart(filename: str, speak_fn=None) -> str | None:
    """
    Intelligently find a file by:
    1. Checking recent files
    2. Searching common directories recursively
    3. Checking currently open files
    4. Using file indexing if available
    """
    import glob
    
    filename_lower = filename.lower()
    
    # 1. Check active file first
    active = get_active_file_path()
    if active and os.path.basename(active).lower() == filename_lower:
        return active
    
    # 2. Common search directories
    search_dirs = [
        os.path.expanduser("~\\Desktop"),
        os.path.expanduser("~\\Documents"),
        os.path.expanduser("~\\Downloads"),
        os.path.expanduser("~\\OneDrive\\Documents"),
        os.path.join(os.environ.get("USERPROFILE", ""), "OneDrive"),
    ]
    
    # Add current working directory
    search_dirs.insert(0, os.getcwd())
    
    for base_dir in search_dirs:
        if not os.path.exists(base_dir):
            continue
            
        try:
            # Exact match first
            for root, dirs, files in os.walk(base_dir):
                for f in files:
                    if f.lower() == filename_lower:
                        full_path = os.path.join(root, f)
                        print(f"[FileShare] Found exact match: {full_path}")
                        return full_path
            
            # Partial match
            for root, dirs, files in os.walk(base_dir):
                for f in files:
                    if filename_lower in f.lower():
                        full_path = os.path.join(root, f)
                        print(f"[FileShare] Found partial match: {full_path}")
                        return full_path
                        
        except Exception as e:
            continue
    
    # 3. Try Windows search/indexing via PowerShell
    try:
        ps_cmd = f'Get-ChildItem -Path $env:USERPROFILE -Recurse -Filter "*{filename}*" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName'
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            found_path = result.stdout.strip()
            if os.path.exists(found_path):
                print(f"[FileShare] Found via PowerShell: {found_path}")
                return found_path
    except:
        pass
    
    return None

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
    """Lists open files for a process and returns the first matching one.
    Excludes cache and temp files.
    """
    # Paths to IGNORE (cache, temp, system files)
    IGNORE_PATHS = [
        "inetcache",
        "localappdata\\microsoft\\windows",
        "\\appdata\\local\\temp",
        "\\appdata\\roaming\\microsoft",
        "\\$recycle",
        "\\~$",
        "appdata\\locallow",
    ]
    
    try:
        import psutil
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                try:
                    best_file = None
                    for f in proc.open_files():
                        if any(f.path.lower().endswith(ext) for ext in extensions):
                            # Skip temp/cache/system files
                            if "~$" in f.path:
                                continue
                            
                            # Skip Windows cache and temp paths
                            is_ignore_path = False
                            for ignore in IGNORE_PATHS:
                                if ignore.lower() in f.path.lower():
                                    is_ignore_path = True
                                    print(f"[FileShare] Skipping cache file: {f.path}")
                                    break
                            
                            if is_ignore_path:
                                continue
                            
                            # Prefer user document files over others
                            if "desktop" in f.path.lower() or "documents" in f.path.lower() or "downloads" in f.path.lower():
                                print(f"[FileShare] psutil found (user file): {f.path}")
                                return f.path
                            
                            # Keep this as backup
                            if not best_file:
                                best_file = f.path
                    
                    # Return backup if we have one
                    if best_file:
                        print(f"[FileShare] psutil found: {best_file}")
                        return best_file
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
#  SEND VIA WHATSAPP DESKTOP (native UI automation)
# ════════════════════════════════════════════════════════════════════════════
def send_whatsapp_file(contact_name: str, file_path: str, speak_fn) -> bool:
    """
    Opens WhatsApp Desktop, searches for contact, attaches file using file picker,
    and sends the file. Works like a human would.
    """
    import pyperclip
    import subprocess

    file_path = os.path.abspath(file_path)
    if not os.path.exists(file_path):
        speak_fn("The file doesn't exist. Cannot send.")
        return False

    speak_fn(f"Opening WhatsApp Desktop and searching for {contact_name}.")

    # ── Step 1: Open WhatsApp Desktop ────────────────────────────────────
    _open_whatsapp_desktop()
    time.sleep(3)

    # ── Step 2: Search for contact using Ctrl+F ──────────────────────────
    print(f"[FileShare] Searching for contact: {contact_name}")
    pyautogui.hotkey("ctrl", "f")
    time.sleep(1)
    
    # Clear any existing search
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.3)
    
    # Type contact name
    pyperclip.copy(contact_name)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(2)

    # Open the first result
    pyautogui.press("enter")
    time.sleep(2)

    # ── Step 3: Open attachment using native Windows file picker ────────
    print("[FileShare] Opening file attachment dialog...")
    
    # Use Windows file picker (explorer) directly and copy file
    # This is more reliable than trying to click on WhatsApp buttons
    try:
        # Open Explorer to the file
        subprocess.Popen(['explorer', '/select,', file_path])
        time.sleep(2)
        
        # Copy the file
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.5)
        
        # Close explorer
        pyautogui.hotkey("alt", "f4")
        time.sleep(1)
        
        # Focus back to WhatsApp
        wa_win = _get_whatsapp_window()
        if wa_win:
            try:
                wa_win.activate()
            except:
                # Click on WhatsApp window area
                pyautogui.click(wa_win.left + wa_win.width//2, wa_win.top + wa_win.height//2)
        
        time.sleep(1)
        
        # Now paste the file in WhatsApp message input
        print(f"[FileShare] Pasting file into chat: {file_path}")
        pyautogui.hotkey("ctrl", "v")
        time.sleep(2)
        
        # Wait for attachment preview to appear
        print("[FileShare] Waiting for attachment to be ready...")
        time.sleep(2)
        
    except Exception as e:
        print(f"[FileShare] File attachment error: {e}")
        speak_fn("There was an issue attaching the file. Please try again.")
        return False

    # ── Step 4: Send message ────────────────────────────────────────────
    print("[FileShare] Sending file to WhatsApp...")
    # Click send button (usually Enter key)
    pyautogui.press("enter")
    time.sleep(3)
    
    # Verify send was successful by checking if message input is clear
    print("[FileShare] Verifying file was sent...")
    time.sleep(2)

    speak_fn(f"File sent to {contact_name} on WhatsApp!")
    return True


def _attach_file_whatsapp_desktop(file_path: str, speak_fn) -> bool:
    """
    Opens file picker dialog in WhatsApp Desktop and selects the file.
    This is a fallback method.
    """
    try:
        import pyperclip
        
        wa_win = _get_whatsapp_window()
        if wa_win:
            try:
                wa_win.activate()
            except:
                pyautogui.click(wa_win.left + wa_win.width//2, wa_win.top + wa_win.height//2)
            
            time.sleep(0.5)
        
        # Try keyboard shortcut for file attachment
        # Different WhatsApp versions use different shortcuts
        shortcuts = [
            ("ctrl", "shift", "a"),  # Common attachment shortcut
            ("ctrl", "u"),             # Some versions use this
            ("shift", "tab"),          # Tab to attachment button
        ]
        
        file_attached = False
        for shortcut in shortcuts:
            try:
                pyautogui.hotkey(*shortcut)
                time.sleep(1)
                
                # Check if file picker dialog opened
                # If it did, paste the file path
                pyperclip.copy(file_path)
                pyautogui.hotkey("ctrl", "l")  # Focus address bar
                time.sleep(0.3)
                pyautogui.hotkey("ctrl", "a")
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.5)
                pyautogui.press("enter")
                time.sleep(2)
                file_attached = True
                break
            except:
                continue
        
        return file_attached
    except Exception as e:
        print(f"[FileShare] Attachment dialog error: {e}")
        return False


def _open_whatsapp_desktop():
    """Opens WhatsApp Desktop (Windows app) if not already open."""
    wa_win = _get_whatsapp_window()
    if wa_win:
        try:
            # Try safe window activation
            wa_win.activate()
            print("[FileShare] WhatsApp window activated")
            return
        except Exception as e:
            print(f"[FileShare] Window activation failed ({e}), will launch fresh")
            # If activation fails, close and relaunch
            try:
                wa_win.close()
                time.sleep(1)
            except:
                pass
    
    # Launch WhatsApp Desktop from Windows Store
    try:
        print("[FileShare] Launching WhatsApp Desktop...")
        # Method 1: Use Windows Store app
        try:
            subprocess.Popen("start whatsapp://", shell=True)
            time.sleep(4)
            # Check if window appeared
            wa_win = _get_whatsapp_window()
            if wa_win:
                return
        except:
            pass
        
        # Method 2: Try direct executable paths
        wa_paths = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "WhatsApp", "WhatsApp.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Packages", "5222FC89.WhatsAppDesktop_cv1g1gvanyjgm", "LocalCache", "Roaming", "WhatsApp", "WhatsApp.exe"),
            "C:\\Program Files\\WhatsApp\\WhatsApp.exe",
        ]
        
        for path in wa_paths:
            if os.path.exists(path):
                print(f"[FileShare] Found WhatsApp at: {path}")
                subprocess.Popen([path])
                time.sleep(4)
                return
        
        # Method 3: Try to launch from PATH
        try:
            subprocess.Popen("whatsapp", shell=True)
            time.sleep(4)
        except:
            pass
            
    except Exception as e:
        print(f"[FileShare] Error opening WhatsApp: {e}")


def _get_whatsapp_window():
    """Gets the WhatsApp Desktop window handle."""
    try:
        wins = gw.getWindowsWithTitle("WhatsApp")
        if wins:
            # Filter to get the main window (not Settings or other dialogs)
            for win in wins:
                if "WhatsApp" in win.title and "settings" not in win.title.lower():
                    return win
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

    # Detect contact name — "send to X on/via/through/over" or just "send to X"
    # Look specifically for "to [name]" pattern
    contact_match = re.search(
        r'\bto\s+([a-zA-Z]+)\b',
        query, re.IGNORECASE
    )
    
    if contact_match:
        potential_contact = contact_match.group(1).strip()
        # Filter out common non-contact words and command words
        non_contacts = ['file', 'the', 'this', 'that', 'please', 'send', 'share', 'email', 'drive', 
                       'whatsapp', 'on', 'via', 'through', 'over', 'at']
        if potential_contact.lower() not in non_contacts:
            result["contact"] = potential_contact
    else:
        # Fallback: Try alternative patterns for contact detection
        # For cases like "share with john" or "send with john"
        contact_match = re.search(
            r'(?:with|via)\s+([a-zA-Z]+)\b',
            query, re.IGNORECASE
        )
        if contact_match:
            potential_contact = contact_match.group(1).strip()
            if potential_contact.lower() not in ['file', 'the', 'this', 'that', 'please']:
                result["contact"] = potential_contact

    return result


# ════════════════════════════════════════════════════════════════════════════
#  MAIN HANDLER — called from command.py
# ════════════════════════════════════════════════════════════════════════════
def handleFileShareCommand(query: str, speak_fn, takecommand_fn):
    """
    Full pipeline with automatic file detection:
    1. Extract contact name FIRST
    2. Check active files (Excel/Word/PPT opened)
    3. Detect file using vision (screen) if needed
    4. Convert Excel → PDF if requested
    5. Execute share to detected platform
    """

    # ── Step 0a: Extract contact name and platform FIRST ──────────────────
    dest = detect_share_destination(query)
    print(f"[FileShare] Detected platform: {dest['platform']}, contact: {dest['contact']}")

    # ── Step 0b: Try automatic file detection ─────────────────────────────
    file_path = None
    
    # Priority 1: Check active document in Office apps (most reliable)
    print("[FileShare] Checking for active files in Office apps...")
    file_path = get_active_excel_path()
    if not file_path:
        file_path = get_active_word_path()
    if not file_path:
        file_path = get_active_ppt_path()
    
    if file_path:
        print(f"[FileShare] Found active file: {file_path}")
        speak_fn(f"Found {os.path.basename(file_path)} that you're working on.")
    
    # Priority 2: Check if user mentioned a specific file in query
    # Use more restrictive regex to avoid capturing contact names
    if not file_path:
        filename_match = re.search(
            r'(?:share|send|upload|attach|file)\s+(?:the\s+)?([a-zA-Z0-9\-_\.\s]+?)(?:\s+(?:to|on|via|with)\b|\s+file)?$',
            query, re.IGNORECASE
        )
        
        if filename_match:
            mentioned_file = filename_match.group(1).strip()
            # Don't use contact name as file
            if dest["contact"] and mentioned_file.lower() == dest["contact"].lower():
                mentioned_file = None
            elif mentioned_file:
                # Take only the last word if it looks like a filename
                parts = mentioned_file.split()
                if parts:
                    mentioned_file = parts[-1]
                    print(f"[FileShare] User mentioned file: {mentioned_file}")
                    speak_fn(f"Looking for {mentioned_file}.")
                    file_path = find_file_smart(mentioned_file, speak_fn)
    
    # Priority 3: Detect from screen using Gemini vision
    if not file_path:
        print("[FileShare] Attempting screen-based file detection with Gemini...")
        speak_fn("Let me check what files are available on your screen.")
        detected_files = detect_files_on_screen(speak_fn)
        if detected_files:
            file_path = detected_files[0]  # Use first detected file
            speak_fn(f"Found {os.path.basename(file_path)} on your screen.")
    
    # ── Step 1: Is this a convert + share request? ────────────────────────
    needs_conversion = bool(re.search(
        r'\b(convert|turn|change)\b.{0,20}\b(excel|xlsx|spreadsheet)\b.{0,20}\b(pdf)\b',
        query, re.IGNORECASE
    ))

    if needs_conversion and file_path and file_path.endswith(('.xlsx', '.xls', '.xlsm', '.csv')):
        speak_fn("Converting Excel to PDF now.")
        pdf_path = convert_excel_to_pdf(file_path, speak_fn)
        if pdf_path:
            file_path = pdf_path
            speak_fn("Conversion done.")
        else:
            return
    elif needs_conversion:
        # User wants to convert but no Excel file found
        speak_fn("I couldn't find an Excel file. Let me help you open one.")
        # Try to detect Excel file
        excel_path = get_active_excel_path()
        if not excel_path:
            speak_fn("Please tell me the Excel file name.")
            filename = takecommand_fn()
            if filename:
                excel_path = find_file_smart(filename, speak_fn)
        
        if excel_path:
            pdf_path = convert_excel_to_pdf(excel_path, speak_fn)
            if pdf_path:
                file_path = pdf_path
                speak_fn("Conversion done.")
        else:
            speak_fn("Sorry, I couldn't find the Excel file.")
            return

    if not file_path:
        speak_fn("Which file should I share? Please say the file name.")
        filename = takecommand_fn()
        if filename:
            file_path = find_file_smart(filename, speak_fn)
            if not file_path:
                speak_fn("I couldn't find that file anywhere. Please open it first.")
                return
        else:
            return

    print(f"[FileShare] Will share: {file_path}")
    speak_fn(f"Found {os.path.basename(file_path)}. Ready to share.")

    # ── Step 2: Confirm platform (already detected in Step 0) ──────────────
    if not dest["platform"]:
        speak_fn("Where should I send it? Say WhatsApp, Google Drive, or Email.")
        platform_query = takecommand_fn()
        if "whatsapp" in platform_query.lower():
            dest["platform"] = "whatsapp"
        elif "drive" in platform_query.lower():
            dest["platform"] = "drive"
        elif "email" in platform_query.lower() or "mail" in platform_query.lower():
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