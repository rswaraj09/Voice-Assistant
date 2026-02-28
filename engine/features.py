import json
import os
from pipes import quote
import re
import sqlite3
import struct
import subprocess
import time
import webbrowser
from playsound import playsound
import eel
import pyaudio
import pyautogui
from engine.command import speak
from engine.config import ASSISTANT_NAME, LLM_KEY
# Playing assiatnt sound function
import pywhatkit as kit
import pvporcupine

from engine.helper import extract_yt_term, markdown_to_text, remove_words
from hugchat import hugchat

con = sqlite3.connect("nora.db")
cursor = con.cursor()

@eel.expose
def playAssistantSound():
    music_dir = "templates\\assets\\audio\\start_sound.mp3"
    playsound(music_dir)

    
def openCommand(query):
    query = query.replace(ASSISTANT_NAME, "")
    query = query.replace("open", "")
    query = query.lower()

    app_name = query.strip()

    if app_name != "":

        try:
            cursor.execute(
                'SELECT path FROM sys_command WHERE LOWER(name) IN (?)', (app_name,))
            results = cursor.fetchall()

            if len(results) != 0:
                speak("Opening "+query)
                os.startfile(results[0][0])

            elif len(results) == 0: 
                cursor.execute(
                'SELECT url FROM web_command WHERE LOWER(name) IN (?)', (app_name,))
                results = cursor.fetchall()
                
                if len(results) != 0:
                    speak("Opening "+query)
                    webbrowser.open(results[0][0])

                else:
                    speak("Opening "+query)
                    try:
                        os.system('start '+query)
                    except:
                        speak("not found")
        except:
            speak("some thing went wrong")

       

def PlayYoutube(query):
    search_term = extract_yt_term(query)
    speak("Playing "+search_term+" on YouTube")
    kit.playonyt(search_term)


def hotword():
    porcupine=None
    paud=None
    audio_stream=None
    try:
       
        # pre trained keywords    
        porcupine=pvporcupine.create(keywords=["jarvis","alexa"]) 
        paud=pyaudio.PyAudio()
        audio_stream=paud.open(rate=porcupine.sample_rate,channels=1,format=pyaudio.paInt16,input=True,frames_per_buffer=porcupine.frame_length)
        
        # loop for streaming
        while True:
            keyword=audio_stream.read(porcupine.frame_length)
            keyword=struct.unpack_from("h"*porcupine.frame_length,keyword)

            # processing keyword comes from mic 
            keyword_index=porcupine.process(keyword)

            # checking first keyword detetcted for not
            if keyword_index>=0:
                print("hotword detected")

                # pressing shorcut key win+j
                import pyautogui as autogui
                autogui.keyDown("win")
                autogui.press("j")
                time.sleep(2)
                autogui.keyUp("win")
                
    except:
        if porcupine is not None:
            porcupine.delete()
        if audio_stream is not None:
            audio_stream.close()
        if paud is not None:
            paud.terminate()



# find contacts
def findContact(query):
    
    # First try to extract the name using regex if the user specified "to [name]"
    # This prevents the message itself (e.g. "hii") from being part of the name
    import re
    match = re.search(r'to\s+([a-zA-Z\s]+?)(?:\s+on|\s*$)', query, re.IGNORECASE)
    
    if match:
        query = match.group(1).strip()
    else:
        # Fallback to the old word removal method
        words_to_remove = [ASSISTANT_NAME, 'make', 'a', 'to', 'phone', 'call', 'send', 'message', 'wahtsapp', 'whatsapp', 'video', 'msg', 'on']
        query = remove_words(query, words_to_remove)

    try:
        query = query.strip().lower()
        cursor.execute("SELECT mobile_no FROM contacts WHERE LOWER(name) LIKE ? OR LOWER(name) LIKE ?", ('%' + query + '%', query + '%'))
        results = cursor.fetchall()
        print(results[0][0])
        mobile_number_str = str(results[0][0])

        if not mobile_number_str.startswith('+91'):
            mobile_number_str = '+91' + mobile_number_str

        return mobile_number_str, query
    except:
        speak('not exist in contacts')
        return 0, 0
    
