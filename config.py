import os
from pathlib import Path
import urllib3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database
DB_URL = os.getenv('DATABASE_URL', 'sqlite:///district_fetch.db')

# LLM Provider Selection
LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'groq')  # 'groq' or 'ollama'

# Groq API
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
# if not GROQ_API_KEY:
#     raise ValueError("GROQ_API_KEY environment variable must be set")
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
GROQ_TEMPERATURE = float(os.getenv('GROQ_TEMPERATURE', '0.3'))

# Ollama API
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://privatechat.setseg.org:11434/api/generate')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'gpt-oss:120b')
OLLAMA_TEMPERATURE = float(os.getenv('OLLAMA_TEMPERATURE', '0.3'))

# HTTP Settings
REQUEST_TIMEOUT = 10  # seconds
USER_AGENT = 'Mozilla/5.0 (compatible; /1.0)'

# Suppress SSL warnings when we intentionally bypass verification
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# HTML Parsing
MAX_TEXT_LENGTH = 15000  # Increased to capture more content for complex pages

# Discovery
MAX_URLS_TO_FILTER = 10  # Top N URLs after LLM filtering

# Project Structure
BASE_DIR = Path(__file__).parent