import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "mongodb://localhost:27017/capibot-voice-recognition")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
    
    # Webhook Configuration
    N8N_WEBHOOK_URL: str = os.getenv("N8N_WEBHOOK_URL", "http://n8n:5678/webhook/voice-transcription")
    WEBHOOK_TIMEOUT: int = int(os.getenv("WEBHOOK_TIMEOUT", "30"))
    WEBHOOK_RETRIES: int = int(os.getenv("WEBHOOK_RETRIES", "3"))
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "CapiBot Voice Recognition Service"
    
    # File upload limits
    MAX_FILE_SIZE: int = 25 * 1024 * 1024  # 25MB
    ALLOWED_AUDIO_TYPES: list = ["audio/mpeg", "audio/wav", "audio/mp4", "audio/m4a", "audio/x-m4a", "audio/ogg"]

settings = Settings()

