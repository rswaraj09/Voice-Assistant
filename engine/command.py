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

        if "open" in query:
            from engine.features import openCommand
            openCommand(query)
        elif "on youtube" in query:
            from engine.features import PlayYoutube
            PlayYoutube(query)
        
        elif "send message" in query or "send msg" in query or "message" in query or "phone call" in query or "video call" in query or (("call" in query or "video" in query) and "open" not in query):
            from engine.features import findContact, whatsApp, makeCall, sendMessage
            contact_no, name = findContact(query)
            if(contact_no != 0):
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
                            print(f"Calling whatsApp with: {contact_no}, {message_text}, message, {name}")
                            whatsApp(contact_no, message_text, 'message', name)
                                        
                        elif "phone call" in query or ("call" in query and "video" not in query):
                            print(f"Calling whatsApp with: {contact_no}, (empty), call, {name}")
                            whatsApp(contact_no, "", 'call', name)
                        elif "video call" in query or "video" in query:
                            print(f"Calling whatsApp with: {contact_no}, (empty), video call, {name}")
                            whatsApp(contact_no, "", 'video call', name)
                        else:
                            speak("please try again")
                    except Exception as whatsapp_error:
                        print(f"WhatsApp Error: {whatsapp_error}")
                        import traceback
                        traceback.print_exc()
                        speak(f"Error with whatsapp: {whatsapp_error}")
                else:
                    print(f"Preference not recognized: {preferance}")
                    speak(f"I didn't understand, you said {preferance}")

        elif "email" in query or "mail" in query:
            from engine.email.intent_handler import extract_email_intent
            from engine.email.email_generator import generate_email_content
            from engine.email.email_validator import validate_email_data
            from engine.email.confirmation_handler import confirm_and_send
            from engine.email.smtp_sender import send_email

            speak("Checking email details, please wait.")
            intent_data = extract_email_intent(query)
            if intent_data:
                recipient = intent_data["entities"].get("recipient")
                if recipient:
                    subject, body = generate_email_content(intent_data)
                    if validate_email_data(recipient, subject, body):
                        confirm_and_send(recipient, subject, body, send_email)
                    else:
                        speak("Sorry, I couldn't generate a valid email body. Please try again.")
                else:
                    speak("I couldn't find a valid email address.")
            else:
                speak("I couldn't understand the email details. Please try again.")
        else:
            from engine.features import geminai
            geminai(query)
    except Exception as e:
        print(f"Command Error: {e}")
        import traceback
        traceback.print_exc()
        speak(f"There was an error")
    
    eel.ShowHood()