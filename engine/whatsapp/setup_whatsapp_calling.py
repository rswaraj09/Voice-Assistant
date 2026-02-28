"""
WHATSAPP CALLING - QUICK START SETUP WIZARD

This script guides you through the entire setup process in 5 minutes!

Run as Administrator:
    python setup_whatsapp_calling.py
"""

import os
import sys
import subprocess
import time
import pyautogui

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def print_step(step_num, text):
    """Print a numbered step"""
    print(f"\n[Step {step_num}] {text}")

def check_admin():
    """Check if running as administrator"""
    try:
        import ctypes
        is_admin = ctypes.windll.shell.IsUserAnAdmin()
        return bool(is_admin)
    except:
        return False

def install_dependencies():
    """Install missing dependencies"""
    print_step(1, "Checking dependencies...")
    
    try:
        import keyboard
        print("✓ python-keyboard already installed")
    except ImportError:
        print("⚠ Installing python-keyboard...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-keyboard"])
        print("✓ Installed python-keyboard")
    
    try:
        import pyautogui
        print("✓ pyautogui already installed")
    except ImportError:
        print("⚠ Installing pyautogui...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyautogui"])
        print("✓ Installed pyautogui")

def check_whatsapp():
    """Check if WhatsApp is installed"""
    print_step(2, "Checking WhatsApp Desktop...")
    
    # Common WhatsApp paths
    whatsapp_paths = [
        os.path.expanduser("~\\AppData\\Local\\WhatsApp\\WhatsApp.exe"),
        "C:\\Program Files (x86)\\WhatsApp\\WhatsApp.exe",
        "C:\\Program Files\\WhatsApp\\WhatsApp.exe",
    ]
    
    for path in whatsapp_paths:
        if os.path.exists(path):
            print(f"✓ WhatsApp found at: {path}")
            return True
    
    print("✗ WhatsApp Desktop not found!")
    print("  Please install WhatsApp from: https://www.whatsapp.com/download/")
    return False

def screen_resolution_test():
    """Check screen resolution"""
    print_step(3, "Checking screen resolution...")
    
    screen_width, screen_height = pyautogui.size()
    print(f"Your screen: {screen_width}x{screen_height}")
    
    if screen_width >= 1920:
        print("✓ Full HD or higher (1920+)")
        voice_x, voice_y = 1047, 151
        video_x, video_y = 1195, 151
    elif screen_width >= 1366:
        print("✓ HD (1366x768)")
        voice_x, voice_y = 745, 90
        video_x, video_y = 850, 90
    else:
        print("⚠ Low resolution - you may need custom coordinates")
        voice_x, voice_y = 700, 85
        video_x, video_y = 800, 85
    
    print(f"\nEstimated coordinates:")
    print(f"  Voice button: ({voice_x}, {voice_y})")
    print(f"  Video button: ({video_x}, {video_y})")
    
    return voice_x, voice_y, video_x, video_y

def manual_coordinate_finder():
    """Help user find exact button coordinates"""
    print_step(4, "Finding button coordinates...")
    
    print("""
This is IMPORTANT for reliability!

Instructions:
1. I'll run the coordinate finder tool
2. Open WhatsApp and click on a contact
3. Move your mouse over the green Voice button
4. Press 'P' to record coordinates
5. Repeat for Video button
6. Press 'Q' to quit

Ready? The tool will open in 5 seconds...
    """)
    
    input("Press ENTER to continue...")
    time.sleep(2)
    
    # Run the coordinate finder
    try:
        subprocess.call([sys.executable, "whatsapp_button_detector.py"])
    except Exception as e:
        print(f"Could not run detector: {e}")
        print("You can run it manually: python whatsapp_button_detector.py")

