import os
import eel
import subprocess

from engine.features import playAssistantSound
from engine.command import speak, allCommands

# face authentication has been disabled
# from engine.auth import recoganize

def start():
    
    eel.init("templates")

    playAssistantSound()

    @eel.expose
    def init():
        subprocess.call([r'device.bat'])
        eel.hideLoader()
        # face authentication steps have been commented out
        # speak("Ready for Face Authentication")
        # flag = recoganize.AuthenticateFace()
        # if flag == 1:
        #     eel.hideFaceAuth()
        #     speak("Face Authentication Successful")
        #     eel.hideFeceAuthSuccess()
        #     speak("Hello, Welcome Sir, How can i Help You")
        #     eel.hideStart()
        #     playAssistantSound()
        # else:
        #     speak("Face Authentication Fail")

        # proceed directly as if auth succeeded
        eel.hideStart()
        playAssistantSound()
        speak("Hello, Welcome Sir, How can i Help You")

    # BUG FIX: added port=8000 so browser opens on correct port
    os.system('start msedge.exe --app="http://localhost:8000/index.html"')
    eel.start('index.html', mode=None, host='localhost', port=8000, block=True)