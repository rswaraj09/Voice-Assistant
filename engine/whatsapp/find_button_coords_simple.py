"""
SIMPLE BUTTON COORDINATE FINDER

This tool helps you find the EXACT coordinates of WhatsApp Voice/Video buttons
on YOUR screen.

How to use:
1. Open WhatsApp
2. Click on any contact to open the chat
3. Run this script in another window
4. Look for printed coordinates as you hover
5. Move to Voice button and write down the X, Y
6. Move to Video button and write down the X, Y
"""

import pyautogui
import time

def main():
    print("\n" + "=" * 70)
    print("WHATSAPP BUTTON COORDINATE FINDER")
    print("=" * 70)
    
    print("\nInstructions:")
    print("1. Make sure WhatsApp is open with a contact chat visible")
    print("2. In 3 seconds, this script will show your mouse position constantly")
    print("3. Move your mouse to the GREEN VOICE button")
    print("4. Write down the coordinates shown (X, Y)")
    print("5. Move to the DARK VIDEO button")
    print("6. Write down those coordinates too")
    print("7. Then update engine/features.py with these coordinates")
    
    print("\nStarting in 3 seconds...")
    time.sleep(3)
    
    print("\n" + "-" * 70)
    print("MOVE YOUR MOUSE NOW - COORDINATES WILL SHOW BELOW:")
    print("-" * 70 + "\n")
    
    try:
        while True:
            x, y = pyautogui.position()
            # Show coordinates in a way that's easy to read
            print(f"\r  Current: X={x:4d}  Y={y:4d}  |  Try: pyautogui.click({x}, {y})        ", end="", flush=True)
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n\n" + "=" * 70)
        print("FINISHED")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Open engine/features.py")
        print("2. Find the _get_call_button_coordinates() function")
        print("3. Update the coordinates based on your findings")
        print("\nExample:")
        print("  if screen_width >= 1920:")
        print("      return YOUR_VOICE_X, YOUR_VOICE_Y, YOUR_VIDEO_X, YOUR_VIDEO_Y")
        print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    main()