def _get_call_button_coordinates():
    """
    Get the appropriate Voice/Video call button coordinates based on screen resolution.
    
    Returns:
        tuple: (voice_x, voice_y, video_x, video_y)
    """
    screen_width, screen_height = pyautogui.size()
    
    # Adjust coordinates based on screen resolution
    # These are approximate positions for typical WhatsApp Desktop layouts
    
    if screen_width >= 1920:  # 1920x1080 or higher
        return 1047, 151, 1195, 151
    elif screen_width >= 1366:  # 1366x768
        return 745, 90, 850, 90
    else:  # Lower resolutions
        return 700, 85, 800, 85


def _click_button_with_retry(x, y, max_retries=3, wait_time=0.5):
    """
    Click a button with retry logic.
    
    Args:
        x, y: Screen coordinates
        max_retries: Number of retry attempts
        wait_time: Wait time between retries
    
    Returns:
        bool: True if click successful, False otherwise
    """
    for attempt in range(max_retries):
        try:
            # move to the location first for visibility/debug
            try:
                pyautogui.moveTo(x, y, duration=0.2)
                # print pixel color under mouse
                img = pyautogui.screenshot()
                color = img.getpixel((x, y))
                print(f"  [DEBUG] moved to ({x},{y}), pixel color {color}")
            except Exception:
                pass
            pyautogui.click(x, y)
            time.sleep(wait_time)
            return True
        except Exception as e:
            print(f"Click attempt {attempt + 1} failed: {e}")
            time.sleep(0.5)
    return False


def _find_and_click_button(button_image_path, confidence=0.7):
    """
    Find a button on screen using image detection and click it.
    
    Args:
        button_image_path: Path to button image
        confidence: Confidence threshold (0-1)
    
    Returns:
        bool: True if button found and clicked, False otherwise
    """
    try:
        # Try to find the button
        location = pyautogui.locateCenterOnScreen(button_image_path, confidence=confidence)
        
        if location:
            print(f"Button found at {location}")
            return _click_button_with_retry(location[0], location[1])
        else:
            print(f"Button not found: {button_image_path}")
            return False
    except Exception as e:
        print(f"Error finding button: {e}")
        return False


def _navigate_whatsapp_menu(option='call'):
    """
    Navigate WhatsApp menu using arrow keys (more reliable than TAB).
    
    Args:
        option: 'call' for voice call, 'video' for video call
    
    Returns:
        bool: True if navigation successful
    """
    try:
        time.sleep(0.5)
        
        # Press down arrow to navigate menu
        if option == 'video':
            pyautogui.press('down')
            time.sleep(0.3)
        
        pyautogui.press('enter')
        time.sleep(1)
        return True
    except Exception as e:
        print(f"Menu navigation error: {e}")
        return False


def _is_green(color, tolerance=80):
    """Return True if the RGB tuple is bright WhatsApp green (not cyan/teal)."""
    if not color or len(color) < 3:
        return False
    r, g, b = color[:3]
    # WhatsApp green is bright green: g should be very high (150+)
    # and significantly higher than both r and b
    # Exclude cyan/teal by requiring r to be low
    return g > 150 and g > r and g > b and (g - r) > 50 and (g - b) > 20


def _search_for_green_button(region=None):
    """Scan a screen region for a bright green pixel (WhatsApp button) and return its coords.

    Region tuple: (x1,y1,x2,y2). Defaults to top-right quarter of screen.
    Searches for the BRIGHTEST green to avoid cyan/teal confusion.
    """
    screen = pyautogui.screenshot()
    width, height = screen.size
    if region is None:
        x1 = int(width * 0.6)
        y1 = 0
        x2 = width
        y2 = int(height * 0.3)
    else:
        x1, y1, x2, y2 = region
    print(f"    [Color-Search] scanning region {x1},{y1}-{x2},{y2} for bright green")
    
    best_match = None
    best_green_value = 0
    
    for y in range(y1, y2, 3):
        for x in range(x1, x2, 3):
            col = screen.getpixel((x, y))
            if _is_green(col):
                r, g, b = col[:3]
                # prefer brighter greens (higher g value = button more likely)
                if g > best_green_value:
                    best_green_value = g
                    best_match = (x, y)
                    print(f"    [Color-Search] found stronger green at {x},{y} color {col}")
    
    if best_match:
        print(f"    [Color-Search] selected best match {best_match} with green value {best_green_value}")
        return best_match
    print("    [Color-Search] no bright green pixel found")
    return None



