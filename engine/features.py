import json
import os
import re
import sqlite3
import struct
import subprocess
import time
import threading
import webbrowser
from playsound import playsound
import eel
import pyaudio
import pyautogui
import base64
from engine.command import speak
from engine.config import ASSISTANT_NAME, LLM_KEY
import pywhatkit as kit
import pvporcupine
from engine.helper import extract_yt_term, markdown_to_text, remove_words
import google.generativeai as genai

HOTWORD_TRIGGER_FILE = "hotword_trigger.txt"

# ── Thread-safe SQLite ────────────────────────────────────────────────────
_local = threading.local()

def get_cursor():
    if not hasattr(_local, 'con'):
        _local.con = sqlite3.connect("nora.db")
        _local.cursor = _local.con.cursor()
    return _local.con, _local.cursor

_main_con = sqlite3.connect("nora.db")
_main_cursor = _main_con.cursor()


# ════════════════════════════════════════════════════════════════════════════
#  ASSISTANT SOUND
# ════════════════════════════════════════════════════════════════════════════
@eel.expose
def playAssistantSound():
    music_dir = "templates\\assets\\audio\\start_sound.mp3"
    playsound(music_dir)


# ════════════════════════════════════════════════════════════════════════════
#  CHECK HOTWORD — JS polls this as fallback
# ════════════════════════════════════════════════════════════════════════════
@eel.expose
def checkHotword():
    if os.path.exists(HOTWORD_TRIGGER_FILE):
        try:
            os.remove(HOTWORD_TRIGGER_FILE)
        except:
            pass
        return True
    return False


# ════════════════════════════════════════════════════════════════════════════
#  HOTWORD DETECTION — Process 2 ONLY
#  Does ONE thing: writes trigger file when hotword detected
#  Process 1 (trigger_watcher in main.py) handles everything else
# ════════════════════════════════════════════════════════════════════════════
def hotword():
    porcupine = None
    paud = None
    audio_stream = None
    try:
        porcupine = pvporcupine.create(keywords=["jarvis", "alexa"])
        paud = pyaudio.PyAudio()
        audio_stream = paud.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length
        )

        print("[Hotword] Listening for 'Jarvis'...")

        while True:
            keyword = audio_stream.read(porcupine.frame_length)
            keyword = struct.unpack_from("h" * porcupine.frame_length, keyword)
            keyword_index = porcupine.process(keyword)

            if keyword_index >= 0:
                print("[Hotword] Detected! Writing trigger...")
                with open(HOTWORD_TRIGGER_FILE, "w") as f:
                    f.write("trigger")
                time.sleep(2)  # prevent double triggers

    except Exception as e:
        print(f"[Hotword Error] {e}")
    finally:
        if porcupine is not None: porcupine.delete()
        if audio_stream is not None: audio_stream.close()
        if paud is not None: paud.terminate()


# ════════════════════════════════════════════════════════════════════════════
#  OPEN COMMAND
# ════════════════════════════════════════════════════════════════════════════
def openCommand(query):
    query = query.replace(ASSISTANT_NAME, "")
    query = query.replace("open", "")
    query = query.lower().strip()

    if query != "":
        try:
            con, cursor = get_cursor()
            cursor.execute('SELECT path FROM sys_command WHERE LOWER(name) IN (?)', (query,))
            results = cursor.fetchall()
            if results:
                speak("Opening " + query)
                os.startfile(results[0][0])
            else:
                cursor.execute('SELECT url FROM web_command WHERE LOWER(name) IN (?)', (query,))
                results = cursor.fetchall()
                if results:
                    speak("Opening " + query)
                    webbrowser.open(results[0][0])
                else:
                    speak("Opening " + query)
                    try:
                        os.system('start ' + query)
                    except:
                        speak("not found")
        except Exception as e:
            print(f"openCommand error: {e}")
            speak("something went wrong")


