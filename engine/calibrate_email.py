"""
Run this ONCE to find exact Gmail compose field coordinates.
Steps:
1. Run this script: python calibrate_email.py
2. Open Gmail in Chrome
3. Click the expand icon (⤢) on the New Message bar
4. When compose is fullscreen, hover over each field and press ENTER
"""
import pyautogui, time, keyboard

fields = ["TO field", "SUBJECT field", "BODY field", "SEND button"]
coords = {}

print("="*50)
print("Gmail Compose Calibration Tool")
print("="*50)
print("\nInstructions:")
print("1. Open Gmail and expand the compose window")
print("2. Hover your mouse over each field when asked")
print("3. Press ENTER to record the position\n")

for field in fields:
    print(f"Hover over the {field} and press ENTER...")
    keyboard.wait('enter')
    pos = pyautogui.position()
    coords[field] = pos
    print(f"  ✓ {field}: {pos}\n")
    time.sleep(0.5)

print("\n" + "="*50)
print("Copy these into email_handler.py:")
print("="*50)
print(f"TO_X      = {coords['TO field'].x}")
print(f"TO_Y      = {coords['TO field'].y}")
print(f"SUBJECT_X = {coords['SUBJECT field'].x}")
print(f"SUBJECT_Y = {coords['SUBJECT field'].y}")
print(f"BODY_X    = {coords['BODY field'].x}")
print(f"BODY_Y    = {coords['BODY field'].y}")
print(f"SEND_X    = {coords['SEND button'].x}")
print(f"SEND_Y    = {coords['SEND button'].y}")