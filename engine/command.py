import re
import pyttsx3
import speech_recognition as sr
import eel
import time


# Global state for interruption
_interrupted = False
_paused_text = ""
_paused_sentences = []
_paused_index = 0


def speak(text):
    global _interrupted, _paused_text, _paused_sentences, _paused_index

    text = str(text)
    _interrupted = False
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    try:
        eel.DisplayMessage(text)
    except:
        pass
    try:
        eel.receiverText(text)
    except:
        pass

    for i, sentence in enumerate(sentences):
        if _interrupted:
            _paused_sentences = sentences
            _paused_index = i
            _paused_text = " ".join(sentences[i:])
            return

        # Create a fresh engine each sentence — avoids "run loop already started"
        try:
            engine = pyttsx3.init('sapi5')
            voices = engine.getProperty('voices')
            engine.setProperty('voice', voices[1].id)  # Female voice
            engine.setProperty('rate', 174)
            engine.say(sentence)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            print(f"[speak] Error: {e}")

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
        except:
            pass
        time.sleep(2)
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


@eel.expose
def allCommands(message=1):
    # Show Siri wave immediately when called
    try:
        eel.showSiriWaveFromPython()  
    except:
        pass

    if message == 1:
        query = takecommand()
        print(query)
        try:
            eel.senderText(query)
        except:
            pass
    else:
        query = message
        try:
            eel.senderText(query)
        except:
            pass

    if not query or query.strip() == "":
        try:
            eel.ShowHood()
        except:
            pass
        return

    try:

        # STOP
        if re.search(r'\b(stop|go back|home|cancel)\b', query):
            speak("Going back to home.")
            try:
                eel.ShowHood()
            except:
                pass
            return

        # RESUME
        elif re.search(r'\b(continue|resume|sorry for interruption|go on)\b', query):
            if _paused_text:
                speak("Continuing from where I left off.")
                remaining = _paused_text
                speak(remaining)
            else:
                speak("There is nothing to continue.")
            try:
                eel.ShowHood()
            except:
                pass
            return

        # EMAIL
        elif "email" in query or "send mail" in query or "send an email" in query:
            from engine.email_handler import handleEmail
            handleEmail()

        # YOUTUBE
        elif "on youtube" in query or "play on youtube" in query:
            from engine.features import PlayYoutube
            PlayYoutube(query)

        # CLOSE APP ON PHONE
        elif "close" in query and is_phone_command(query):
            from engine.adb_controller import closeApp
            app = extract_app_name(query, 'close')
            closeApp(app)

        # OPEN APP
        elif "open" in query:
            if is_phone_command(query):
                from engine.adb_controller import openApp
                app = extract_app_name(query, 'open')
                openApp(app)
            else:
                from engine.features import openCommand
                openCommand(query)

        # AI CODE GENERATION
        elif any(trigger in query for trigger in [
            "create a", "make a", "build a", "generate a", "write a",
            "create an", "make an", "build an", "generate code", "write code"
        ]) and any(t in query for t in [
            "page", "website", "script", "program", "app", "calculator",
            "form", "code", "html", "python", "javascript", "login", "game", "tool"
        ]):
            from engine.code_generator import handleCodeGeneration
            handleCodeGeneration(query)

        # VOLUME CONTROLS
        elif any(w in query for w in ["volume up", "increase volume", "turn up volume"]):
            from engine.system_controls import volumeUp
            volumeUp()

        elif any(w in query for w in ["volume down", "decrease volume", "turn down volume"]):
            from engine.system_controls import volumeDown
            volumeDown()

        elif "unmute" in query:
            from engine.system_controls import unmuteVolume
            unmuteVolume()

        elif "mute" in query:
            from engine.system_controls import muteVolume
            muteVolume()

        elif "set volume" in query:
            from engine.system_controls import setVolume
            match = re.search(r'\d+', query)
            level = int(match.group()) if match else 50
            setVolume(level)

        # BRIGHTNESS
        elif any(w in query for w in ["brightness up", "increase brightness", "brighter"]):
            from engine.system_controls import brightnessUp
            brightnessUp()

        elif any(w in query for w in ["brightness down", "decrease brightness", "dimmer", "dim screen"]):
            from engine.system_controls import brightnessDown
            brightnessDown()

        elif "set brightness" in query:
            from engine.system_controls import setBrightness
            match = re.search(r'\d+', query)
            level = int(match.group()) if match else 50
            setBrightness(level)

        # PHONE CONTROLS
        elif "take screenshot" in query and is_phone_command(query):
            from engine.adb_controller import takeScreenshot
            takeScreenshot()

        elif "lock" in query and is_phone_command(query):
            from engine.adb_controller import lockPhone
            lockPhone()

        elif "unlock" in query and is_phone_command(query):
            from engine.adb_controller import unlockPhone
            unlockPhone()

        # CALLS / MESSAGES
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
                    speak("Should I use WhatsApp or mobile call?")
                    preferance = takecommand()

                print(f"User preference: {preferance}")

                if "mobile" in preferance:
                    if "message" in query or "msg" in query:
                        speak("What message should I send?")
                        message_text = takecommand()
                        from engine.adb_controller import sendSMS
                        sendSMS(contact_no, message_text, name)
                    elif "call" in query:
                        from engine.adb_controller import makePhoneCall
                        makePhoneCall(contact_no, name)
                    else:
                        speak("Please try again.")

                elif "whatsapp" in preferance:
                    try:
                        if "message" in query or "msg" in query:
                            speak("What message should I send?")
                            message_text = takecommand()
                            whatsApp(contact_no, message_text, 'message', name)
                        elif "video call" in query or "video" in query:
                            from engine.whatsapp_caller import makeWhatsAppVideoCall
                            makeWhatsAppVideoCall(contact_no, name)
                        elif "call" in query:
                            from engine.whatsapp_caller import makeWhatsAppVoiceCall
                            makeWhatsAppVoiceCall(contact_no, name)
                        else:
                            speak("Please try again.")
                    except Exception as whatsapp_error:
                        print(f"WhatsApp Error: {whatsapp_error}")
                        speak("Error with WhatsApp.")
                else:
                    speak(f"I didn't understand. You said {preferance}.")

        # GEMINI
        else:
            from engine.config import LLM_KEY
            import google.generativeai as genai
            from engine.helper import markdown_to_text

            query_clean = query.strip()
            if re.search(r'\b(detail|explain|elaborate|full|complete|in depth|tell me more)\b', query):
                prompt = f"{query_clean}\nGive a detailed explanation."
            else:
                prompt = f"{query_clean}\nAnswer in maximum 2-3 sentences only. Be concise."

            genai.configure(api_key=LLM_KEY)
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            speak(markdown_to_text(response.text))

    except Exception as e:
        print(f"Command Error: {e}")
        import traceback
        traceback.print_exc()
        speak("There was an error. Please try again.")

    try:
        eel.ShowHood()
    except:
        pass