# ════════════════════════════════════════════════════════════════════════════
#  YOUTUBE
# ════════════════════════════════════════════════════════════════════════════
def PlayYoutube(query):
    search_term = extract_yt_term(query)
    speak("Playing " + search_term + " on YouTube")
    kit.playonyt(search_term)


# ════════════════════════════════════════════════════════════════════════════
#  FIND CONTACT
# ════════════════════════════════════════════════════════════════════════════
def findContact(query):
    match = re.search(r'to\s+([a-zA-Z\s]+?)(?:\s+on|\s*$)', query, re.IGNORECASE)
    if match:
        query = match.group(1).strip()
    else:
        words_to_remove = [ASSISTANT_NAME, 'make', 'a', 'to', 'phone', 'call',
                           'send', 'message', 'wahtsapp', 'whatsapp', 'video', 'msg', 'on']
        query = remove_words(query, words_to_remove)
    try:
        query = query.strip().lower()
        con, cursor = get_cursor()
        cursor.execute(
            "SELECT mobile_no FROM contacts WHERE LOWER(name) LIKE ? OR LOWER(name) LIKE ?",
            ('%' + query + '%', query + '%')
        )
        results = cursor.fetchall()
        mobile_number_str = str(results[0][0])
        if not mobile_number_str.startswith('+91'):
            mobile_number_str = '+91' + mobile_number_str
        return mobile_number_str, query
    except:
        speak('not exist in contacts')
        return 0, 0


# ════════════════════════════════════════════════════════════════════════════
#  WHATSAPP
# ════════════════════════════════════════════════════════════════════════════
def whatsApp(mobile_no, message, flag, name):
    from pipes import quote
    encoded_message = quote(message) if message else ""
    clean_no = mobile_no.replace(" ", "")
    whatsapp_url = f"whatsapp://send?phone={clean_no}&text={encoded_message}"
    subprocess.run(f'start "" "{whatsapp_url}"', shell=True)
    time.sleep(5)
    try:
        import pygetwindow as gw
        windows = gw.getWindowsWithTitle('WhatsApp')
        if windows:
            windows[0].activate()
            time.sleep(0.5)
    except Exception as e:
        print(f"Window focus error: {e}")
    if flag == 'message':
        time.sleep(2)
        pyautogui.press('enter')
        speak("Message sent successfully to " + name)


# ════════════════════════════════════════════════════════════════════════════
#  MOBILE CALL (ADB)
# ════════════════════════════════════════════════════════════════════════════
def makeCall(name, mobileNo):
    mobileNo = mobileNo.replace(" ", "")
    speak("Calling " + name)
    os.system('adb shell am start -a android.intent.action.CALL -d tel:' + mobileNo)


# ════════════════════════════════════════════════════════════════════════════
#  SEND SMS (ADB)
# ════════════════════════════════════════════════════════════════════════════
def sendMessage(message, mobileNo, name):
    from engine.helper import replace_spaces_with_percent_s, goback, keyEvent, tapEvents, adbInput
    message = replace_spaces_with_percent_s(message)
    mobileNo = replace_spaces_with_percent_s(mobileNo)
    speak("sending message")
    goback(4)
    time.sleep(1)
    keyEvent(3)
    tapEvents(136, 2220)
    tapEvents(819, 2192)
    adbInput(mobileNo)
    tapEvents(601, 574)
    tapEvents(390, 2270)
    adbInput(message)
    tapEvents(957, 1397)
    speak("message sent successfully to " + name)


