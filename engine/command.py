import re
import asyncio
import edge_tts
import pygame
import pyttsx3
import os
import io
import hashlib
import speech_recognition as sr
import eel
import time
import threading


# ── Global state ──────────────────────────────────────────────────────────
_interrupted = False
_paused_text = ""
_conversation_history = []
MAX_HISTORY = 10

# ── Voice config ──────────────────────────────────────────────────────────
VOICE = "en-IN-NeerjaNeural"
RATE  = "+20%"
PITCH = "+0Hz"

# ── Audio cache — only for fixed phrases, never for Gemini responses ──────
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tts_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


# ════════════════════════════════════════════════════════════════════════════
#  SPEAK
# ════════════════════════════════════════════════════════════════════════════
async def _generate_audio(text):
    communicate = edge_tts.Communicate(text, voice=VOICE, rate=RATE, pitch=PITCH)
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
    """
    use_cache=True  → fixed phrases — saved to disk, instant on repeat
    use_cache=False → Gemini responses — never saved to disk
    """
    global _interrupted, _paused_text

    text = str(text).strip()
    if not text:
        return

    _interrupted = False

    try:
        eel.DisplayMessage(text)
        eel.receiverText(text)
    except:
        pass

    cache_path = _get_cache_path(text)

    try:
        pygame.mixer.init(frequency=24000)

        if use_cache and os.path.exists(cache_path):
            # Cache hit — play instantly
            print(f"[speak] Cache hit")
            with open(cache_path, "rb") as f:
                audio_bytes = f.read()
        else:
            # Generate via Edge TTS
            print(f"[speak] Generating audio...")
            audio_bytes = asyncio.run(_generate_audio(text))

            # Only save to cache for fixed phrases
            if use_cache and audio_bytes:
                with open(cache_path, "wb") as f:
                    f.write(audio_bytes)

        if audio_bytes and not _interrupted:
            _play_audio_bytes(audio_bytes)

    except Exception as e:
        print(f"[speak] Edge TTS error: {e} — falling back to pyttsx3")
        try:
            engine = pyttsx3.init('sapi5')
            voices = engine.getProperty('voices')
            engine.setProperty('voice', voices[1].id)
            engine.setProperty('rate', 185)
            engine.setProperty('volume', 1.0)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e2:
            print(f"[speak] Fallback error: {e2}")
    finally:
        try:
            pygame.mixer.quit()
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


# ── Pre-cache fixed phrases at startup ───────────────────────────────────
def precache_common_phrases():
    phrases = [
        "Hello, Welcome Sir, How can I Help You",
        "Okay, see you later!",
        "Fresh start! What's on your mind?",
        "Should I use WhatsApp or mobile?",
        "What should I say?",
        "Opening WhatsApp",
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
                        print(f"[Cache] Cached: {phrase[:40]}")
                except:
                    pass
    threading.Thread(target=_cache, daemon=True).start()


# ════════════════════════════════════════════════════════════════════════════
#  TAKE COMMAND
# ════════════════════════════════════════════════════════════════════════════
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
                                              'android', 'laptop', 'windows', 'computer', 'pc']
    pattern = r'\b(' + '|'.join(words_to_remove) + r')\b'
    app = re.sub(pattern, '', query).strip()
    return re.sub(r'\s+', ' ', app).strip()


# ════════════════════════════════════════════════════════════════════════════
#  AI CONVERSATION — Gemini streams, speaks sentence by sentence
#  use_cache=False — Gemini responses never saved to disk
# ════════════════════════════════════════════════════════════════════════════
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
                    speak(to_speak, use_cache=False)  # ← never cache Gemini

        if buffer.strip() and not _interrupted:
            speak(buffer.strip(), use_cache=False)    # ← never cache Gemini

        _conversation_history.append({"role": "model", "parts": [full_reply]})

    except Exception as e:
        print(f"[Chat] Error: {e}")
        try:
            genai.configure(api_key=LLM_KEY)
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(f"{system_prompt}\n\nUser: {query}\nNora:")
            speak(markdown_to_text(response.text).strip(), use_cache=False)  # ← never cache
        except:
            speak("Sorry, couldn't think of a response right now!")


def clear_conversation():
    global _conversation_history
    _conversation_history = []


# ════════════════════════════════════════════════════════════════════════════
#  PROCESS SINGLE QUERY
# ════════════════════════════════════════════════════════════════════════════
def process_query(query):
    if not query or query.strip() == "":
        return False

    try:

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
                from engine.adb_controller import openApp
                openApp(extract_app_name(query, 'open'))
            else:
                from engine.features import openCommand
                openCommand(query)
            return False

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

        else:
            chat_with_nora(query)
            return True

    except Exception as e:
        print(f"Command Error: {e}")
        import traceback
        traceback.print_exc()
        speak("Oops, something went wrong!")
        return True


# ════════════════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════
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