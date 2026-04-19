import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # engine/
ROOT_DIR = os.path.dirname(BASE_DIR)                    # project root

load_dotenv(os.path.join(ROOT_DIR, '.env'))

ASSISTANT_NAME = "jarvis"
LLM_KEY        = os.getenv("LLM_KEY", "")
CHROME_PROFILE = "Default"