import re
import pyttsx3
import speech_recognition as sr
import eel
import time


def speak(text):
    text = str(text)
    engine = pyttsx3.init('sapi5')
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[1].id)
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

    if message == 1:
        query = takecommand()
        print(query)
        eel.senderText(query)
    else:
        query = message
        eel.senderText(query)

    if not query or query.strip() == "":
        eel.ShowHood()
        return

    try:

        # EMAIL
        if "email" in query or "send mail" in query or "send an email" in query:
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

        # OPEN APP ON PHONE OR LAPTOP
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

        # BRIGHTNESS CONTROLS
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

        # WHATSAPP / CALLS / MESSAGES
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
                        import traceback
                        traceback.print_exc()
                        speak("Error with WhatsApp.")
                else:
                    speak(f"I didn't understand. You said {preferance}.")

        # GEMINI AI CHAT
        else:
            from engine.features import geminai
            geminai(query)

    except Exception as e:
        print(f"Command Error: {e}")
        import traceback
        traceback.print_exc()
        speak("There was an error. Please try again.")

    eel.ShowHood()