import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./job.db")
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")

if not DEEPSEEK_API_KEY:
    print("[WARNING] DEEPSEEK_API_KEY is not set. AI features will not work.")
