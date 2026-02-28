"""
🧠 AI Code Generator Module
============================
Integrates with your existing Voice Assistant (rswaraj09/Voice-Assistant)
Plugs into: engine/features.py and engine/command.py

Features:
- Generate code from voice commands using Gemini AI
- Save files to user-specified location
- Auto-open in VS Code
- Auto-run the generated code
"""

import os
import subprocess
import re
import time
import google.generativeai as genai
from engine.config import ASSISTANT_NAME, LLM_KEY
from engine.command import speak, takecommand

# ── VS Code executable path (adjust if needed) ──────────────────────────────
VSCODE_PATH = r"code"  # works if VS Code is in PATH; else use full path like:
# VSCODE_PATH = r"C:\Users\YourName\AppData\Local\Programs\Microsoft VS Code\Code.exe"

# ── Default save folder ──────────────────────────────────────────────────────
DEFAULT_FOLDER = os.path.join(os.path.expanduser("~"), "Desktop", "VoiceOS_Projects")
os.makedirs(DEFAULT_FOLDER, exist_ok=True)


# ════════════════════════════════════════════════════════════════════════════
#  STEP 1: Extract what the user wants to build
# ════════════════════════════════════════════════════════════════════════════
def extract_code_intent(query: str) -> dict:
    """
    Parse the voice query to understand:
    - What to build (e.g., 'login page', 'calculator', 'todo app')
    - What language/type (html, python, js)
    - Where to save it
    - What to name the file
    """
    query = query.lower()

    # Detect file type
    if any(w in query for w in ["html", "webpage", "web page", "website", "login page", "landing page", "form"]):
        file_type = "html"
        extension = ".html"
    elif any(w in query for w in ["python", "script", "calculator", "game"]):
        file_type = "python"
        extension = ".py"
    elif any(w in query for w in ["javascript", "js", "node"]):
        file_type = "javascript"
        extension = ".js"
    elif any(w in query for w in ["css", "style"]):
        file_type = "css"
        extension = ".css"
    else:
        file_type = "python"  # default
        extension = ".py"

    # Detect what to build (remove common voice words)
    remove = [ASSISTANT_NAME.lower(), "create", "make", "build", "generate", "write",
              "a", "an", "the", "for", "me", "please", "code", "program",
              "html", "python", "javascript", "js", "file", "page", "script"]
    words = query.split()
    intent_words = [w for w in words if w not in remove]
    intent = " ".join(intent_words).strip()

    # Generate a clean filename from intent
    filename_base = re.sub(r'[^a-z0-9_]', '_', intent.replace(" ", "_"))
    filename_base = filename_base.strip("_") or "generated_code"
    filename = filename_base + extension

    return {
        "intent": intent or query,
        "file_type": file_type,
        "extension": extension,
        "filename": filename,
        "original_query": query
    }


