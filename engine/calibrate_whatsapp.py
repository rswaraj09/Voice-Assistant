import pyautogui, keyboard, time

print("="*50)
print("WhatsApp Call Button Calibration Tool")
print("="*50)
print("\n1. Open WhatsApp Desktop")
print("2. Click on any contact to open their chat")
print("3. Follow instructions below\n")

# Step 1: Main call button
print("Hover over the CALL button (top right of chat) and press ENTER...")
keyboard.wait('enter')
call_btn = pyautogui.position()
print(f"  ✓ Call button: {call_btn}\n")
time.sleep(0.5)

# Step 2: Click it to open dropdown, then find Voice option
print("Now CLICK the call button to open the dropdown...")
print("Then hover over VOICE CALL option and press ENTER...")
keyboard.wait('enter')
voice_btn = pyautogui.position()
print(f"  ✓ Voice call option: {voice_btn}\n")
time.sleep(0.5)

# Step 3: Close dropdown, click again, find Video option
print("Press ESC to close dropdown, click call button again...")
print("Then hover over VIDEO CALL option and press ENTER...")
keyboard.wait('enter')
video_btn = pyautogui.position()
print(f"  ✓ Video call option: {video_btn}\n")

print("\n" + "="*50)
print("Copy these into whatsapp_caller.py:")
print("="*50)
print(f"CALL_BTN_X  = {call_btn.x}")
print(f"CALL_BTN_Y  = {call_btn.y}")
print(f"VOICE_OPT_X = {voice_btn.x}")
print(f"VOICE_OPT_Y = {voice_btn.y}")
print(f"VIDEO_OPT_X = {video_btn.x}")
print(f"VIDEO_OPT_Y = {video_btn.y}")
