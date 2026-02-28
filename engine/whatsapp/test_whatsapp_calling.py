"""
WhatsApp Voice/Video Call Automation - Quick Test Script

This script tests the WhatsApp calling functionality with multiple approaches:
1. Direct coordinate clicking (fastest)
2. Arrow key menu navigation (most reliable)
3. Image detection (most adaptable)

Run this before using the main voice assistant to verify calling works.
"""

import pyautogui
import time
import subprocess
from pipes import quote
from playsound import playsound


def test_direct_click_method(mobile_no, call_type='call'):
    """
    Test direct clicking on Voice/Video buttons.
    
    For WhatsApp Desktop, the buttons are typically at:
    - Voice Call button: around (1047, 151)
    - Video Call button: around (1195, 151)
    
    These coordinates work on 1920x1080 displays. Adjust for your screen.
    """
    print(f"\n[TEST] Direct Click Method - {call_type}")
    print("=" * 60)
    
    try:
        # Open WhatsApp
        whatsapp_url = f"whatsapp://send?phone={mobile_no}&text="
        full_command = f'start "" "{whatsapp_url}"'
        subprocess.run(full_command, shell=True)
        
        print("Waiting 5 seconds for WhatsApp to load...")
        time.sleep(5)
        
        # Adjust these coordinates to your screen!
        # To find correct coordinates:
        # 1. Run: python whatsapp_button_detector.py
        # 2. Move mouse over Voice/Video button
        # 3. Note the X, Y coordinates
        
        if call_type == 'call':
            button_x, button_y = 1047, 151  # Voice button
            print(f"Clicking Voice button at ({button_x}, {button_y})")
        else:
            button_x, button_y = 1195, 151  # Video button
            print(f"Clicking Video button at ({button_x}, {button_y})")
        
        # Click the button
        pyautogui.click(button_x, button_y)
        print("✓ Button clicked! Check WhatsApp to confirm call initiated.")
        time.sleep(2)
        
        return True
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_arrow_key_method(call_type='call'):
    """
    Test menu navigation using arrow keys.
    More reliable than TAB for popup menus.
    """
    print(f"\n[TEST] Arrow Key Navigation Method - {call_type}")
    print("=" * 60)
    print("Instructions:")
    print("1. Click on a contact in WhatsApp")
    print("2. Look for the Voice/Video call buttons that appear")
    print("3. The script will try to trigger the menu and navigate")
    
    input("Press ENTER when ready...")
    
    try:
        time.sleep(1)
        
        # Try using arrow keys to navigate
        if call_type == 'call':
            print("Pressing DOWN arrow (no movement)")
            # Some menus don't need down for first item
        else:
            print("Pressing DOWN arrow (to video option)")
            pyautogui.press('down')
            time.sleep(0.3)
        
        print("Pressing ENTER to select...")
        pyautogui.press('enter')
        
        print("✓ Menu selection executed! Check WhatsApp to confirm.")
        time.sleep(2)
        
        return True
    
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def check_screen_resolution():
    """
    Check your screen resolution.
    Button coordinates need to be adjusted based on this.
    """
    print("\n[INFO] Screen Resolution Detection")
    print("=" * 60)
    
    # Get screen size
    screen_width, screen_height = pyautogui.size()
    print(f"Your screen resolution: {screen_width}x{screen_height}")
    
    print("\nButton Coordinate Guide:")
    print("-" * 60)
    print(f"1920x1080 (Full HD):    Voice ~(1047, 151), Video ~(1195, 151)")
    print(f"1366x768 (HD):          Voice ~(745, 90),   Video ~(850, 90)")
    print(f"2560x1440 (QHD 2K):     Voice ~(1400, 180), Video ~(1560, 180)")
    print("-" * 60)
    
    if screen_width == 1920:
        print("✓ Detected 1920x1080 - Default coordinates should work")
        return 1047, 151, 1195, 151
    elif screen_width == 1366:
        print("✓ Detected 1366x768 - Using adjusted coordinates")
        return 745, 90, 850, 90
    elif screen_width == 2560:
        print("✓ Detected 2560x1440 - Using adjusted coordinates")
        return 1400, 180, 1560, 180
    else:
        print(f"⚠ Unknown resolution {screen_width}x{screen_height}")
        print("Use the detector tool to find correct coordinates")
        return None


def find_coordinates_interactively():
    """
    Help user find correct button coordinates.
    """
    print("\n[SETUP] Interactive Coordinate Finder")
    print("=" * 60)
    print("""
Steps:
1. Open WhatsApp and click on a contact
2. When Voice/Video buttons appear, run: python whatsapp_button_detector.py
3. Move your mouse over each button
4. Press 'P' to record positions
5. Update the coordinates in this script
    """)


def main():
    """Main test menu"""
    print("\n" + "=" * 60)
    print("WHATSAPP CALLING - QUICK TEST")
    print("=" * 60)
    
    # First, check resolution
    coords = check_screen_resolution()
    
    print("\n" + "=" * 60)
    print("TEST OPTIONS")
    print("=" * 60)
    print("1. Test Direct Click (fastest)")
    print("2. Test Arrow Key Navigation (most reliable)")
    print("3. Find Button Coordinates (setup)")
    print("0. Exit")
    print("=" * 60)
    
    choice = input("\nSelect test (0-3): ").strip()
    
    if choice == '1':
        # For testing, use a test contact
        test_number = input("Enter phone number to test with (e.g., +919876543210): ").strip()
        call_type = input("Call type - 'call' or 'video': ").strip().lower()
        
        if test_number:
            test_direct_click_method(test_number, call_type)
    
    elif choice == '2':
        call_type = input("Call type - 'call' or 'video': ").strip().lower()
        test_arrow_key_method(call_type)
    
    elif choice == '3':
        find_coordinates_interactively()
    
    elif choice == '0':
        print("Goodbye!")
        return
    
    else:
        print("Invalid option!")
    
    # Ask if they want to run another test
    again = input("\nRun another test? (y/n): ").strip().lower()
    if again == 'y':
        main()


if __name__ == "__main__":
    try:
        print("=" * 60)
        print("NOTE: Run this script as Administrator for best results!")
        print("WhatsApp may block simulated input without proper permissions.")
        print("=" * 60)
        
        main()
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
    except Exception as e:
        print(f"\nError: {e}")
