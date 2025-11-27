import httpx
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import json
from app.config import settings

class WebhookService:
    def __init__(self):
        self.webhook_url = settings.N8N_WEBHOOK_URL
        self.timeout = settings.WEBHOOK_TIMEOUT
        self.retries = settings.WEBHOOK_RETRIES
    
    async def send_transcription_result(
        self, 
        text: str, 
        language: str, 
        duration: float,
        api_key_name: str,
        original_filename: Optional[str] = None,
        audio_size: Optional[int] = None
    ) -> bool:
        """
        Send transcription result to n8n webhook
        
        Args:
            text: Transcribed text
            language: Detected language
            duration: Audio duration in seconds
            api_key_name: Name of the API key used
            original_filename: Original audio filename (if file upload)
            audio_size: Audio file size in bytes (if file upload)
        
        Returns:
            bool: True if webhook was successful, False otherwise
        """
        
        payload = {
            "transcription": {
                "text": text,
                "language": language,
                "duration": duration,
                "timestamp": datetime.utcnow().isoformat(),
                "api_key_name": api_key_name,
                "source": "capibot-voice-service"
            },
            "metadata": {
                "original_filename": original_filename,
                "audio_size": audio_size,
                "service_version": "1.0.0"
            }
        }
        
        for attempt in range(self.retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        self.webhook_url,
                        json=payload,
                        headers={
                            "Content-Type": "application/json",
                            "User-Agent": "CapiBot-Voice-Service/1.0.0"
                        }
                    )
                    
                    if response.status_code in [200, 201, 202]:
                        print(f"Webhook sent successfully to n8n (attempt {attempt + 1})")
                        return True
                    else:
                        print(f"Webhook failed with status {response.status_code} (attempt {attempt + 1})")
                        
            except httpx.TimeoutException:
                print(f"Webhook timeout (attempt {attempt + 1})")
            except httpx.ConnectError:
                print(f"Webhook connection error (attempt {attempt + 1})")
            except Exception as e:
                print(f"Webhook error: {e} (attempt {attempt + 1})")
            
            # Wait before retry (exponential backoff)
            if attempt < self.retries - 1:
                wait_time = 2 ** attempt
                print(f"Retrying webhook in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
        
        print(f"Webhook failed after {self.retries} attempts")
        return False
    
    async def send_error_notification(
        self,
        error_message: str,
        api_key_name: str,
        original_filename: Optional[str] = None
    ) -> bool:
        """
        Send error notification to n8n webhook
        
        Args:
            error_message: Error description
            api_key_name: Name of the API key used
            original_filename: Original audio filename (if file upload)
        
        Returns:
            bool: True if webhook was successful, False otherwise
        """
        
        payload = {
            "error": {
                "message": error_message,
                "timestamp": datetime.utcnow().isoformat(),
                "api_key_name": api_key_name,
                "source": "capibot-voice-service"
            },
            "metadata": {
                "original_filename": original_filename,
                "service_version": "1.0.0"
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "CapiBot-Voice-Service/1.0.0"
                    }
                )
                
                if response.status_code in [200, 201, 202]:
                    print("Error notification sent to n8n")
                    return True
                else:
                    print(f"Error notification failed with status {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"Error notification failed: {e}")
            return False

# Global service instance
webhook_service = WebhookService()

