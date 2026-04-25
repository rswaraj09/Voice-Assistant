import sys
import os
sys.path.append(os.getcwd())
from engine.system_controls import volumeUp, brightnessUp

print("Testing Volume Up...")
volumeUp(10)
print("Testing Brightness Up...")
brightnessUp(10)
print("Test complete.")
