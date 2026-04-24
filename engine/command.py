import re
import asyncio
import edge_tts
import pygame
import pyttsx3
import os
import io
import json
import hashlib
import subprocess
import time
import webbrowser
import speech_recognition as sr
import eel
import threading


#   Global state
_interrupted = False
_paused_text = ""
_conversation_history = []
MAX_HISTORY = 10

#   Voice config
VOICE = "en-US-AvaNeural"
RATE  = "+0%"
PITCH = "+0Hz"

#   Paths
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(BASE_DIR, "..")
CACHE_DIR   = os.path.join(PROJECT_DIR, "cache", "tts_cache")
WIN_APP_CACHE = os.path.join(PROJECT_DIR, "cache", "win_app_cache.json")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(os.path.join(PROJECT_DIR, "cache"), exist_ok=True)

#   Common environment paths
_LOCAL  = os.environ.get("LOCALAPPDATA", "")
_ROAMING = os.environ.get("APPDATA", "")
_PROG   = r"C:\Program Files"
_PROG86 = r"C:\Program Files (x86)"

#   WIN APP MAP — name → full path or exe name

WIN_APP_MAP = {
    "notepad":              "notepad.exe",
    "calculator":           "calc.exe",
    "paint":                "mspaint.exe",
    "task manager":         "taskmgr.exe",
    "file explorer":        "explorer.exe",
    "explorer":             "explorer.exe",
    "cmd":                  "cmd.exe",
    "command prompt":       "cmd.exe",
    "terminal":             "wt.exe",
    "windows terminal":     "wt.exe",
    "control panel":        "control.exe",
    "registry":             "regedit.exe",
    "device manager":       "devmgmt.msc",
    "disk management":      "diskmgmt.msc", 
    "word":        os.path.join(_PROG, "Microsoft Office", "root", "Office16", "WINWORD.EXE"),
    "excel":       os.path.join(_PROG, "Microsoft Office", "root", "Office16", "EXCEL.EXE"),
    "powerpoint":  os.path.join(_PROG, "Microsoft Office", "root", "Office16", "POWERPNT.EXE"),
    "outlook":     os.path.join(_PROG, "Microsoft Office", "root", "Office16", "OUTLOOK.EXE"),
    "chrome":       os.path.join(_PROG, "Google", "Chrome", "Application", "chrome.exe"),
    "google chrome":os.path.join(_PROG, "Google", "Chrome", "Application", "chrome.exe"),
    "firefox":      os.path.join(_PROG, "Mozilla Firefox", "firefox.exe"),
    "edge":         os.path.join(_PROG, "Microsoft", "Edge", "Application", "msedge.exe"),
    "brave":        os.path.join(_LOCAL, "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
    "opera":        os.path.join(_ROAMING, "Opera Software", "Opera Stable", "opera.exe"),
    "vs code":              os.path.join(_LOCAL, "Programs", "Microsoft VS Code", "Code.exe"),
    "vscode":               os.path.join(_LOCAL, "Programs", "Microsoft VS Code", "Code.exe"),
    "visual studio code":   os.path.join(_LOCAL, "Programs", "Microsoft VS Code", "Code.exe"),
    "cursor":               os.path.join(_LOCAL, "Programs", "cursor", "Cursor.exe"),
    "notepad++":            os.path.join(_PROG, "Notepad++", "notepad++.exe"),
    "sublime":              os.path.join(_PROG, "Sublime Text", "sublime_text.exe"),
    "sublime text":         os.path.join(_PROG, "Sublime Text", "sublime_text.exe"),
    "pycharm":              os.path.join(_PROG, "JetBrains", "PyCharm Community Edition", "bin", "pycharm64.exe"),
    "android studio":       os.path.join(_LOCAL, "Programs", "Android Studio", "bin", "studio64.exe"),
    "git bash":             os.path.join(_PROG, "Git", "git-bash.exe"),
    "discord":   os.path.join(_LOCAL, "Discord", "Update.exe"),
    "slack":     os.path.join(_LOCAL, "slack", "slack.exe"),
    "zoom":      os.path.join(_ROAMING, "Zoom", "bin", "Zoom.exe"),
    "teams":     os.path.join(_LOCAL, "Microsoft", "Teams", "current", "Teams.exe"),
    "skype":     os.path.join(_ROAMING, "Microsoft", "Skype for Desktop", "Skype.exe"),
    "telegram":  os.path.join(_ROAMING, "Telegram Desktop", "Telegram.exe"),
    "spotify":  os.path.join(_ROAMING, "Spotify", "Spotify.exe"),
    "vlc":      os.path.join(_PROG, "VideoLAN", "VLC", "vlc.exe"),
    "obs":      os.path.join(_PROG, "obs-studio", "bin", "64bit", "obs64.exe"),
    "obs studio": os.path.join(_PROG, "obs-studio", "bin", "64bit", "obs64.exe"),
    "postman":  os.path.join(_LOCAL, "Postman", "Postman.exe"),
    "steam":    os.path.join(_PROG86, "Steam", "steam.exe"),
    "7zip":     os.path.join(_PROG, "7-Zip", "7zFM.exe"),
    "winrar":   os.path.join(_PROG, "WinRAR", "WinRAR.exe"),
    "anydesk":  os.path.join(_PROG, "AnyDesk", "AnyDesk.exe"),
    "teamviewer": os.path.join(_PROG, "TeamViewer", "TeamViewer.exe"),
}


#   WINDOWS APP CACHE

def _load_win_cache():
    try:
        if os.path.exists(WIN_APP_CACHE):
            with open(WIN_APP_CACHE, "r") as f:
                return json.load(f)
    except:
        pass
    return {}


def _save_win_cache(cache):
    try:
        with open(WIN_APP_CACHE, "w") as f:
            json.dump(cache, f, indent=2)
    except:
        pass


def _cache_win_app(app_name, path_or_id):
    cache = _load_win_cache()
    cache[app_name.lower()] = path_or_id
    _save_win_cache(cache)
    print(f"[WinCache] Saved: {app_name} → {path_or_id}")


#   4-TIER APP FINDER

def _find_win_app(app_name):
    """
    Tier 1: WIN_APP_MAP  — instant dict, verifies full path exists
    Tier 2: Cache file   — instant JSON read
    Tier 3: Get-StartApps (Store + registered apps)
    Tier 4: where command (PATH apps)
    Returns (path_or_id, kind) where kind = 'exe' | 'appid'
    """
    key = app_name.lower().strip()

    #   Tier 1: WIN_APP_MAP
    if key in WIN_APP_MAP:
        val = WIN_APP_MAP[key]
        if os.path.isabs(val):
            # Full path — check if file exists
            if os.path.exists(val):
                print(f"[WinFind] Tier 1 full path: {val}")
                return val, "exe"
            else:
                print(f"[WinFind] Tier 1 path not found: {val} — trying next tiers")
        else:
            # Just exe name — pass as hint but continue to find full path
            print(f"[WinFind] Tier 1 exe hint: {val}")
            # Try PATH directly
            result = subprocess.run(
                f'where "{val}"', shell=True,
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0 and result.stdout.strip():
                full = result.stdout.strip().split('\n')[0].strip()
                print(f"[WinFind] Tier 1 + where: {full}")
                _cache_win_app(key, full)
                return full, "exe"

    #   Tier 2: Cache file
    cache = _load_win_cache()
    if key in cache:
        cached = cache[key]
        # Verify cached path still exists
        if cached.startswith("appid:") or os.path.exists(cached):
            print(f"[WinFind] Tier 2 cache: {cached}")
            if cached.startswith("appid:"):
                return cached, "appid"
            return cached, "exe"
        else:
            # Stale cache — remove and continue
            del cache[key]
            _save_win_cache(cache)

    #   Tier 3: Get-StartApps (Store + all registered apps)
    try:
        result = subprocess.run(
            f'powershell -command "Get-StartApps | Where-Object {{$_.Name -like \'*{app_name}*\'}} | Select-Object -First 1 -ExpandProperty AppID"',
            shell=True, capture_output=True, text=True, timeout=5
        )
        app_id = result.stdout.strip()
        if app_id:
            print(f"[WinFind] Tier 3 Store: {app_id}")
            full_id = f"appid:{app_id}"
            _cache_win_app(key, full_id)
            return full_id, "appid"
    except:
        pass

    #   Tier 4: where command
    exe = app_name + ".exe"
    try:
        result = subprocess.run(
            f'where "{exe}"', shell=True,
            capture_output=True, text=True, timeout=3
        )
        if result.returncode == 0 and result.stdout.strip():
            path = result.stdout.strip().split('\n')[0].strip()
            print(f"[WinFind] Tier 4 where: {path}")
            _cache_win_app(key, path)
            return path, "exe"
    except:
        pass

    return None, None


#  OPEN WINDOWS APP

def openApp(app_name):
    app_name = app_name.strip()
    speak(f"Opening {app_name}.")
    print(f"[openApp] Looking for: {app_name}")

    path, kind = _find_win_app(app_name)

    if path and kind:
        try:
            if kind == "appid":
                app_id = path.replace("appid:", "")
                subprocess.Popen(f'explorer shell:AppsFolder\\{app_id}', shell=True)
                print(f"[openApp] Launched via AppID: {app_id}")
            else:
                subprocess.Popen([path])
                print(f"[openApp] Launched via exe: {path}")
            return True
        except Exception as e:
            print(f"[openApp] Launch error: {e}")
            speak(f"Found {app_name} but couldn't open it.")
            return False
    else:
        speak(f"Sir, {app_name} is not installed. Would you like me to help install it?")
        response = takecommand()
        if response and any(w in response for w in ["yes", "yeah", "sure", "okay", "ok", "please", "download", "install"]):
            _download_app(app_name)
        else:
            speak("Alright, no problem.")
        return False

def _download_app(app_name):
    import pyautogui
    search_url = f"https://www.google.com/search?q={app_name.replace(' ', '+')}+download+for+windows"
    speak(f"Opening the download page for {app_name}.")
    webbrowser.open(search_url)
    time.sleep(4)  # wait for full page load
    try:
        # Click on the page body first to give it focus
        # Screen center is safe — avoids clicking any link
        screen_width, screen_height = pyautogui.size()
        pyautogui.click(screen_width // 2, screen_height // 2)
        time.sleep(0.5)

        # Now Tab once — focus moves to first link on page
        pyautogui.press('tab')
        time.sleep(0.3)

        # Enter to open it
        pyautogui.press('enter')
        time.sleep(2)

        speak(f"I've opened the download page for {app_name}. You can proceed with the installation.")
    except Exception as e:
        print(f"[download] Error: {e}")
        speak(f"I've opened the search results for {app_name}. Please click on the official website.")


#   SPEAK
async def _generate_audio(text):
    communicate = edge_tts.Communicate(text, voice=VOICE)
    audio_bytes = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes += chunk["data"]
        if _interrupted:
            break
    return audio_bytes


def _get_cache_path(text):
    key = hashlib.md5(f"{VOICE}{RATE}{text}".encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{key}.mp3")


def _play_audio_bytes(audio_bytes):
    global _interrupted
    audio_io = io.BytesIO(audio_bytes)
    pygame.mixer.music.load(audio_io, "mp3")
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        if _interrupted:
            pygame.mixer.music.stop()
            break
        time.sleep(0.05)


def speak(text, use_cache=True):
    global _interrupted, _paused_text

    text = str(text).strip()
    if not text:
        return

    _interrupted = False

    try:
        eel.DisplayMessage(text)
        eel.receiverText(text)
        eel.noraAvatarState("speaking")
    except:
        pass

    cache_path = _get_cache_path(text)

    try:
        pygame.mixer.init(frequency=24000)

        if use_cache and os.path.exists(cache_path):
            print(f"[speak] Cache hit")
            with open(cache_path, "rb") as f:
                audio_bytes = f.read()
        else:
            print(f"[speak] Generating audio...")
            audio_bytes = asyncio.run(_generate_audio(text))
            if use_cache and audio_bytes:
                with open(cache_path, "wb") as f:
                    f.write(audio_bytes)

        if audio_bytes and not _interrupted:
            _play_audio_bytes(audio_bytes)

    except Exception as e:
        print(f"[speak] Edge TTS error: {e} — falling back to pyttsx3")
        try:
            # Run pyttsx3 in a separate process/thread to avoid loop errors
            def _fallback():
                try:
                    engine = pyttsx3.init('sapi5')
                    voices = engine.getProperty('voices')
                    engine.setProperty('voice', voices[1].id if len(voices) > 1 else voices[0].id)
                    engine.setProperty('rate', 185)
                    engine.say(text)
                    engine.runAndWait()
                except:
                    pass
            threading.Thread(target=_fallback).start()
        except Exception as e2:
            print(f"[speak] Fallback error: {e2}")
    finally:
        try:
            pygame.mixer.quit()
        except:
            pass
        try:
            eel.noraAvatarState("idle")
        except:
            pass

    _paused_text = ""


def interrupt_speech():
    global _interrupted
    _interrupted = True


def speak_resume():
    global _paused_text
    if _paused_text:
        remaining = _paused_text
        _paused_text = ""
        speak(remaining)


def precache_common_phrases():
    phrases = [
        "Hello, Welcome Sir, How can I Help You",
        "Okay, see you later!",
        "Fresh start! What's on your mind?",
        "Should I use WhatsApp or mobile?",
        "What should I say?",
        "Sure, continuing!",
        "Nothing to continue!",
        "Oops, something went wrong!",
    ]
    def _cache():
        for phrase in phrases:
            cache_path = _get_cache_path(phrase)
            if not os.path.exists(cache_path):
                try:
                    audio_bytes = asyncio.run(_generate_audio(phrase))
                    if audio_bytes:
                        with open(cache_path, "wb") as f:
                            f.write(audio_bytes)
                except:
                    pass
    threading.Thread(target=_cache, daemon=True).start()



#  TAKE COMMAND

def takecommand():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print('listening....')
        try:
            eel.DisplayMessage('listening....')
        except:
            pass
        r.pause_threshold = 1
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source, 10, 6)
    try:
        print('recognizing')
        try:
            eel.DisplayMessage('recognizing....')
        except:
            pass
        query = r.recognize_google(audio, language='en-in')
        print(f"user said: {query}")
        try:
            eel.DisplayMessage(query)
            eel.senderText(query)
        except:
            pass
        time.sleep(0.3)
    except Exception as e:
        return ""
    return query.lower()


def is_phone_command(query):
    return bool(re.search(r'\b(phone|mobile|android)\b', query))


def extract_app_name(query, *remove_words):
    words_to_remove = list(remove_words) + ['on', 'my', 'the', 'phone', 'mobile',
                                              'android', 'laptop', 'windows', 'computer',
                                              'pc', 'please', 'jarvis', 'nora', 'hey']
    pattern = r'\b(' + '|'.join(words_to_remove) + r')\b'
    app = re.sub(pattern, '', query, flags=re.IGNORECASE).strip()
    return re.sub(r'\s+', ' ', app).strip()


def _is_ml_request(query):
    """
    Returns True if the query is asking for an AI/ML project.
    Checks for ML-specific keywords to distinguish from generic web app requests.
    """
    q = query.lower()
 
    # Strong ML signals — any single one triggers ML mode
    strong_signals = [
        "machine learning", "ml model", "ai model", "train a model", "train the model",
        "deep learning", "neural network", "random forest", "regression model",
        "classification model", "train and test", "pickle", "sklearn", "scikit",
        "predict using ml", "ml project", "ai project",
    ]
    for signal in strong_signals:
        if signal in q:
            return True
 
    # Combination signals — need BOTH an action + a task
    action_words  = ["create", "make", "build", "generate", "develop", "train"]
    ml_task_words = [
        "predict", "prediction", "classifier", "regression",
        "sentiment", "detection", "diagnosis", "clustering",
        "recommendation", "forecasting", "spam", "fraud",
        "price prediction", "house price", "stock price",
        "churn prediction", "cancer detection", "heart disease",
    ]
    has_action = any(w in q for w in action_words)
    has_task   = any(t in q for t in ml_task_words)
 
    return has_action and has_task


def _is_file_share_request(query):
    has_action = any(w in query for w in [
        "convert", "share", "send", "forward", "upload", "attach"
    ])
    has_target = any(w in query for w in [
        "whatsapp", "telegram", "email", "gmail", "google drive",
        "drive", "bluetooth", "slack", "discord"
    ])
    has_file = any(w in query for w in [
        "excel", "spreadsheet", "pdf", "word", "document",
        "file", "sheet", "ppt", "presentation", "image", "photo"
    ])
    return (has_action and has_target) or (has_action and has_file and has_target)



#  AI CONVERSATION
def chat_with_nora(query):
    global _conversation_history
    from engine.config import LLM_KEY
    from engine.helper import markdown_to_text
    import google.generativeai as genai

    _conversation_history.append({"role": "user", "parts": [query]})
    if len(_conversation_history) > MAX_HISTORY * 2:
        _conversation_history = _conversation_history[-(MAX_HISTORY * 2):]

    system_prompt = """You are Nora, a friendly, witty, and intelligent AI voice assistant. 
You talk like a close friend — casual, warm, and natural. Keep responses SHORT (1-3 sentences max) 
since this is a voice conversation. Be direct, fun, and human. 
Don't use bullet points, markdown, or long explanations unless asked.
Remember the conversation context and refer back to it naturally."""

    try:
        genai.configure(api_key=LLM_KEY)
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=system_prompt
        )
        chat = model.start_chat(history=_conversation_history[:-1])
        response = chat.send_message(query, stream=True)

        buffer = ""
        full_reply = ""

        for chunk in response:
            if _interrupted:
                break
            chunk_text = markdown_to_text(chunk.text) if chunk.text else ""
            buffer += chunk_text
            full_reply += chunk_text

            sentences = re.split(r'(?<=[.!?])\s+', buffer)
            if len(sentences) > 1:
                to_speak = " ".join(sentences[:-1]).strip()
                buffer = sentences[-1]
                if to_speak:
                    speak(to_speak, use_cache=False)

        if buffer.strip() and not _interrupted:
            speak(buffer.strip(), use_cache=False)

        _conversation_history.append({"role": "model", "parts": [full_reply]})

    except Exception as e:
        print(f"[Chat] Error: {e}")
        try:
            genai.configure(api_key=LLM_KEY)
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(f"{system_prompt}\n\nUser: {query}\nNora:")
            speak(markdown_to_text(response.text).strip(), use_cache=False)
        except:
            speak("Sorry, couldn't think of a response right now!")


def clear_conversation():
    global _conversation_history
    _conversation_history = []



def process_query(query):
    if not query or query.strip() == "":
        return False

    try:
        #  SPECIAL NOTES MODE — handled before general modes
        if re.search(r'\b(start|enter|activate|open)\s+notes?\s+mode\b', query.lower()):
            from engine.notes_mode import handleNotesMode
            handleNotesMode()
            return True

        # MODE SYSTEM — checked early so "open X mode" isn't eaten by generic open handler
        if re.search(r'\bmodes?\b', query):
            from engine.modes import handle_mode_command
            if handle_mode_command(query):
                return True

        #  NEWS — route before chat fallback
        if re.search(r'\b(news|headlines|trending)\b', query):
            from engine.news_aggregator import handle_news_command
            if handle_news_command(query):
                return True

        #   AVATAR
        if re.search(r'\bavatars?\b', query):
            from engine.avatar_generator import handle_avatar_command
            if handle_avatar_command(query):
                return True

        if re.search(r'\b(stop|go back|home|cancel|goodbye|bye|exit)\b', query):
            speak("Okay, see you later!")
            return False

        elif re.search(r'\b(continue|resume|sorry for interruption|go on)\b', query):
            if _paused_text:
                speak("Sure, continuing!")
                speak(_paused_text)
            else:
                speak("Nothing to continue!")
            return True

        elif re.search(r'\b(forget|clear|reset|new conversation|start over)\b', query):
            clear_conversation()
            speak("Fresh start! What's on your mind?")
            return True

        elif "email" in query or "send mail" in query or "send an email" in query:
            from engine.email_handler import handleEmail
            handleEmail()
            return True

        elif "on youtube" in query or "play on youtube" in query:
            from engine.features import PlayYoutube
            PlayYoutube(query)
            return False

        elif "close" in query and is_phone_command(query):
            from engine.adb_controller import closeApp
            closeApp(extract_app_name(query, 'close'))
            return True

        elif "open" in query:
            if is_phone_command(query):
                from engine.adb_controller import openApp as adb_openApp
                adb_openApp(extract_app_name(query, 'open'))
            else:
                app_name = extract_app_name(query, 'open')
                openApp(app_name)
            return False

        #  PPT GENERATION
        elif any(w in query for w in [
            "create a ppt", "make a ppt", "generate a ppt", "build a ppt",
            "create a presentation", "make a presentation", "generate presentation",
            "create ppt", "make ppt", "create powerpoint", "make powerpoint",
            "create slides", "make slides", "prepare a presentation",
            "prepare ppt", "build presentation"
        ]):
            from engine.ppt_generator import handlePPTGeneration
            handlePPTGeneration(query)
            return False

        #  IMAGE GENERATION
        elif re.search(
            r'\b(generate|create|draw|make|show)\b.{0,15}\b(image|picture|photo|wallpaper|illustration)\b'
            r'|'
            r'\bdraw\s+(?:a\s+)?(?:4k|realistic|hd)?\s*\w+',
            query, re.IGNORECASE
        ):
            from engine.image_generator import handleImageGeneration
            handleImageGeneration(query, speak)
            return False

        elif re.search(
            r'\b(convert|turn|change)\b.{0,20}\bpdf\b.{0,20}\b(excel|xlsx|spreadsheet)\b'
            r'|'
            r'\bpdf\b.{0,15}\b(to|into)\b.{0,10}\b(excel|xlsx|spreadsheet)\b',
            query, re.IGNORECASE
        ):
            from engine.pdf_to_excel import handlePDFToExcel
            threading.Thread(target=handlePDFToExcel, args=(speak,), daemon=True).start()
            return True

        #   ML / AI PROJECT GENERATION
        elif _is_ml_request(query):
            from engine.ml_project_generator import handleMLGeneration
            handleMLGeneration(query)
            return True

        elif re.search(
            r'\b(convert|send|share|forward|upload)\b.{0,30}'
            r'\b(excel|xlsx|pdf|spreadsheet|file|document)\b.{0,30}'
            r'\b(whatsapp|drive|email|mail|gmail|telegram|send|share)\b',
            query, re.IGNORECASE
        ):
            from engine.file_share import handleFileShareCommand
            threading.Thread(
                target=handleFileShareCommand,
                args=(query, speak, takecommand),
                daemon=True
            ).start()
            return True

        elif any(t in query for t in ["create a", "make a", "build a", "generate a", "write a",
                                       "create an", "make an", "build an", "generate code", "write code"]) \
        and any(t in query for t in ["page", "website", "script", "program", "app", "calculator",
                                      "form", "code", "html", "python", "javascript", "login", "game"]):
            from engine.code_generator import handleCodeGeneration
            handleCodeGeneration(query)
            return True

        elif any(w in query for w in ["volume up", "increase volume", "turn up volume", "increase the volume"]):
            match = re.search(r'(\d+)', query)
            if match:
                from engine.system_controls import setVolume
                setVolume(int(match.group()))
            else:
                from engine.system_controls import volumeUp
                volumeUp()
            return True

        elif any(w in query for w in ["volume down", "decrease volume", "turn down volume", "decrease the volume"]):
            match = re.search(r'(\d+)', query)
            if match:
                from engine.system_controls import setVolume
                setVolume(int(match.group()))
            else:
                from engine.system_controls import volumeDown
                volumeDown()
            return True

        elif "set volume" in query or "volume to" in query:
            from engine.system_controls import setVolume
            match = re.search(r'(\d+)', query)
            setVolume(int(match.group()) if match else 50)
            return True

        elif "unmute" in query:
            from engine.system_controls import unmuteVolume
            unmuteVolume()
            return True

        elif "mute" in query:
            from engine.system_controls import muteVolume
            muteVolume()
            return True

        elif any(w in query for w in ["brightness up", "increase brightness", "brighter", "increase the brightness"]):
            match = re.search(r'(\d+)', query)
            if match:
                from engine.system_controls import setBrightness
                setBrightness(int(match.group()))
            else:
                from engine.system_controls import brightnessUp
                brightnessUp()
            return True

        elif any(w in query for w in ["brightness down", "decrease brightness", "dimmer", "decrease the brightness"]):
            match = re.search(r'(\d+)', query)
            if match:
                from engine.system_controls import setBrightness
                setBrightness(int(match.group()))
            else:
                from engine.system_controls import brightnessDown
                brightnessDown()
            return True

        elif "set brightness" in query or "brightness to" in query:
            from engine.system_controls import setBrightness
            match = re.search(r'(\d+)', query)
            setBrightness(int(match.group()) if match else 50)
            return True

        elif "take screenshot" in query and is_phone_command(query):
            from engine.adb_controller import takeScreenshot
            takeScreenshot()
            return True

        elif "lock" in query and is_phone_command(query):
            from engine.adb_controller import lockPhone
            lockPhone()
            return True

        elif "unlock" in query and is_phone_command(query):
            from engine.adb_controller import unlockPhone
            unlockPhone()
            return True

        elif ("send message" in query or "send msg" in query or "message" in query
              or "phone call" in query or "video call" in query
              or (("call" in query or "video" in query) and "open" not in query)):
            from engine.features import findContact, whatsApp
            contact_no, name = findContact(query)
            if contact_no != 0:
                if re.search(r'\b(whatsapp)\b', query):
                    preferance = "whatsapp"
                elif re.search(r'\b(mobile|phone|android)\b', query):
                    preferance = "mobile"
                else:
                    speak("Should I use WhatsApp or mobile?")
                    preferance = takecommand()

                if "mobile" in preferance:
                    if "message" in query or "msg" in query:
                        speak("What should I say?")
                        message_text = takecommand()
                        from engine.adb_controller import sendSMS
                        sendSMS(contact_no, message_text, name)
                    elif "call" in query:
                        from engine.adb_controller import makePhoneCall
                        makePhoneCall(contact_no, name)
                elif "whatsapp" in preferance:
                    try:
                        if "message" in query or "msg" in query:
                            speak("What should I say?")
                            message_text = takecommand()
                            whatsApp(contact_no, message_text, 'message', name)
                        elif "video" in query:
                            from engine.whatsapp_caller import makeWhatsAppVideoCall
                            makeWhatsAppVideoCall(contact_no, name)
                        elif "call" in query:
                            from engine.whatsapp_caller import makeWhatsAppVoiceCall
                            makeWhatsAppVoiceCall(contact_no, name)
                    except Exception as e:
                        print(f"WhatsApp Error: {e}")
                        speak("Something went wrong with WhatsApp.")
            return False

        #  VIRTUAL TRY-ON
        elif any(w in query for w in [
            "try this cloth", "try on", "virtual try",
            "wear this", "try this outfit", "try this dress",
            "try this shirt", "try this top", "how does this look",
            "virtual dressing", "try on this"
        ]):
            from engine.virtual_tryon import handleVirtualTryOn
            handleVirtualTryOn(query)
            return False

        else:
            chat_with_nora(query)
            return True

    except Exception as e:
        print(f"Command Error: {e}")
        import traceback
        traceback.print_exc()
        speak("Oops, something went wrong!")
        return True


#  MAIN ENTRY POINT
@eel.expose
def allCommands(message=1):
    precache_common_phrases()

    if message == 1:
        query = takecommand()
        print(query)
    else:
        query = message
        try:
            eel.senderText(query)
        except:
            pass

    keep_going = process_query(query)

    while keep_going:
        try:
            eel.DisplayMessage('listening....')
        except:
            pass
        query = takecommand()
        print(f"[Loop] user said: {query}")
        keep_going = process_query(query)

    try:
        eel.ShowHood()
    except:
        pass