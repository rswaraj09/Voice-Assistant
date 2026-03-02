import os
import subprocess
import time

IP_FILE = "engine/device_ip.txt"


# ════════════════════════════════════════════════════════════════════════════
#  HELPER: Get device IP
# ════════════════════════════════════════════════════════════════════════════
def get_device_ip():
    """Read saved device IP from file."""
    try:
        with open(IP_FILE, 'r') as f:
            ip = f.read().strip()
            if ip:
                return f"{ip}:5555"
    except:
        pass
    return None


def adb(command: str):
    """
    Run ADB command on specific device.
    Always targets the WiFi device to avoid multi-device error.
    """
    device = get_device_ip()
    if device:
        full_cmd = f'adb -s {device} {command}'
    else:
        full_cmd = f'adb {command}'

    print(f"[ADB] {full_cmd}")
    result = os.system(full_cmd)
    return result


def adb_output(command: str):
    """Run ADB command and return output as string."""
    device = get_device_ip()
    if device:
        full_cmd = f'adb -s {device} {command}'
    else:
        full_cmd = f'adb {command}'

    print(f"[ADB] {full_cmd}")
    try:
        result = subprocess.check_output(full_cmd, shell=True, text=True)
        return result.strip()
    except:
        return ""


def is_connected():
    """Check if phone is connected via ADB."""
    device = get_device_ip()
    if not device:
        print("[ADB] No device IP saved. Run device.bat first.")
        return False
    output = adb_output("get-state")
    return "device" in output


# ════════════════════════════════════════════════════════════════════════════
#  PHONE CONTROLS
# ════════════════════════════════════════════════════════════════════════════
def makePhoneCall(mobile_no: str, name: str):
    """Make a phone call via ADB."""
    from engine.command import speak
    mobile_no = mobile_no.replace(" ", "")
    speak(f"Calling {name} on your phone.")
    adb(f'shell am start -a android.intent.action.CALL -d tel:{mobile_no}')


def sendSMS(mobile_no: str, message: str, name: str):
    """Send SMS via ADB."""
    from engine.command import speak
    from engine.helper import replace_spaces_with_percent_s, goback, keyEvent, tapEvents, adbInput
    message = replace_spaces_with_percent_s(message)
    mobile_no = replace_spaces_with_percent_s(mobile_no)
    speak("Sending message.")
    goback(4)
    time.sleep(1)
    keyEvent(3)
    tapEvents(136, 2220)
    tapEvents(819, 2192)
    adbInput(mobile_no)
    tapEvents(601, 574)
    tapEvents(390, 2270)
    adbInput(message)
    tapEvents(957, 1397)
    speak(f"Message sent to {name}.")


def takeScreenshot():
    """Take screenshot of phone screen."""
    from engine.command import speak
    speak("Taking screenshot.")
    adb("shell screencap -p /sdcard/screenshot.png")
    time.sleep(1)
    adb("pull /sdcard/screenshot.png screenshots/phone_screenshot.png")
    speak("Screenshot saved.")


