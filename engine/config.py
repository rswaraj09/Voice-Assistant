import os
from dotenv import load_dotenv
load_dotenv()
ASSISTANT_NAME = "jarvis"
LLM_KEY = os.getenv("LLM_KEY", "")
CHROME_PROFILE = "Default"