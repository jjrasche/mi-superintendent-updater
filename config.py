import os
from pathlib import Path
import urllib3

# Database
DB_URL = os.getenv('DATABASE_URL', 'sqlite:///superintendents.db')

# Groq API
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
# if not GROQ_API_KEY:
#     raise ValueError("GROQ_API_KEY environment variable must be set")
GROQ_MODEL = 'llama-3.3-70b-versatile'
GROQ_TEMPERATURE = 0.3

# HTTP Settings
REQUEST_TIMEOUT = 10  # seconds
USER_AGENT = 'Mozilla/5.0 (compatible; SuperintendentScraper/1.0)'

# Suppress SSL warnings when we intentionally bypass verification
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# HTML Parsing
MAX_TEXT_LENGTH = 15000  # Increased to capture more content for complex pages

# Discovery
MAX_URLS_TO_FILTER = 10  # Top N URLs after LLM filtering

# Project Structure
BASE_DIR = Path(__file__).parent