def whatsApp(mobile_no, message, flag, name):
    """
    Initiate WhatsApp call using production-grade method.
    
    This function opens WhatsApp and initiates a call/video call using:
    1. Direct coordinate clicking (most reliable for WhatsApp Desktop)
    2. Image detection fallback (adaptive to UI changes)
    3. Arrow key navigation fallback (keyboard-based menu navigation)
    
    IMPORTANT: Run your voice assistant as Administrator for best results!
    
    Args:
        mobile_no: Phone number with country code (e.g., +91XXXXXXXXXX)
        message: Message text (used for message flag only)
        flag: 'message', 'call', or 'video call'
        name: Contact name for status messages
    """
    
    print(f"\n[WhatsApp Function Called]")
    print(f"  Mobile: {mobile_no}")
    print(f"  Message: {message}")
    print(f"  Flag: {flag}")
    print(f"  Name: {name}")
    
    jarvis_message = ""
    
    # Encode the message for URL
    encoded_message = quote(message) if message else ""
    print(f"  Encoded message: {encoded_message}")
    
    # Construct the WhatsApp URL
    # ensure no spaces in phone number
    clean_no = mobile_no.replace(" ", "")
    whatsapp_url = f"whatsapp://send?phone={clean_no}&text={encoded_message}"
    full_command = f'start "" "{whatsapp_url}"'
    
    print(f"  WhatsApp URL: {whatsapp_url}")
    print(f"  Full Command: {full_command}")
    
    try:
        # Open WhatsApp with the constructed URL
        print(f"[Step 1] Opening WhatsApp for: {name}")
        subprocess.run(full_command, shell=True)
        print(f"[Step 2] Waiting 5 seconds for WhatsApp to load...")
        time.sleep(5)  # Wait for WhatsApp to load and chat to open
        
        # Ensure WhatsApp window is active/focused
        try:
            windows = pyautogui.getWindowsWithTitle('WhatsApp')
            if windows:
                print("[Step 2a] Activating WhatsApp window")
                windows[0].activate()
                time.sleep(0.5)
            else:
                print("[Step 2a] Could not find WhatsApp window to activate")
        except Exception as wf_err:
            print(f"[Step 2a] Window focus error: {wf_err}")
        
        if flag == 'message':
            # For messages, press enter to send
            time.sleep(2)  # Give it a tiny bit extra time just in case
            pyautogui.press('enter')
            
            jarvis_message = "message send successfully to " + name
            print(f"[Step 3] Message mode - Speaking: {jarvis_message}")
            speak(jarvis_message)
            print(f"[Complete] Message sent")
            return
        
        # Get button coordinates based on screen resolution
        voice_x, voice_y, video_x, video_y = _get_call_button_coordinates()
        print(f"[Step 3] Button Coordinates - Voice: ({voice_x}, {voice_y}), Video: ({video_x}, {video_y})")
        
        if flag == 'call':
            jarvis_message = "calling to " + name
            print(f"[Step 4] Voice Call Mode")
            print(f"  Attempting voice call to {name}")
            
            # Method 1: Sequential Image Scanning (PRIMARY)
            print(f"  [Method 1] Scanning for call icon...")
            call_icon_found = _find_and_click_button(
                "templates/assets/images/call_icon.png", 
                confidence=0.7
            )
            if call_icon_found:
                print("  Call icon clicked. Scanning for voice call icon...")
                time.sleep(1) # wait for dropdown to animate
                voice_icon_found = _find_and_click_button(
                    "templates/assets/images/voice_call_icon.png", 
                    confidence=0.7
                )
                if voice_icon_found:
                    print(f"  [Method 1] SUCCESS - Voice call initiated via sequential image scanning")
                    speak(jarvis_message)
                    print(f"[Complete] Voice call to {name}")
                    return
                else:
                    print("  [FAILED] Voice call icon not found after clicking call icon")
            else:
                print("  [FAILED] Call icon not found")
            
            # Method 2: Direct coordinate click (FALLBACK)
            print(f"  [Method 2] Trying direct coordinate click at ({voice_x}, {voice_y})...")
            if _click_button_with_retry(voice_x, voice_y):
                # wait for popup
                time.sleep(0.5)
                # try image detection if asset exists
                try:
                    loc = pyautogui.locateCenterOnScreen("templates/assets/images/voice_call_icon.png", confidence=0.7)
                except Exception as img_err:
                    print(f"    [Popup] image detection error: {img_err}")
                    loc = None
                if loc:
                    print(f"    [Popup] found voice call icon at {loc}")
                    _click_button_with_retry(loc[0], loc[1])
                    speak(jarvis_message)
                    print(f"[Complete] Voice call to {name}")
                    return
                else:
                    print("    [Popup] voice call icon not found via image, scanning colors")
                    found = _search_for_green_button()
                    if found:
                        print(f"    [Popup] found green pixel at {found}")
                        _click_button_with_retry(found[0], found[1])
                        speak(jarvis_message)
                        print(f"[Complete] Voice call to {name}")
                        return
                    
            # Method 3: Arrow key navigation (FALLBACK)
            print(f"  [Method 3] Trying arrow key navigation...")
            if _navigate_whatsapp_menu(option='call'):
                print(f"  [Method 3] SUCCESS - Voice call initiated via menu navigation")
                speak(jarvis_message)
                print(f"[Complete] Voice call to {name}")
                return
            
            # All methods failed
            print(f"  [FAILED] Could not initiate voice call")
            speak(f"Could not initiate call with {name}")
            print(f"[Complete] Voice call failed")
        
        elif flag == 'video call':
            jarvis_message = "starting video call with " + name
            print(f"[Step 4] Video Call Mode")
            print(f"  Attempting video call to {name}")
            
            # Method 1: Direct coordinate click (PRIMARY - most reliable)
            print(f"  [Method 1] Clicking initial icon at ({video_x}, {video_y})")
            screen = pyautogui.screenshot()
            try:
                current_color = screen.getpixel((video_x, video_y))
            except Exception:
                current_color = None
            print(f"    pixel color at initial target: {current_color}")
            if current_color and _is_green(current_color):
                if _click_button_with_retry(video_x, video_y):
                    print(f"  [Method 1] SUCCESS - Video call initiated via direct click")
                    speak(jarvis_message)
                    print(f"[Complete] Video call to {name}")
                    return
            else:
                print("    not green, clicking to open popup")
                if _click_button_with_retry(video_x, video_y):
                    time.sleep(0.5)
                    try:
                        loc = pyautogui.locateCenterOnScreen("templates/assets/images/video_button.png", confidence=0.7)
                    except Exception as img_err:
                        print(f"    [Popup] image detection error: {img_err}")
                        loc = None
                    if loc:
                        print(f"    [Popup] found green video button at {loc}")
                        _click_button_with_retry(loc[0], loc[1])
                        speak(jarvis_message)
                        print(f"[Complete] Video call to {name}")
                        return
                    else:
                        print("    [Popup] green video button not found via image, scanning colors")
                        found = _search_for_green_button()
                        if found:
                            print(f"    [Popup] found green pixel at {found}")
                            _click_button_with_retry(found[0], found[1])
                            speak(jarvis_message)
                            print(f"[Complete] Video call to {name}")
                            return
                print("    [Method1] initial icon click did not start call")
            
            # Method 2: Image detection (FALLBACK - adaptive)
            print(f"  [Method 2] Trying image detection...")
            video_button_found = _find_and_click_button(
                "templates/assets/images/video_button.png", 
                confidence=0.7
            )
            if video_button_found:
                print(f"  [Method 2] SUCCESS - Video call initiated via image detection")
                speak(jarvis_message)
                print(f"[Complete] Video call to {name}")
                return
            
            # Method 3: Arrow key navigation (FALLBACK - keyboard-based)
            print(f"  [Method 3] Trying arrow key navigation...")
            if _navigate_whatsapp_menu(option='video'):
                print(f"  [Method 3] SUCCESS - Video call initiated via menu navigation")
                speak(jarvis_message)
                print(f"[Complete] Video call to {name}")
                return
            
            # All methods failed
            print(f"  [FAILED] Could not initiate video call")
            print(f"  Check button coordinates or ensure WhatsApp is visible")
            speak(f"Could not initiate video call with {name}")
            print(f"[Complete] Video call failed")
        
    except Exception as e:
        print(f"[ERROR] Exception in WhatsApp function: {e}")
        import traceback
        traceback.print_exc()
        speak(f"Error initiating {flag} with {name}")