def contacts_check():
    """Check and help with contacts"""
    print_step(5, "Checking contacts database...")
    
    contacts_file = "engine/contacts.csv"
    
    if os.path.exists(contacts_file):
        with open(contacts_file, 'r') as f:
            lines = f.readlines()
        print(f"✓ Found contacts file with {len(lines)} entries")
        print("\nSample contacts:")
        for line in lines[:3]:
            print(f"  {line.strip()}")
    else:
        print("⚠ contacts.csv not found!")
        print("Creating template...")
        
        with open(contacts_file, 'w') as f:
            f.write("Name,PhoneNumber\n")
            f.write("Mom,+919876543210\n")
            f.write("Dad,+919876543211\n")
        
        print("✓ Created template. Edit engine/contacts.csv and add your contacts!")

def show_final_checklist():
    """Show final checklist"""
    print_header("FINAL CHECKLIST")
    
    checklist = [
        ("Admin permissions", check_admin()),
        ("Dependencies installed", True),  # We just installed them
        ("WhatsApp Desktop", True),  # User confirmed
        ("Screen resolution detected", True),
        ("Contacts setup", os.path.exists("engine/contacts.csv")),
    ]
    
    all_good = True
    for item, status in checklist:
        status_str = "✓" if status else "✗"
        print(f"{status_str} {item}")
        if not status:
            all_good = False
    
    return all_good

def run_first_test():
    """Run a quick test"""
    print_step(6, "Running first test...")
    
    response = input("\nWould you like to test the calling function now? (y/n): ").strip().lower()
    
    if response == 'y':
        try:
            subprocess.call([sys.executable, "test_whatsapp_calling.py"])
        except Exception as e:
            print(f"Could not run test: {e}")

def main():
    """Main setup wizard"""
    print_header("WHATSAPP CALLING - QUICK START SETUP")
    
    # Check admin
    if not check_admin():
        print("\n⚠️  WARNING: NOT RUNNING AS ADMINISTRATOR ⚠️")
        print("\nFor full functionality, please:")
        print("1. Close this window")
        print("2. Right-click on this file")
        print("3. Select 'Run as Administrator'")
        print("\nWhatsApp may block input without admin permissions!")
        input("\nPress ENTER to continue anyway...")
    
    # Step 1: Dependencies
    install_dependencies()
    
    # Step 2: WhatsApp
    if not check_whatsapp():
        print("\nSetup cannot continue without WhatsApp Desktop")
        input("Press ENTER to exit...")
        return
    
    # Step 3: Screen resolution
    voice_x, voice_y, video_x, video_y = screen_resolution_test()
    
    # Step 4: Find coordinates
    response = input("\nShould we run the coordinate finder? (y/n): ").strip().lower()
    if response == 'y':
        manual_coordinate_finder()
    else:
        print("\nYou can find coordinates manually:")
        print("  python whatsapp_button_detector.py")
    
    # Step 5: Contacts
    contacts_check()
    
    # Step 6: Final checklist
    print_header("SETUP COMPLETE!")
    
    all_good = show_final_checklist()
    
    if all_good:
        print("\n✅ Everything looks good!")
        print("\nYou can now:")
        print("  1. Test calling: python test_whatsapp_calling.py")
        print("  2. Use voice commands: 'Call [Contact Name]'")
        print("  3. Read the guide: WHATSAPP_SETUP_GUIDE.md")
    else:
        print("\n⚠ Some issues detected. Please check the setup guide.")
        print("   See: WHATSAPP_SETUP_GUIDE.md")
    
    # Run test
    response = input("\nWould you like to test calling now? (y/n): ").strip().lower()
    if response == 'y':
        run_first_test()
    
    print("\n" + "=" * 70)
    print("Setup complete! Next steps:")
    print("=" * 70)
    print("1. Add your contacts to engine/contacts.csv")
    print("2. Test with: python test_whatsapp_calling.py")
    print("3. Use voice command: 'Call [Contact Name]'")
    print("4. For help, see: WHATSAPP_SETUP_GUIDE.md")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease run as Administrator and try again")
        sys.exit(1)
