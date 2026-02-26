import os
import eel

from engine.features import *
from engine.command import *
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
        #     eel.hideFaceAuthSuccess()
        #     speak("Hello, Welcome Sir, How can i Help You")
        #     eel.hideStart()
        #     playAssistantSound()
        # else:
        #     speak("Face Authentication Fail")
        
        # proceed directly as if auth succeeded
        eel.hideStart()
        playAssistantSound()
        speak("Hello, Welcome Sir, How can i Help You")
    os.system('start msedge.exe --app="http://localhost:8000/index.html"')

    eel.start('index.html', mode=None, host='localhost', block=True)