# ════════════════════════════════════════════════════════════════════════════
#  STEP 2: Generate code using Gemini AI
# ════════════════════════════════════════════════════════════════════════════
def generate_code_with_ai(intent: str, file_type: str) -> str:
    """Use Gemini to generate clean, working code."""
    try:
        genai.configure(api_key=LLM_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = f"""You are an expert {file_type} developer. 
Generate complete, working, well-commented {file_type} code for: {intent}

Rules:
- Return ONLY the raw code, no markdown, no backticks, no explanation
- Make it fully functional and ready to run
- Add helpful comments in the code
- For HTML: include CSS styling inside the file (no external files needed)
- For Python: include if __name__ == '__main__': block
- Make it look professional and modern
"""
        response = model.generate_content(prompt)
        code = response.text.strip()

        # Remove markdown code blocks if Gemini adds them anyway
        code = re.sub(r'^```[a-z]*\n?', '', code)
        code = re.sub(r'\n?```$', '', code)

        return code.strip()

    except Exception as e:
        print(f"[CodeGen Error] {e}")
        speak("Sorry, I had trouble generating the code. Please check your API key.")
        return None


# ════════════════════════════════════════════════════════════════════════════
#  STEP 3: Ask where to save the file
# ════════════════════════════════════════════════════════════════════════════
def get_save_location(filename: str) -> str:
    """Ask user where to save the file via voice."""
    speak(f"Where should I save the file? Say Desktop, Documents, or a folder name. Or say default to save on Desktop.")
    location_query = takecommand()

    if not location_query or "default" in location_query or location_query.strip() == "":
        folder = DEFAULT_FOLDER
    elif "desktop" in location_query:
        folder = os.path.join(os.path.expanduser("~"), "Desktop")
    elif "document" in location_query:
        folder = os.path.join(os.path.expanduser("~"), "Documents")
    elif "download" in location_query:
        folder = os.path.join(os.path.expanduser("~"), "Downloads")
    else:
        # Try to use what they said as a folder name on Desktop
        folder_name = location_query.strip().replace(" ", "_")
        folder = os.path.join(os.path.expanduser("~"), "Desktop", folder_name)
        os.makedirs(folder, exist_ok=True)

    return os.path.join(folder, filename)


# ════════════════════════════════════════════════════════════════════════════
#  STEP 4: Save the file
# ════════════════════════════════════════════════════════════════════════════
def save_code_to_file(code: str, filepath: str) -> bool:
    """Save generated code to the specified file path."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
        print(f"[CodeGen] File saved: {filepath}")
        return True
    except Exception as e:
        print(f"[CodeGen] Save error: {e}")
        speak("I had trouble saving the file.")
        return False


# ════════════════════════════════════════════════════════════════════════════
#  STEP 5: Open in VS Code
# ════════════════════════════════════════════════════════════════════════════
def open_in_vscode(filepath: str):
    """Open the generated file in VS Code."""
    try:
        speak("Opening the file in VS Code.")
        subprocess.Popen([VSCODE_PATH, filepath])
        time.sleep(2)
        print(f"[CodeGen] Opened in VS Code: {filepath}")
    except FileNotFoundError:
        # Try with full common path
        try:
            vscode_full = r"C:\Users\{}\AppData\Local\Programs\Microsoft VS Code\Code.exe".format(
                os.environ.get("USERNAME", ""))
            subprocess.Popen([vscode_full, filepath])
        except Exception as e:
            print(f"[CodeGen] VS Code not found: {e}")
            speak("I couldn't open VS Code. Please open the file manually.")
    except Exception as e:
        print(f"[CodeGen] VS Code error: {e}")
        speak("There was an issue opening VS Code.")


# ════════════════════════════════════════════════════════════════════════════
#  STEP 6: Run the code
# ════════════════════════════════════════════════════════════════════════════
def run_code(filepath: str, file_type: str):
    """Run the generated code based on its type."""
    try:
        speak("Running the code now.")

        if file_type == "python":
            subprocess.Popen(["python", filepath], creationflags=subprocess.CREATE_NEW_CONSOLE)
            speak("Python script is now running in a new terminal window.")

        elif file_type == "html":
            os.startfile(filepath)  # Opens in default browser
            speak("Opening the HTML file in your browser.")

        elif file_type == "javascript":
            subprocess.Popen(["node", filepath], creationflags=subprocess.CREATE_NEW_CONSOLE)
            speak("JavaScript file is running with Node.js.")

        else:
            os.startfile(filepath)
            speak("File opened.")

    except Exception as e:
        print(f"[CodeGen] Run error: {e}")
        speak("I couldn't run the file automatically. Please run it manually.")


# ════════════════════════════════════════════════════════════════════════════
#  MAIN FUNCTION — call this from command.py
# ════════════════════════════════════════════════════════════════════════════
def handleCodeGeneration(query: str):
    """
    Full pipeline:
    1. Understand what to build
    2. Generate code with AI
    3. Ask where to save
    4. Save file
    5. Open in VS Code
    6. Ask if user wants to run it
    """
    speak("Sure! Let me generate the code for you. One moment...")

    # Step 1: Understand intent
    intent_data = extract_code_intent(query)
    speak(f"I'll create a {intent_data['file_type']} file for {intent_data['intent']}.")

    # Step 2: Generate code
    code = generate_code_with_ai(intent_data["intent"], intent_data["file_type"])
    if not code:
        return

    speak("Code generated successfully!")

    # Step 3: Ask where to save
    filepath = get_save_location(intent_data["filename"])

    # Step 4: Save file
    saved = save_code_to_file(code, filepath)
    if not saved:
        return

    speak(f"File saved as {intent_data['filename']}")

    # Step 5: Open in VS Code
    speak("Should I open it in VS Code?")
    response = takecommand()
    if response and any(w in response for w in ["yes", "yeah", "sure", "open", "ok", "yep"]):
        open_in_vscode(filepath)

    # Step 6: Ask if they want to run it
    time.sleep(1)
    speak("Do you want me to run the code?")
    run_response = takecommand()
    if run_response and any(w in run_response for w in ["yes", "yeah", "sure", "run", "ok", "yep"]):
        run_code(filepath, intent_data["file_type"])
    else:
        speak(f"Alright! Your file is saved at {filepath}. Let me know if you need anything else.")
