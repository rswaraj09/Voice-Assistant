"""
WHATSAPP AUTOMATION DIAGNOSTIC

This script diagnoses why WhatsApp calling isn't working.
"""

import pyautogui
import subprocess
import time
import os

def check_resolution():
    """Check and display screen resolution"""
    print("\n" + "=" * 70)
    print("1. SCREEN RESOLUTION CHECK")
    print("=" * 70)
    
    width, height = pyautogui.size()
    print(f"Your screen resolution: {width}x{height}")
    
    # Show what coordinates should be used
    if width >= 1920:
        print("📍 Expected button area: TOP RIGHT of WhatsApp window")
        print("   Voice button: Around X=1047, Y=151")
        print("   Video button: Around X=1195, Y=151")
    elif width >= 1366:
        print("📍 Expected button area: TOP RIGHT of WhatsApp window")
        print("   Voice button: Around X=745, Y=90")
        print("   Video button: Around X=850, Y=90")
    else:
        print("⚠️  Unusual resolution - buttons may be in different spot")
    
    return width, height

def check_whatsapp_installed():
    """Check if WhatsApp is installed"""
    print("\n" + "=" * 70)
    print("2. WHATSAPP INSTALLATION CHECK")
    print("=" * 70)
    
    whatsapp_paths = [
        os.path.expanduser("~\\AppData\\Local\\WhatsApp\\WhatsApp.exe"),
        "C:\\Program Files (x86)\\WhatsApp\\WhatsApp.exe",
        "C:\\Program Files\\WhatsApp\\WhatsApp.exe",
    ]
    
    for path in whatsapp_paths:
        if os.path.exists(path):
            print(f"✓ WhatsApp found: {path}")
            return True
    
    print("✗ WhatsApp not found!")
    return False

def test_whatsapp_open():
    """Test if WhatsApp can be opened"""
    print("\n" + "=" * 70)
    print("3. WHATSAPP OPENING TEST")
    print("=" * 70)
    
    try:
        print("Testing WhatsApp URL opening...")
        # Try to open WhatsApp (don't send to a contact, just open app)
        result = subprocess.run('start whatsapp://', shell=True)
        print(f"✓ WhatsApp URL command executed")
        print("  Wait 3 seconds for WhatsApp to open...")
        time.sleep(3)
        print("✓ If WhatsApp opened, that's good!")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def show_button_locations():
    """Show where to look for buttons"""
    print("\n" + "=" * 70)
    print("4. BUTTON LOCATION GUIDE")
    print("=" * 70)
    
    print("""
On WhatsApp Desktop chat window:
┌─────────────────────────────────────────────┐
│ Profile  ⋮  🔍  📞 (Voice) 📹 (Video)  ⋮   │  ← BUTTONS HERE (top right)
├─────────────────────────────────────────────┤
│                                             │
│  Chat messages go here                      │
│                                             │
└─────────────────────────────────────────────┘

The Voice (☎️) and Video (📹) buttons should be in:
  • Top right corner of the chat window
  • Next to the search icon and menu (⋮)
  • They are GREEN colored

If you DON'T see these buttons:
  1. Click on a CONTACT (not a group) in the left sidebar
  2. The buttons should appear in the chat header
  3. Make sure WhatsApp is in focus (actively selected)
    """)

def find_coordinates():
    """Help find correct coordinates"""
    print("\n" + "=" * 70)
    print("5. FINDING EXACT COORDINATES")
    print("=" * 70)
    
    response = input("Would you like to find button coordinates now? (y/n): ").strip().lower()
    
    if response == 'y':
        print("\nOpening coordinate finder tool...")
        time.sleep(1)
        try:
            subprocess.call(["python", "find_button_coords_simple.py"])
        except Exception as e:
            print(f"Could not open tool: {e}")
            print("Run this command manually:")
            print("  python find_button_coords_simple.py")

def test_click():
    """Test a click at specific coordinates"""
    print("\n" + "=" * 70)
    print("6. TEST CLICK")
    print("=" * 70)
    
    response = input("Would you like to test clicking at specific coordinates? (y/n): ").strip().lower()
    
    if response == 'y':
        x = int(input("Enter X coordinate: "))
        y = int(input("Enter Y coordinate: "))
        
        print(f"\nI will click at ({x}, {y}) in 2 seconds...")
        print("Make sure WhatsApp window is visible!")
        time.sleep(2)
        
        try:
            pyautogui.click(x, y)
            print("✓ Click executed!")
            print("  Check if a call button was clicked in WhatsApp")
        except Exception as e:
            print(f"✗ Error: {e}")

def show_summary():
    """Show summary of findings"""
    print("\n" + "=" * 70)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 70)
    
    print("""
If WhatsApp calling isn't working, it's usually one of these:

1. ❌ WRONG BUTTON COORDINATES
   → Solution: Run find_button_coords_simple.py and update coordinates
   → Edit: engine/features.py → _get_call_button_coordinates()

2. ❌ WHATSAPP DIDN'T FULLY LOAD
   → Solution: Increase wait time
   → Edit: engine/features.py → time.sleep(5) → change to time.sleep(8)

3. ❌ BUTTONS NOT VISIBLE
   → Make sure you clicked on a CONTACT (not group)
   → Make sure WhatsApp window is in focus
   → Try with a different contact

4. ❌ NOT RUNNING AS ADMINISTRATOR
   → Right-click on your voice assistant
   → Select "Run as Administrator"
   → WhatsApp blocks input without admin permissions

5. ❌ WHATSAPP URL NOT WORKING
   → Make sure WhatsApp Desktop is properly installed
   → Try opening WhatsApp manually first
   → Then use voice command
    """)

def main():
    """Main diagnostic flow"""
    print("\n" + "=" * 70)
    print("WHATSAPP CALLING DIAGNOSTIC TOOL")
    print("=" * 70)
    
    # Run checks
    check_resolution()
    has_whatsapp = check_whatsapp_installed()
    
    if has_whatsapp:
        test_whatsapp_open()
    
    show_button_locations()
    find_coordinates()
    test_click()
    show_summary()
    
    print("\n" + "=" * 70)
    print("Next steps:")
    print("=" * 70)
    print("1. Run coordinate finder: python find_button_coords_simple.py")
    print("2. Update coordinates in engine/features.py")
    print("3. Test calling again")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
