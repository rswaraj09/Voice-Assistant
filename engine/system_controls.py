from engine.command import speak

# ════════════════════════════════════════════════════════════════════════════
#  🔊 VOLUME CONTROLS
# ════════════════════════════════════════════════════════════════════════════

def _get_volume_interface():
    """Get Windows audio volume interface."""
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        import ctypes
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = ctypes.cast(interface, ctypes.POINTER(IAudioEndpointVolume))
        return volume
    except Exception as e:
        print(f"[Volume] Could not get audio interface: {e}")
        return None


def volumeUp(step: int = 10):
    """Increase system volume by step%."""
    try:
        volume = _get_volume_interface()
        if volume:
            current = volume.GetMasterVolumeLevelScalar() * 100
            new_level = min(100, current + step)
            volume.SetMasterVolumeLevelScalar(new_level / 100, None)
            speak(f"Volume increased to {int(new_level)} percent.")
        else:
            # Fallback: use keyboard
            import pyautogui
            for _ in range(5):
                pyautogui.press("volumeup")
            speak("Volume increased.")
    except Exception as e:
        print(f"[Volume Up Error] {e}")
        speak("Couldn't change volume.")


def volumeDown(step: int = 10):
    """Decrease system volume by step%."""
    try:
        volume = _get_volume_interface()
        if volume:
            current = volume.GetMasterVolumeLevelScalar() * 100
            new_level = max(0, current - step)
            volume.SetMasterVolumeLevelScalar(new_level / 100, None)
            speak(f"Volume decreased to {int(new_level)} percent.")
        else:
            import pyautogui
            for _ in range(5):
                pyautogui.press("volumedown")
            speak("Volume decreased.")
    except Exception as e:
        print(f"[Volume Down Error] {e}")
        speak("Couldn't change volume.")


def setVolume(level: int):
    """Set volume to a specific level (0-100)."""
    try:
        level = max(0, min(100, level))
        volume = _get_volume_interface()
        if volume:
            volume.SetMasterVolumeLevelScalar(level / 100, None)
            speak(f"Volume set to {level} percent.")
        else:
            speak("Couldn't set volume precisely on this system.")
    except Exception as e:
        print(f"[Set Volume Error] {e}")
        speak("Couldn't set volume.")


def muteVolume():
    """Mute system volume."""
    try:
        volume = _get_volume_interface()
        if volume:
            volume.SetMute(1, None)
            speak("Volume muted.")
        else:
            import pyautogui
            pyautogui.press("volumemute")
            speak("Volume muted.")
    except Exception as e:
        print(f"[Mute Error] {e}")
        speak("Couldn't mute volume.")


def unmuteVolume():
    """Unmute system volume."""
    try:
        volume = _get_volume_interface()
        if volume:
            volume.SetMute(0, None)
            speak("Volume unmuted.")
        else:
            import pyautogui
            pyautogui.press("volumemute")
            speak("Volume unmuted.")
    except Exception as e:
        print(f"[Unmute Error] {e}")
        speak("Couldn't unmute volume.")


# ════════════════════════════════════════════════════════════════════════════
#  ☀️ BRIGHTNESS CONTROLS
# ════════════════════════════════════════════════════════════════════════════

def _get_current_brightness() -> int:
    """Get current screen brightness (0-100)."""
    try:
        import screen_brightness_control as sbc
        return sbc.get_brightness(display=0)[0]
    except Exception as e:
        print(f"[Brightness] Could not get brightness: {e}")
        return 50  # fallback default


def brightnessUp(step: int = 10):
    """Increase screen brightness by step%."""
    try:
        import screen_brightness_control as sbc
        current = _get_current_brightness()
        new_level = min(100, current + step)
        sbc.set_brightness(new_level)
        speak(f"Brightness increased to {new_level} percent.")
    except ImportError:
        speak("Please install screen brightness control. Run: pip install screen-brightness-control")
    except Exception as e:
        print(f"[Brightness Up Error] {e}")
        speak("Couldn't change brightness. This may not be supported on external monitors.")


def brightnessDown(step: int = 10):
    """Decrease screen brightness by step%."""
    try:
        import screen_brightness_control as sbc
        current = _get_current_brightness()
        new_level = max(10, current - step)  # minimum 10% so screen doesn't go black
        sbc.set_brightness(new_level)
        speak(f"Brightness decreased to {new_level} percent.")
    except ImportError:
        speak("Please install screen brightness control. Run: pip install screen-brightness-control")
    except Exception as e:
        print(f"[Brightness Down Error] {e}")
        speak("Couldn't change brightness. This may not be supported on external monitors.")


def setBrightness(level: int):
    """Set screen brightness to a specific level (0-100)."""
    try:
        import screen_brightness_control as sbc
        level = max(10, min(100, level))
        sbc.set_brightness(level)
        speak(f"Brightness set to {level} percent.")
    except ImportError:
        speak("Please install screen brightness control. Run: pip install screen-brightness-control")
    except Exception as e:
        print(f"[Set Brightness Error] {e}")
        speak("Couldn't set brightness on this display.")
