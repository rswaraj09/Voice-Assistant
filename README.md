# Voice Assistant

A comprehensive Python-based voice assistant application with a web UI, featuring speech recognition, text-to-speech, WhatsApp integration, email automation, and more.

## Features

- **Voice Commands**: Recognize and execute voice commands using Google Speech Recognition
- **Text-to-Speech**: Respond to user commands with natural speech using pyttsx3
- **Web Interface**: Interactive web UI built with HTML, CSS, and JavaScript using Eel
- **WhatsApp Integration**: Send messages and initiate calls/video calls on WhatsApp
- **Email Automation**: Send emails and handle email confirmations
- **Face Authentication**: Optional face recognition for user authentication
- **Command Execution**: Execute system commands and open applications
- **Database Support**: SQLite database for storing system commands and contacts
- **AI Integration**: Support for Google Generative AI and HugChat
- **Music & Media**: YouTube search and playback capabilities

## Project Structure

```
Voice Assistant/
├── main.py                      # Main application entry point
├── run.py                       # Multi-process runner (GUI + Hotword)
├── device.bat                   # Device initialization script
├── requirements.txt             # Python dependencies
├── nora.db                       # SQLite database
│
├── engine/
│   ├── command.py              # Core command processing
│   ├── features.py             # Feature implementations (600+ lines)
│   ├── config.py               # Configuration settings
│   ├── helper.py               # Helper functions
│   ├── db.py                   # Database operations
│   ├── contacts.csv            # Contact list for messaging
│   │
│   ├── auth/                   # Face authentication module
│   │   ├── recoganize.py       # Face recognition logic
│   │   ├── trainer.py          # Model training
│   │   ├── sample.py           # Sample capture
│   │   ├── haarcascade_frontalface_default.xml
│   │   ├── trainer/
│   │   │   └── trainer.yml     # Trained model
│   │   └── samples/            # Face samples for training
│   │
│   ├── email/                  # Email automation module
│   │   ├── __init__.py
│   │   ├── email_generator.py
│   │   ├── email_validator.py
│   │   ├── smtp_sender.py
│   │   ├── confirmation_handler.py
│   │   └── intent_handler.py
│   │
│   └── whatsapp/               # WhatsApp integration module
│       ├── whatsapp_button_detector.py
│       ├── setup_whatsapp_calling.py
│       ├── test_whatsapp_calling.py
│       ├── diagnose_whatsapp.py
│       └── find_button_coords_simple.py
│
├── templates/                   # Web UI files
│   ├── index.html              # Main HTML interface
│   ├── main.js                 # Main JavaScript logic
│   ├── controller.js           # UI controller
│   ├── script.js               # Additional scripts
│   ├── style.css               # Styling
│   │
│   └── assets/
│       ├── audio/              # Audio files (start sound, etc.)
│       ├── images/             # Image assets
│       └── vendore/
│           └── texllate/       # Text animation library
│               ├── animate.css
│               ├── jquery.fittext.js
│               ├── jquery.lettering.js
│               └── style.css
│
└── README.md                    # This file
```

## Installation

### Prerequisites
- Python 3.8 or higher
- Windows OS (some features are Windows-specific)
- Microphone for voice input
- Speaker or headphones for audio output
- Microsoft Edge browser (used for the web UI)

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd "Voice Assistant"
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure settings**
   - Update `engine/config.py` with your API keys and configuration
   - Add contacts to `engine/contacts.csv`

5. **Database initialization**
   - The SQLite database `nora.db` will be created automatically on first run
   - System commands are stored in the database for quick access

## Usage

### Start the Assistant

**Option 1: Full Application (GUI + Voice)**
```bash
python run.py
```
This starts both the web UI and the hotword listening in separate processes.

**Option 2: GUI Only**
```bash
python main.py
```
This launches just the web interface.

### Voice Commands