def openApp(app_name: str):
    from engine.command import speak
    import json

    # Step 1: Load saved cache
    cache_file = "engine/app_cache.json"
    try:
        with open(cache_file, 'r') as f:
            cached = json.load(f)
    except:
        cached = {}

    # Step 2: Hardcoded map
    app_map = {
        "instagram"   : "com.instagram.android",
        "whatsapp"    : "com.whatsapp",
        "youtube"     : "com.google.android.youtube",
        "camera"      : "com.android.camera2",
        "photos"     : "com.google.android.apps.photos",
        "settings"    : "com.android.settings",
        "chrome"      : "com.android.chrome",
        "spotify"     : "com.spotify.music",
        "maps"        : "com.google.android.apps.maps",
        "gmail"       : "com.google.android.gm",
        "phone"       : "com.android.dialer",
        "messages"    : "com.google.android.apps.messaging",
        "facebook"    : "com.facebook.katana",
        "twitter"     : "com.twitter.android",
        "snapchat"    : "com.snapchat.android",
        "telegram"    : "org.telegram.messenger",
        "netflix"     : "com.netflix.mediaclient",
        "amazon"      : "com.amazon.mShop.android.shopping",
        "flipkart"    : "com.flipkart.android",
        "paytm"       : "net.one97.paytm",
        "gpay"        : "com.google.android.apps.nbu.paisa.user",
        "phonepe"     : "com.phonepe.app",
        "zomato"      : "com.application.zomato",
        "swiggy"      : "in.swiggy.android",
        "hotstar"     : "in.startv.hotstar",
        "bgmi"        : "com.pubg.imobile",
        "battlegrounds mobile india" : "com.pubg.imobile",
        "pubg"        : "com.pubg.imobile",
        "free fire"   : "com.dts.freefireth",
        "cod"         : "com.activision.callofduty.shooter",
        "clash of clans" : "com.supercell.clashofclans",
        "discord"     : "com.discord",
        "linkedin"    : "com.linkedin.android",
        "uber"        : "com.ubercab",
        "ola"         : "com.olacabs.customer",
        "myntra"      : "com.myntra.android",
        "meesho"      : "com.meesho.supply",
    }

    # Step 3: Merge cache into map (cache overrides nothing, just adds)
    app_map.update(cached)

    app_name_clean = app_name.lower().strip()
    package = app_map.get(app_name_clean)

    # Step 4: Not found anywhere → search phone live
    if not package:
        print(f"[ADB] Searching phone for: {app_name}")
        speak(f"Let me search for {app_name} on your phone.")

        result = adb_output("shell pm list packages")
        search_term = app_name_clean.replace(" ", "")
        
        matches = []
        for line in result.splitlines():
            pkg = line.replace("package:", "").strip().lower()
            if search_term in pkg or any(w in pkg for w in app_name_clean.split()):
                matches.append(pkg)

        if matches:
            package = matches[0]
            print(f"[ADB] Found: {package}")
            # Save to cache
            cached[app_name_clean] = package
            with open(cache_file, 'w') as f:
                json.dump(cached, f, indent=2)
            speak(f"Found it! Opening {app_name}.")
        else:
            speak(f"{app_name} is not installed on your phone.")
            return

    adb(f"shell monkey -p {package} -c android.intent.category.LAUNCHER 1")



def closeApp(app_name: str):
    from engine.command import speak
    import json

    # Step 1: Load cache + hardcoded map
    cache_file = "engine/app_cache.json"
    try:
        with open(cache_file, 'r') as f:
            cached = json.load(f)
    except:
        cached = {}

    app_map = {
        "instagram"  : "com.instagram.android",
        "whatsapp"   : "com.whatsapp",
        "youtube"    : "com.google.android.youtube",
        "camera"     : "com.android.camera2",
        "settings"   : "com.android.settings",
        "chrome"     : "com.android.chrome",
        "spotify"    : "com.spotify.music",
        "maps"       : "com.google.android.apps.maps",
        "gmail"      : "com.google.android.gm",
        "facebook"   : "com.facebook.katana",
        "twitter"    : "com.twitter.android",
        "snapchat"   : "com.snapchat.android",
        "telegram"   : "org.telegram.messenger",
        "netflix"    : "com.netflix.mediaclient",
        "bgmi"       : "com.pubg.imobile",
        "battlegrounds mobile india" : "com.pubg.imobile",
        "pubg"       : "com.pubg.imobile",
        "free fire"  : "com.dts.freefireth",
        "discord"    : "com.discord",
    }
    app_map.update(cached)

    app_name_clean = app_name.lower().strip()
    package = app_map.get(app_name_clean)

    # Step 2: If not found → search live
    if not package:
        result = adb_output("shell pm list packages")
        search_term = app_name_clean.replace(" ", "")
        for line in result.splitlines():
            pkg = line.replace("package:", "").strip().lower()
            if search_term in pkg or any(w in pkg for w in app_name_clean.split()):
                package = pkg
                break

    # Step 3: Force stop the app
    if package:
        speak(f"Closing {app_name} on your phone.")
        adb(f"shell am force-stop {package}")
    else:
        speak(f"{app_name} is not installed on your phone.")


def setPhoneVolume(level: int):
    """Set phone volume (0-15)."""
    from engine.command import speak
    level = max(0, min(15, level))
    speak(f"Setting phone volume to {level}.")
    adb(f"shell media volume --stream 3 --set {level}")


def lockPhone():
    """Lock the phone screen."""
    from engine.command import speak
    speak("Locking your phone.")
    adb("shell input keyevent 26")


def unlockPhone():
    """Wake up and unlock phone screen."""
    from engine.command import speak
    speak("Unlocking your phone.")
    adb("shell input keyevent 26")   # wake up
    time.sleep(0.5)
    adb("shell input swipe 540 1800 540 900")  # swipe up to unlock


def phoneVolumeUp():
    adb("shell input keyevent 24")


def phoneVolumeDown():
    adb("shell input keyevent 25")