# chat bot 
def chatBot(query):
    user_input = query.lower()
    chatbot = hugchat.ChatBot(cookie_path="engine\cookies.json")
    id = chatbot.new_conversation()
    chatbot.change_conversation(id)
    response =  chatbot.chat(user_input)
    print(response)
    speak(response)
    return response

# android automation

def makeCall(name, mobileNo):
    mobileNo =mobileNo.replace(" ", "")
    speak("Calling "+name)
    command = 'adb shell am start -a android.intent.action.CALL -d tel:'+mobileNo
    os.system(command)


# to send message
def sendMessage(message, mobileNo, name):
    from engine.helper import replace_spaces_with_percent_s, goback, keyEvent, tapEvents, adbInput
    message = replace_spaces_with_percent_s(message)
    mobileNo = replace_spaces_with_percent_s(mobileNo)
    speak("sending message")
    goback(4)
    time.sleep(1)
    keyEvent(3)
    # open sms app
    tapEvents(136, 2220)
    #start chat
    tapEvents(819, 2192)
    # search mobile no
    adbInput(mobileNo)
    #tap on name
    tapEvents(601, 574)
    # tap on input
    tapEvents(390, 2270)
    #message
    adbInput(message)
    #send
    tapEvents(957, 1397)
    speak("message send successfully to "+name)

