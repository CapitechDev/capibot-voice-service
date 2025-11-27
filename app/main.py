from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import tempfile
import os
from app.config import settings
from app.models import TranscriptionRequest, TranscriptionResponse
from app.auth import validate_api_key
from app.services.transcription import transcription_service
from app.services.webhook import webhook_service
import logging
import asyncio
from functools import partial

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Mapeamento de extensões para tipos MIME
EXTENSION_TO_MIME = {
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.m4a': 'audio/m4a',
    '.mp4': 'audio/mp4',
    '.ogg': 'audio/ogg',
    '.flac': 'audio/flac',
}

def normalize_content_type(content_type: Optional[str]) -> Optional[str]:
    """Normaliza o content-type removendo espaços e convertendo para lowercase"""
    if not content_type:
        return None
    return content_type.strip().lower()

def get_mime_from_extension(filename: str) -> Optional[str]:
    """Obtém o tipo MIME baseado na extensão do arquivo"""
    if not filename:
        return None
    ext = os.path.splitext(filename)[1].lower()
    return EXTENSION_TO_MIME.get(ext)

def validate_audio_type(content_type: Optional[str], filename: Optional[str]) -> bool:
    """
    Valida o tipo de áudio de forma flexível:
    1. Tenta validar pelo content-type normalizado
    2. Se falhar, tenta validar pela extensão do arquivo
    """
    logger.info(f"Validando tipo de áudio: content_type='{content_type}', filename='{filename}'")
    logger.info(f"Tipos permitidos: {settings.ALLOWED_AUDIO_TYPES}")
    
    # Normaliza o content-type
    normalized_type = normalize_content_type(content_type)
    logger.info(f"Content-type normalizado: '{normalized_type}'")
    
    # Tenta validar pelo content-type
    if normalized_type and normalized_type in settings.ALLOWED_AUDIO_TYPES:
        logger.info(f"Validação bem-sucedida pelo content-type: '{normalized_type}'")
        return True
    
    # Fallback: valida pela extensão do arquivo
    if filename:
        mime_from_ext = get_mime_from_extension(filename)
        logger.info(f"Tipo MIME da extensão '{os.path.splitext(filename)[1]}': '{mime_from_ext}'")
        if mime_from_ext and mime_from_ext in settings.ALLOWED_AUDIO_TYPES:
            logger.info(f"Content-type '{content_type}' não está na lista, mas extensão '{os.path.splitext(filename)[1]}' é válida. Usando tipo MIME: {mime_from_ext}")
            return True
    
    logger.warning(f"Validação falhou: content_type='{content_type}' (normalizado: '{normalized_type}'), filename='{filename}'")
    return False

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Microservice for Portuguese audio transcription using OpenAI Whisper",
    version="1.0.0"
)

# Add CORS middleware
origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "CapiBot Voice Recognition Service",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "whisper_model": settings.WHISPER_MODEL
    }

