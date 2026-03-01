# Nora Voice Assistant

Nora is an advanced, AI-powered voice assistant built with Python. It features a modern web-based UI and provides various capabilities including opening system applications, playing media, initiating WhatsApp calls/messages, sending emails, and conversing using Large Language Models (LLMs).

## Features
- **Voice Recognition & Wake Word**: Uses `pvporcupine` for hotword detection (e.g., "jarvis", "alexa") along with speech recognition for continuous listening.
- **Web UI**: A frontend graphical user interface powered by `Eel` (HTML, CSS, JavaScript).
- **App & Web Automation**: Opens Windows applications and specific websites using pre-configured commands stored in a SQLite database.
- **WhatsApp Automation**: Capable of sending WhatsApp messages and making voice/video calls automatically via the WhatsApp Desktop application using UI automation (`PyAutoGUI`).
- **Conversational AI**: Integrates with `hugchat` and Google's Generative AI (`Gemini Flash`) for intelligent, contextual responses.
- **Email Handling**: Secure, conversational email sending functionality using Gmail SMTP with intent detection.
- **Media**: Automates playing YouTube videos.
- **Contact Management**: Stores and retrieves contacts from the local database to quickly issue call or message commands by name.

## Tech Stack
- **Backend/Core**: Python 3
- **GUI**: Eel (HTML/CSS/JS)
- **Database**: SQLite (`nora.db`)
- **Voice/Audio**: `SpeechRecognition`, `pyttsx3`, `pyaudio`, `pvporcupine`, `playsound`
- **Automation**: `PyAutoGUI`, `pywhatkit`, `opencv-python`
- **AI/LLM**: `hugchat`, `google-generativeai`

## Prerequisites
- Python 3.8+
- [C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) (often required to build Python audio and Porcupine libraries on Windows)
- Microsoft Edge or Google Chrome (required for the Eel UI)

## Installation

1. **Clone the repository** (if applicable) or navigate to your project directory.

2. **Create a virtual environment** (Optional but highly recommended):
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**:
   Ensure you have a `.env` file in the root directory configured with your API keys. Example:
   ```env
   LLM_KEY=your_gemini_api_key_here
   ```

## Usage

1. **Run the assistant**:
   To start the assistant with both the UI and background hotword listening mode concurrently, execute:
   ```bash
   python run.py
   ```
   *(Alternatively, you can run `python main.py` to start just the core UI process).*

2. **Interacting**:
   - Speak the hotword (e.g., **"jarvis"** or **"alexa"**) to wake the assistant.
   - You can then give commands like:
     - *"Open notepad"*
     - *"Play [song name] on YouTube"*
     - *"Send a WhatsApp message to [Contact Name]"*
     - *"Call [Contact Name]"*

## Project Structure
- `main.py`: Entry point for the Eel web app UI.
- `run.py`: multiprocessing script to run the UI and hotword listener concurrently.
- `engine/`: Contains the core logic scripts:
  - `features.py`: Implementations of primary features (WhatsApp, YouTube, LLM chat, App launching).
  - `command.py`: Voice command processing.
  - `db.py` / `nora.db`: Database connection and schema for contacts and commands.
  - `email_handler.py`: Email processing and SMTP logic.
- `templates/`: Directory containing HTML, CSS, JavaScript, and graphical assets for the web UI.
- `calibrate/`: Scripts for tuning/calibrating coordinate-based automation (e.g., WhatsApp button clicking).
- `device.bat`: Batch script for device initialization.
- `requirements.txt`: Project package dependencies list.

## Notes
- **WhatsApp Automation**: Uses `PyAutoGUI` to interact with the Windows WhatsApp app. For best results, don't obstruct the screen while the automation executes. Features fallbacks like image detection and arrow-key navigation.
- **Face Authentication**: Original code includes logic for OpenCV-based face authentication, which can be re-enabled from `main.py`.

## License
MIT License (or your specified license)