Once running, you can use voice commands like:
- "Open [application name]"
- "Send message to [contact]"
- "Make a call to [contact]"
- "Send WhatsApp message to [contact]"
- "Search for [query]"
- "Play [song name]"
- "What's the weather?"
- And many more...

### WhatsApp Setup

1. Run the WhatsApp setup tool:
   ```bash
   python engine/whatsapp/setup_whatsapp_calling.py
   ```

2. For testing WhatsApp calling:
   ```bash
   python engine/whatsapp/test_whatsapp_calling.py
   ```

3. To diagnose WhatsApp issues:
   ```bash
   python engine/whatsapp/diagnose_whatsapp.py
   ```

## Key Components

### Engine Features (`engine/features.py`)
Implements all major features including:
- WhatsApp messaging and calling
- Email sending
- System command execution
- Web search
- Music playback
- Contact management

### Command Processing (`engine/command.py`)
- Handles voice command recognition
- Routes commands to appropriate handlers
- Manages text-to-speech responses

### Web UI (`templates/`)
- Modern, responsive interface
- Real-time message display
- Voice command visualization
- Built with HTML5, CSS3, and JavaScript

### Database (`engine/db.py`)
- Manages SQLite database operations
- Stores system commands and configurations

## Configuration

Edit `engine/config.py` to customize:
- Assistant name
- API keys (Google AI, etc.)
- Audio settings
- Voice parameters (rate, voice ID)
- Default behaviors

## Dependencies

### Speech & Audio
- `SpeechRecognition` - Voice input
- `pyttsx3` - Text-to-speech
- `PyAudio` - Audio processing
- `pvporcupine` - Hotword detection

### Web Framework
- `Eel` - Python-JavaScript bridge
- `Flask` - Web server

### AI/ML
- `google-generativeai` - Google's generative AI
- `hugchat` - HugChat integration
- `opencv-python` - Computer vision

### Automation
- `PyAutoGUI` - GUI automation
- `pywhatkit` - WhatsApp & YouTube automation
- `requests` - HTTP requests

### Other
- `numpy` - Numerical computing
- `Pillow` - Image processing
- `beautifulsoup4` - Web scraping
- `pymongo` - MongoDB support

## Troubleshooting

### Microphone Issues
- Check that your microphone is connected and set as default
- Test audio input in Windows settings
- Run `diagnose_whatsapp.py` for specific WhatsApp issues

### Speech Recognition Not Working
- Ensure internet connection (Google API is used)
- Check microphone permissions
- Verify `SpeechRecognition` is properly installed

### WhatsApp Integration Issues
1. Ensure WhatsApp Desktop is installed
2. Run `engine/whatsapp/diagnose_whatsapp.py` to identify problems
3. Use `engine/whatsapp/find_button_coords_simple.py` to calibrate coordinates

### Face Authentication
- Currently disabled by default
- To enable, uncomment code in `main.py`
- Requires training the model first using `engine/auth/trainer.py`

## Development

### Adding New Features
1. Add feature logic to `engine/features.py`
2. Update command handlers in `engine/command.py`
3. Add UI elements in `templates/` if needed
4. Update `engine/config.py` with new settings

### Running in Debug Mode
- Add print statements or use Python debugger
- Check browser console for JavaScript errors
- Monitor the terminal for output logs

## Security Notes

- Store sensitive API keys in environment variables
- Don't commit `nora.db` with sensitive data
- Use HTTPS for any cloud communications
- Be cautious with voice commands that perform sensitive operations

## License

This project is provided as-is for educational and personal use.

## Authors

Developed as a comprehensive voice assistant project with support for multiple services and integrations.

## Support & Contributions

For issues, feature requests, or contributions, please follow standard Git practices:
1. Create a new branch for your feature
2. Make your changes
3. Test thoroughly
4. Create a pull request

## Notes

- The assistant is designed for Windows platform
- Some features require active internet connection
- GPU acceleration is optional but recommended for better performance
- Face authentication can be enabled/disabled as needed




Developed By: M.R.C.P