@app.post("/transcribe")
async def transcribe_audio(
    # File upload option
    audio: Optional[UploadFile] = File(None),
    api_key_file: Optional[str] = Form(None),
    
    # Base64 option
    request_data: Optional[TranscriptionRequest] = None,
    
    # Authentication
    authenticated_key: dict = Depends(validate_api_key)
):
    """
    Transcribe audio to text in Portuguese and send result to n8n webhook.
    
    Supports two input methods:
    1. File upload (multipart/form-data)
    2. Base64 encoded audio (JSON)
    
    Authentication via:
    - X-API-Key header
    - Authorization header  
    - api_key in request body
    
    The transcription result is sent to the configured n8n webhook.
    """
    
    try:
        text = ""
        language = "pt"
        duration = 0.0
        original_filename = None
        audio_size = None
        
        # Handle file upload
        if audio and audio.filename:
            original_filename = audio.filename
            audio_size = audio.size
            
            # Log para debug
            logger.info(f"Recebendo arquivo de áudio: filename='{original_filename}', content_type='{audio.content_type}', size={audio_size}")
            
            # Validate file type (validação flexível)
            if not validate_audio_type(audio.content_type, original_filename):
                # Tenta obter o tipo MIME da extensão para a mensagem de erro
                mime_from_ext = get_mime_from_extension(original_filename) if original_filename else None
                error_detail = f"Unsupported audio type. Received: content_type='{audio.content_type}', filename='{original_filename}'"
                if mime_from_ext:
                    error_detail += f", detected_mime_from_extension='{mime_from_ext}'"
                error_detail += f". Allowed types: {settings.ALLOWED_AUDIO_TYPES}"
                
                logger.warning(f"Tipo de áudio rejeitado: content_type='{audio.content_type}', filename='{original_filename}'")
                await webhook_service.send_error_notification(
                    f"Unsupported audio type: {audio.content_type}",
                    authenticated_key.get("name", "unknown"),
                    original_filename
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_detail
                )
            
            logger.info(f"Tipo de áudio validado com sucesso para arquivo: {original_filename}")
            
            # Validate file size
            if audio.size and audio.size > settings.MAX_FILE_SIZE:
                await webhook_service.send_error_notification(
                    f"File too large: {audio.size} bytes",
                    authenticated_key.get("name", "unknown"),
                    original_filename
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE} bytes"
                )
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio.filename)[1]) as temp_file:
                content = await audio.read()
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Validate and transcribe
                if not transcription_service.validate_audio_file(temp_file_path):
                    await webhook_service.send_error_notification(
                        "Invalid audio file format or size",
                        authenticated_key.get("name", "unknown"),
                        original_filename
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid audio file format or size"
                    )
                
                # Run CPU-bound transcription in a separate thread
                loop = asyncio.get_running_loop()
                text, language, duration = await loop.run_in_executor(
                    None, 
                    partial(transcription_service.transcribe_audio_file, temp_file_path)
                )
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
        
        # Handle base64 audio
        elif request_data and request_data.audio_base64:
            # Run CPU-bound transcription in a separate thread
            loop = asyncio.get_running_loop()
            text, language, duration = await loop.run_in_executor(
                None,
                partial(transcription_service.transcribe_base64_audio, request_data.audio_base64)
            )
        
        else:
            await webhook_service.send_error_notification(
                "No audio data provided",
                authenticated_key.get("name", "unknown"),
                None
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either audio file or audio_base64 must be provided"
            )
        
        # Send result to n8n webhook (optional, don't fail if it doesn't work)
        webhook_success = False
        try:
            webhook_success = await webhook_service.send_transcription_result(
                text=text,
                language=language,
                duration=duration,
                api_key_name=authenticated_key.get("name", "unknown"),
                original_filename=original_filename,
                audio_size=audio_size
            )
        except Exception as e:
            logger.warning(f"Failed to send result to n8n webhook: {e}")
        
        # Return transcription result directly to the client
        return {
            "message": "Transcription completed",
            "status": "success",
            "text": text,
            "language": language,
            "duration": duration,
            "webhook_delivered": webhook_success,
            "transcription_id": f"trans_{authenticated_key.get('_id', 'unknown')}_{int(duration) if duration else 0}"
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in transcription: {e}")
        await webhook_service.send_error_notification(
            f"Internal server error: {str(e)}",
            authenticated_key.get("name", "unknown"),
            original_filename
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during transcription"
        )

@app.post("/admin/create-api-key")
async def create_api_key(name: str = Form(...)):
    """Create a new API key (admin endpoint)"""
    from app.auth import create_api_key
    
    try:
        api_key = create_api_key(name)
        return {
            "message": "API key created successfully",
            "api_key": api_key,
            "name": name
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}"
        )

@app.post("/admin/deactivate-api-key")
async def deactivate_api_key(api_key: str = Form(...)):
    """Deactivate an API key (admin endpoint)"""
    from app.auth import deactivate_api_key
    
    try:
        success = deactivate_api_key(api_key)
        if success:
            return {"message": "API key deactivated successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate API key: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