import google.generativeai as genai
def geminai(query):
    try:
        query = query.replace(ASSISTANT_NAME, "")
        query = query.replace("search", "")
        # Set your API key
        genai.configure(api_key=LLM_KEY)

        # Select a model
        model = genai.GenerativeModel("gemini-2.5-flash")

        # Generate a response
        response = model.generate_content(query)
        filter_text = markdown_to_text(response.text)
        speak(filter_text)
    except Exception as e:
        print("Error:", e)

# Settings Modal 



# Assistant name
@eel.expose
def assistantName():
    name = ASSISTANT_NAME
    return name


@eel.expose
def personalInfo():
    try:
        cursor.execute("SELECT * FROM info")
        results = cursor.fetchall()
        jsonArr = json.dumps(results[0])
        eel.getData(jsonArr)
        return 1    
    except:
        print("no data")


@eel.expose
def updatePersonalInfo(name, designation, mobileno, email, city):
    cursor.execute("SELECT COUNT(*) FROM info")
    count = cursor.fetchone()[0]

    if count > 0:
        # Update existing record
        cursor.execute(
            '''UPDATE info 
               SET name=?, designation=?, mobileno=?, email=?, city=?''',
            (name, designation, mobileno, email, city)
        )
    else:
        # Insert new record if no data exists
        cursor.execute(
            '''INSERT INTO info (name, designation, mobileno, email, city) 
               VALUES (?, ?, ?, ?, ?)''',
            (name, designation, mobileno, email, city)
        )

    con.commit()
    personalInfo()
    return 1



@eel.expose
def displaySysCommand():
    cursor.execute("SELECT * FROM sys_command")
    results = cursor.fetchall()
    jsonArr = json.dumps(results)
    eel.displaySysCommand(jsonArr)
    return 1


@eel.expose
def deleteSysCommand(id):
    cursor.execute("DELETE FROM sys_command WHERE id = ?", (id,))
    con.commit()


@eel.expose
def addSysCommand(key, value):
    cursor.execute(
        '''INSERT INTO sys_command VALUES (?, ?, ?)''', (None,key, value))
    con.commit()


@eel.expose
def displayWebCommand():
    cursor.execute("SELECT * FROM web_command")
    results = cursor.fetchall()
    jsonArr = json.dumps(results)
    eel.displayWebCommand(jsonArr)
    return 1


@eel.expose
def addWebCommand(key, value):
    cursor.execute(
        '''INSERT INTO web_command VALUES (?, ?, ?)''', (None, key, value))
    con.commit()


@eel.expose
def deleteWebCommand(id):
    cursor.execute("DELETE FROM web_command WHERE Id = ?", (id,))
    con.commit()


@eel.expose
def displayPhoneBookCommand():
    cursor.execute("SELECT * FROM contacts")
    results = cursor.fetchall()
    jsonArr = json.dumps(results)
    eel.displayPhoneBookCommand(jsonArr)
    return 1


@eel.expose
def deletePhoneBookCommand(id):
    cursor.execute("DELETE FROM contacts WHERE Id = ?", (id,))
    con.commit()


@eel.expose
def InsertContacts(Name, MobileNo, Email, City):
    cursor.execute(
        '''INSERT INTO contacts VALUES (?, ?, ?, ?, ?)''', (None,Name, MobileNo, Email, City))
    con.commit()