import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY")
    DEBUG_LOG_DIR: str = os.getenv("DEBUG_LOG_DIR", os.path.join(os.getcwd(), "logs"))

settings = Settings()
