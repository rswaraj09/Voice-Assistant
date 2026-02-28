"""
WhatsApp Button Detector & Debugger

This script helps you:
1. Locate Voice and Video call buttons on screen
2. Capture button images for use with image detection
3. Test clicking on specific coordinates

Usage:
    python whatsapp_button_detector.py
"""

import pyautogui
import time
import os
from PIL import ImageGrab
import keyboard

def show_mouse_position():
    """
    Display current mouse position. Move mouse over the button and press 'p' to print position.
    Press 'q' to quit.
    """
    print("=" * 60)
    print("MOUSE POSITION TRACKER")
    print("=" * 60)
    print("Instructions:")
    print("1. Move your mouse over the VOICE button")
    print("2. Press 'P' to print coordinates")
    print("3. Move your mouse over the VIDEO button")
    print("4. Press 'P' to print coordinates")
    print("5. Press 'Q' to quit")
    print("=" * 60)
    
    positions = {}
    
    try:
        while True:
            current_pos = pyautogui.position()
            print(f"\rCurrent position: X={current_pos[0]}, Y={current_pos[1]}         ", end="")
            
            if keyboard.is_pressed('p'):
                print(f"\n✓ Position recorded: {current_pos}")
                time.sleep(0.5)  # Debounce
            
            if keyboard.is_pressed('q'):
                print("\n\nQuitting...")
                break
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")


def capture_button_screen(output_file="whatsapp_call_buttons.png"):
    """
    Capture a screenshot of the WhatsApp window showing call buttons.
    """
    print("\n" + "=" * 60)
    print("BUTTON SCREENSHOT CAPTURE")
    print("=" * 60)
    print(f"Taking screenshot in 3 seconds...")
    print("Make sure WhatsApp is open and showing the contact with call buttons!")
    time.sleep(3)
    
    screenshot = ImageGrab.grab()
    screenshot.save(output_file)
    print(f"✓ Screenshot saved: {output_file}")
    return output_file


def test_click(x, y, click_count=1):
    """
    Test clicking on specific coordinates.
    
    Args:
        x, y: Screen coordinates
        click_count: Number of times to click
    """
    print("\n" + "=" * 60)
    print("CLICK TEST")
    print("=" * 60)
    print(f"Will click at position ({x}, {y}) in 2 seconds...")
    print("Make sure WhatsApp is visible!")
    time.sleep(2)
    
    for i in range(click_count):
        print(f"Clicking {i+1}/{click_count}...")
        pyautogui.click(x, y)
        time.sleep(0.5)
    
    print("✓ Click test complete!")


def create_voice_button_image():
    """
    Create a reference image for the Voice button.
    Based on WhatsApp's green button style.
    """
    print("\n" + "=" * 60)
    print("CREATING BUTTON IMAGES")
    print("=" * 60)
    
    # For now, we'll give instructions for manual capture
    print("""
To create button images:

1. Open WhatsApp and open a contact chat
2. Look for the green "Voice" and "Video" buttons in the top right
3. Use your screenshot tool to capture just those buttons
4. Save them as:
   - templates/assets/images/voice_button.png
   - templates/assets/images/video_button.png

Or use this python snippet:

    from PIL import Image, ImageGrab
    
    # Capture Voice button (top right area)
    voice_button = ImageGrab.grab(bbox=(1020, 140, 1120, 180))
    voice_button.save('templates/assets/images/voice_button.png')
    
    # Capture Video button (top right area)
    video_button = ImageGrab.grab(bbox=(1140, 140, 1240, 180))
    video_button.save('templates/assets/images/video_button.png')
    """)


def main():
    """Main menu"""
    import sys
    
    print("\n" + "=" * 60)
    print("WHATSAPP BUTTON DETECTOR & DEBUGGER")
    print("=" * 60)
    print("\nOptions:")
    print("1. Show mouse position (to find button coordinates)")
    print("2. Capture current screen")
    print("3. Test click at coordinates")
    print("4. Create button image references")
    print("5. Exit")
    print("=" * 60)
    
    choice = input("\nSelect option (1-5): ").strip()
    
    if choice == '1':
        show_mouse_position()
    
    elif choice == '2':
        output = input("Output filename (default: whatsapp_call_buttons.png): ").strip()
        if not output:
            output = "whatsapp_call_buttons.png"
        capture_button_screen(output)
    
    elif choice == '3':
        x = int(input("Enter X coordinate: "))
        y = int(input("Enter Y coordinate: "))
        capture_button_screen()  # Take screenshot first
        time.sleep(1)
        test_click(x, y)
    
    elif choice == '4':
        create_voice_button_image()
    
    elif choice == '5':
        print("Goodbye!")
        sys.exit(0)
    
    else:
        print("Invalid option!")
        return


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
