import whisper
import base64
import io
import tempfile
import os
from typing import Optional, Tuple
from fastapi import HTTPException, status
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the Whisper model"""
        try:
            logger.info(f"Loading Whisper model: {settings.WHISPER_MODEL}")
            self.model = whisper.load_model(settings.WHISPER_MODEL)
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load speech recognition model"
            )
    
    def transcribe_audio_file(self, audio_file_path: str) -> Tuple[str, str, float]:
        """
        Transcribe audio from file path
        Returns: (text, language, duration)
        """
        if not self.model:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Speech recognition model not loaded"
            )
        
        try:
            # Transcribe with Portuguese language hint
            result = self.model.transcribe(
                audio_file_path,
                language="pt",  # Force Portuguese
                fp16=False  # Use fp32 for better compatibility
            )
            
            text = result["text"].strip()
            language = result.get("language", "pt")
            
            # Calculate duration from segments (more accurate)
            segments = result.get("segments", [])
            if segments:
                # Get the end time of the last segment
                duration = segments[-1].get("end", 0.0)
            else:
                # Fallback: approximate duration
                duration = 0.0
            
            return text, language, duration
            
        except FileNotFoundError as e:
            if "ffmpeg" in str(e).lower():
                logger.error(f"Transcription error: ffmpeg not found. Please install ffmpeg: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="ffmpeg is required for audio transcription but is not installed. Please install ffmpeg: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)"
                )
            else:
                logger.error(f"Transcription error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to transcribe audio: {str(e)}"
                )
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            error_msg = str(e)
            if "ffmpeg" in error_msg.lower():
                error_msg = "ffmpeg is required for audio transcription but is not installed. Please install ffmpeg: brew install ffmpeg (macOS) or apt-get install ffmpeg (Linux)"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to transcribe audio: {error_msg}"
            )
    
    def transcribe_base64_audio(self, audio_base64: str) -> Tuple[str, str, float]:
        """
        Transcribe audio from base64 string
        Returns: (text, language, duration)
        """
        try:
            # Decode base64 audio
            audio_data = base64.b64decode(audio_base64)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                temp_file.write(audio_data)
                temp_file_path = temp_file.name
            
            try:
                # Transcribe the temporary file
                result = self.transcribe_audio_file(temp_file_path)
                return result
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Base64 transcription error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to process base64 audio: {str(e)}"
            )
    
    def validate_audio_file(self, file_path: str) -> bool:
        """Validate audio file format and size"""
        if not os.path.exists(file_path):
            return False
        
        # Check file size (25MB limit)
        file_size = os.path.getsize(file_path)
        if file_size > settings.MAX_FILE_SIZE:
            return False
        
        # Check file extension
        allowed_extensions = ['.mp3', '.wav', '.m4a', '.mp4', '.ogg', '.flac']
        file_ext = os.path.splitext(file_path)[1].lower()
        
        return file_ext in allowed_extensions

# Global service instance
transcription_service = TranscriptionService()


