import os
import eel
import subprocess
import threading
import time

from engine.features import playAssistantSound
from engine.command import speak, allCommands


def start():

    eel.init("templates")

    playAssistantSound()

    @eel.expose
    def init():
        subprocess.call([r'device.bat'])
        eel.hideLoader()
        eel.hideStart()
        playAssistantSound()
        speak("Hello, Welcome Sir, How can I Help You")

    # ── HOTWORD LISTENER THREAD ───────────────────────────────────────────
    def hotword_listener():
        import struct
        import pyaudio
        import pvporcupine
        import pygetwindow as gw

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
                    print("[Hotword] Detected!")

                    try:
                        from engine.command import interrupt_speech
                        interrupt_speech()
                    except:
                        pass

                    # Bring Nora window to front
                    try:
                        windows = (
                            gw.getWindowsWithTitle('Nora') or
                            gw.getWindowsWithTitle('localhost:8000') or
                            gw.getWindowsWithTitle('index.html')
                        )
                        if windows:
                            win = windows[0]
                            win.minimize()
                            time.sleep(0.1)
                            win.restore()
                            win.activate()
                            time.sleep(0.4)
                            print("[Hotword] Window focused")
                    except Exception as e:
                        print(f"[Hotword] Focus error: {e}")

                    # Write trigger file for JS UI update
                    try:
                        with open("hotword_trigger.txt", "w") as f:
                            f.write("trigger")
                        print("[Hotword] Trigger written")
                    except Exception as e:
                        print(f"[Hotword] Trigger write error: {e}")

                    # Start listening directly
                    try:
                        print("[Hotword] Starting allCommands directly...")
                        allCommands()
                    except Exception as e:
                        print(f"[Hotword] allCommands error: {e}")

                    time.sleep(2)

        except Exception as e:
            print(f"[Hotword Error] {e}")
        finally:
            if porcupine is not None: porcupine.delete()
            if audio_stream is not None: audio_stream.close()
            if paud is not None: paud.terminate()

    # Start hotword thread
    t = threading.Thread(target=hotword_listener, daemon=True)
    t.start()
    print("[Main] Hotword thread started")

    # Open Edge AFTER a short delay so eel server is ready
    def open_browser():
        time.sleep(2)  # wait for eel server to start
        os.system('start msedge.exe --app="http://localhost:8000/index.html"')

    threading.Thread(target=open_browser, daemon=True).start()

    # eel.start blocks — server starts here, THEN browser opens
    eel.start('index.html', mode=None, host='localhost', port=8000, block=True)