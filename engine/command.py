import pyttsx3
import speech_recognition as sr
import eel
import time

def speak(text):
    text = str(text)
    engine = pyttsx3.init('sapi5')
    voices = engine.getProperty('voices') 
    engine.setProperty('voice', voices[0].id)
    engine.setProperty('rate', 174)
    eel.DisplayMessage(text)
    engine.say(text)
    eel.receiverText(text)
    engine.runAndWait()


def takecommand():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print('listening....')
        eel.DisplayMessage('listening....')
        r.pause_threshold = 1
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source, 10, 6)
    try:
        print('recognizing')
        eel.DisplayMessage('recognizing....')
        query = r.recognize_google(audio, language='en-in')
        print(f"user said: {query}")
        eel.DisplayMessage(query)
        time.sleep(2)
    except Exception as e:
        return ""
    return query.lower()


@eel.expose
def allCommands(message=1):

    if message == 1:
        query = takecommand()
        print(query)
        eel.senderText(query)
    else:
        query = message
        eel.senderText(query)

    try:
        # ── Open applications ─────────────────────────────────────────────
        if "open" in query:
            from engine.features import openCommand
            openCommand(query)

        # ── YouTube ───────────────────────────────────────────────────────
        elif "on youtube" in query:
            from engine.features import PlayYoutube
            PlayYoutube(query)

        # ── 🆕 AI CODE GENERATION ─────────────────────────────────────────
        # Triggers: "create a login page", "build a calculator", "make a python script", etc.
        elif any(trigger in query for trigger in [
            "create a", "make a", "build a", "generate a", "write a",
            "create an", "make an", "build an", "generate code", "write code"
        ]) and any(t in query for t in [
            "page", "website", "script", "program", "app", "calculator",
            "form", "code", "html", "python", "javascript", "login", "game", "tool"
        ]):
            from engine.code_generator import handleCodeGeneration
            handleCodeGeneration(query)

        # ── 🆕 SYSTEM CONTROLS — Volume ───────────────────────────────────
        elif any(w in query for w in ["volume up", "increase volume", "turn up volume"]):
            from engine.system_controls import volumeUp
            volumeUp()

        elif any(w in query for w in ["volume down", "decrease volume", "turn down volume"]):
            from engine.system_controls import volumeDown
            volumeDown()

        elif "mute" in query:
            from engine.system_controls import muteVolume
            muteVolume()

        elif "unmute" in query:
            from engine.system_controls import unmuteVolume
            unmuteVolume()

        elif "set volume" in query:
            from engine.system_controls import setVolume
            # Try to extract number from query e.g. "set volume to 50"
            import re
            match = re.search(r'\d+', query)
            level = int(match.group()) if match else 50
            setVolume(level)

        # ── 🆕 SYSTEM CONTROLS — Brightness ──────────────────────────────
        elif any(w in query for w in ["brightness up", "increase brightness", "brighter"]):
            from engine.system_controls import brightnessUp
            brightnessUp()

        elif any(w in query for w in ["brightness down", "decrease brightness", "dimmer", "dim screen"]):
            from engine.system_controls import brightnessDown
            brightnessDown()

        elif "set brightness" in query:
            from engine.system_controls import setBrightness
            import re
            match = re.search(r'\d+', query)
            level = int(match.group()) if match else 50
            setBrightness(level)

        # ── WhatsApp / Calls / Messages ───────────────────────────────────
        elif "send message" in query or "send msg" in query or "message" in query \
                or "phone call" in query or "video call" in query \
                or (("call" in query or "video" in query) and "open" not in query):
            from engine.features import findContact, whatsApp, makeCall, sendMessage
            contact_no, name = findContact(query)
            if contact_no != 0:
                if "whatsapp" in query:
                    preferance = "whatsapp"
                elif "mobile" in query or "phone" in query:
                    preferance = "mobile"
                else:
                    speak("Which mode you want to use whatsapp or mobile")
                    preferance = takecommand()

                print(f"User preference: {preferance}")

                if "mobile" in preferance:
                    if "send message" in query or "send sms" in query or "send msg" in query or "message" in query:
                        speak("what message to send")
                        message_text = takecommand()
                        sendMessage(message_text, contact_no, name)
                    elif "phone call" in query or ("call" in query and "video" not in query):
                        makeCall(name, contact_no)
                    else:
                        speak("please try again")
                elif "whatsapp" in preferance:
                    try:
                        if "send message" in query or "send msg" in query or "message" in query:
                            speak("what message to send")
                            message_text = takecommand()
                            whatsApp(contact_no, message_text, 'message', name)
                        elif "phone call" in query or ("call" in query and "video" not in query):
                            whatsApp(contact_no, "", 'call', name)
                        elif "video call" in query or "video" in query:
                            whatsApp(contact_no, "", 'video call', name)
                        else:
                            speak("please try again")
                    except Exception as whatsapp_error:
                        print(f"WhatsApp Error: {whatsapp_error}")
                        import traceback
                        traceback.print_exc()
                        speak(f"Error with whatsapp: {whatsapp_error}")
                else:
                    speak(f"I didn't understand, you said {preferance}")

        # ── Email ─────────────────────────────────────────────────────────
        elif "email" in query or "mail" in query:
            from engine.email_handler import handleEmail
            handleEmail()

        # ── 🆕 AI CONVERSATION (Gemini as friendly AI) ────────────────────
        # This is the catch-all — anything not matched above goes to Gemini
        else:
            from engine.features import geminai
            geminai(query)

    except Exception as e:
        print(f"Command Error: {e}")
        import traceback
        traceback.print_exc()
        speak(f"There was an error")

    eel.ShowHood()