# ════════════════════════════════════════════════════════════════════════════
#  GEMINI AI
# ════════════════════════════════════════════════════════════════════════════
def geminai(query):
    try:
        query = query.replace(ASSISTANT_NAME, "")
        query = query.replace("search", "")
        genai.configure(api_key=LLM_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(query)
        filter_text = markdown_to_text(response.text)
        speak(filter_text)
    except Exception as e:
        print("Error:", e)


# ════════════════════════════════════════════════════════════════════════════
#  EEL EXPOSED — UI FUNCTIONS
# ════════════════════════════════════════════════════════════════════════════
@eel.expose
def assistantName():
    return ASSISTANT_NAME


@eel.expose
def personalInfo():
    try:
        _main_cursor.execute("SELECT * FROM info")
        results = _main_cursor.fetchall()
        eel.getData(json.dumps(results[0]))
        return 1
    except:
        print("no data")


@eel.expose
def updatePersonalInfo(name, designation, mobileno, email, city):
    _main_cursor.execute("SELECT COUNT(*) FROM info")
    count = _main_cursor.fetchone()[0]
    if count > 0:
        _main_cursor.execute(
            'UPDATE info SET name=?, designation=?, mobileno=?, email=?, city=?',
            (name, designation, mobileno, email, city)
        )
    else:
        _main_cursor.execute(
            'INSERT INTO info (name, designation, mobileno, email, city) VALUES (?, ?, ?, ?, ?)',
            (name, designation, mobileno, email, city)
        )
    _main_con.commit()
    personalInfo()
    return 1


@eel.expose
def displaySysCommand():
    _main_cursor.execute("SELECT * FROM sys_command")
    results = _main_cursor.fetchall()
    eel.displaySysCommand(json.dumps(results))
    return 1


@eel.expose
def deleteSysCommand(id):
    _main_cursor.execute("DELETE FROM sys_command WHERE id = ?", (id,))
    _main_con.commit()


@eel.expose
def addSysCommand(key, value):
    _main_cursor.execute('INSERT INTO sys_command VALUES (?, ?, ?)', (None, key, value))
    _main_con.commit()


@eel.expose
def displayWebCommand():
    _main_cursor.execute("SELECT * FROM web_command")
    results = _main_cursor.fetchall()
    eel.displayWebCommand(json.dumps(results))
    return 1


@eel.expose
def checkUITrigger():
    import os
    UI_TRIGGER_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ui_trigger.txt")
    UI_TRIGGER_FILE = os.path.normpath(UI_TRIGGER_FILE)
    if os.path.exists(UI_TRIGGER_FILE):
        try:
            os.remove(UI_TRIGGER_FILE)
        except:
            pass
        return True
    return False


@eel.expose  
def showSiriWaveFromPython():
    pass  # JS handles this via checkUITrigger polling          

@eel.expose
def addWebCommand(key, value):
    _main_cursor.execute('INSERT INTO web_command VALUES (?, ?, ?)', (None, key, value))
    _main_con.commit()


@eel.expose
def deleteWebCommand(id):
    _main_cursor.execute("DELETE FROM web_command WHERE Id = ?", (id,))
    _main_con.commit()


@eel.expose
def displayPhoneBookCommand():
    _main_cursor.execute("SELECT * FROM contacts")
    results = _main_cursor.fetchall()
    eel.displayPhoneBookCommand(json.dumps(results))
    return 1


@eel.expose
def deletePhoneBookCommand(id):
    _main_cursor.execute("DELETE FROM contacts WHERE Id = ?", (id,))
    _main_con.commit()


@eel.expose
def InsertContacts(Name, MobileNo, Email, City):
    _main_cursor.execute(
        'INSERT INTO contacts VALUES (?, ?, ?, ?, ?)',
        (None, Name, MobileNo, Email, City)
    )
    _main_con.commit()


@eel.expose
def receivePDFUpload(filename, base64_data):
    """Receives the uploaded PDF from JS, saves to temp, signals converter."""
    try:
        from engine.pdf_to_excel import set_uploaded_pdf
        pdf_bytes = base64.b64decode(base64_data)
        tmp_dir   = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Temp", "JarvisPDF")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_path  = os.path.join(tmp_dir, filename)
        with open(tmp_path, "wb") as f:
            f.write(pdf_bytes)
        print(f"[PDF Upload] Saved to: {tmp_path}")
        set_uploaded_pdf(tmp_path)
        return tmp_path
    except Exception as e:
        print(f"[PDF Upload] Error: {e}")
        return ""