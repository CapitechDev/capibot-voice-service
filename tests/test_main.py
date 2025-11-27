from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, MagicMock
import pytest

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "CapiBot Voice Recognition Service",
        "status": "running",
        "version": "1.0.0"
    }

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@patch("app.main.transcription_service")
@patch("app.main.webhook_service")
@patch("app.main.validate_api_key")
def test_transcribe_audio_file(mock_validate, mock_webhook, mock_transcription):
    # Mock auth
    mock_validate.return_value = {"name": "test-key", "_id": "123"}
    
    # Mock transcription
    mock_transcription.validate_audio_file.return_value = True
    mock_transcription.transcribe_audio_file.return_value = ("Teste de transcrição", "pt", 5.0)
    
    # Mock webhook
    mock_webhook.send_transcription_result.return_value = True
    
    # Create a dummy file
    files = {"audio": ("test.mp3", b"dummy content", "audio/mpeg")}
    
    response = client.post("/transcribe", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["transcription_id"].startswith("trans_123_")

@patch("app.main.transcription_service")
@patch("app.main.webhook_service")
@patch("app.main.validate_api_key")
def test_transcribe_base64(mock_validate, mock_webhook, mock_transcription):
    # Mock auth
    mock_validate.return_value = {"name": "test-key", "_id": "123"}
    
    # Mock transcription
    mock_transcription.transcribe_base64_audio.return_value = ("Teste base64", "pt", 3.0)
    
    # Mock webhook
    mock_webhook.send_transcription_result.return_value = True
    
    payload = {
        "audio_base64": "data:audio/mp3;base64,dummy"
    }
    
    response = client.post("/transcribe", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
