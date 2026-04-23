import os
import eel
import subprocess
import threading
import time

from engine.features import playAssistantSound
from engine.command import speak, allCommands
from engine import modes as _modes  # noqa: F401 — registers eel-exposed mode helpers
from engine import news_aggregator as _news  # noqa: F401
from engine import avatar_generator as _avatar  # noqa: F401
from engine import model_trainer as _trainer  # noqa: F401

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HOTWORD_TRIGGER_FILE = os.path.join(BASE_DIR, "hotword_trigger.txt")
UI_TRIGGER_FILE = os.path.join(BASE_DIR, "ui_trigger.txt")


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

    # ── TRIGGER FILE WATCHER — runs in Process 1 ─────────────────────────
    def trigger_watcher():
        import pygetwindow as gw

        # Clean old files
        for f in [HOTWORD_TRIGGER_FILE, UI_TRIGGER_FILE]:
            if os.path.exists(f):
                os.remove(f)

        print(f"[Watcher] Polling: {HOTWORD_TRIGGER_FILE}")

        while True:
            time.sleep(0.3)

            if os.path.exists(HOTWORD_TRIGGER_FILE):
                try:
                    os.remove(HOTWORD_TRIGGER_FILE)
                except:
                    pass

                print("[Watcher] Trigger detected!")

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
                        time.sleep(0.3)
                        print("[Watcher] Window focused")
                except Exception as e:
                    print(f"[Watcher] Focus error: {e}")

                # Write UI trigger — JS polls this to show Siri wave
                with open(UI_TRIGGER_FILE, "w") as f:
                    f.write("trigger")

                # Small delay for JS to pick up UI trigger and show Siri wave
                time.sleep(0.8)

                # Start listening
                try:
                    print("[Watcher] Starting allCommands...")
                    allCommands()
                    print("[Watcher] allCommands done")
                except Exception as e:
                    print(f"[Watcher] allCommands error: {e}")

    t = threading.Thread(target=trigger_watcher, daemon=True)
    t.start()

    # Open Edge after eel server is ready
    def open_browser():
        time.sleep(2)
        os.system('start msedge.exe --app="http://localhost:8000/index.html"')

    threading.Thread(target=open_browser, daemon=True).start()

    eel.start('index.html', mode=None, host='localhost', port=8000, block=True)