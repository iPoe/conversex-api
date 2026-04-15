import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # "cloud" por defecto, cámbialo a "local" en tu .env para usar Docker.
    ENV: str = os.getenv("ENV", "cloud").lower()

    # --- Configuración Cloud (Supabase Real) ---
    _CLOUD_URL: str = os.getenv("SUPABASE_URL")
    _CLOUD_KEY: str = os.getenv("SUPABASE_KEY")

    # --- Configuración Local (Supabase CLI / Docker) ---
    _LOCAL_URL: str = "http://127.0.0.1:54321"
    # Key 'anon' local estándar
    _LOCAL_KEY: str = os.getenv("LOCAL_SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InByb2plY3QtcmVmIiwicm9sZSI6ImFub24iLCJpYXQiOjE2MTYxNjE2MTYsImV4cCI6MTkyNzA0MTYxNn0.VGFmX2J1Y2tldF9rZXk")

    def __init__(self):
        # Determinamos los valores finales al instanciar
        if self.ENV == "local":
            self.SUPABASE_URL = self._LOCAL_URL
            self.SUPABASE_KEY = self._LOCAL_KEY
        else:
            self.SUPABASE_URL = self._CLOUD_URL
            self.SUPABASE_KEY = self._CLOUD_KEY
        
        # Log de seguridad (solo URL)
        print(f"🔌 Conversex API conectada a: {self.ENV.upper()} ({self.SUPABASE_URL})")

    DEBUG_LOG_DIR: str = os.getenv("DEBUG_LOG_DIR", os.path.join(os.getcwd(), "logs"))

settings = Settings()
