from fastapi import HTTPException, status, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from pymongo import MongoClient
from datetime import datetime
import os
from app.config import settings

# MongoDB connection
client = MongoClient(settings.DATABASE_URL)
db = client.capibot_voice_recognition
api_keys_collection = db.api_keys

security = HTTPBearer(auto_error=False)

async def get_api_key_from_header(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Extract API key from X-API-Key header"""
    return x_api_key

async def get_api_key_from_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Extract API key from Authorization header"""
    if credentials:
        return credentials.credentials
    return None

async def validate_api_key(
    api_key_header: Optional[str] = Depends(get_api_key_from_header),
    api_key_auth: Optional[str] = Depends(get_api_key_from_auth),
    api_key_body: Optional[str] = None
):
    """
    Validate API key from multiple sources:
    1. X-API-Key header
    2. Authorization header
    3. Request body
    """
    api_key = api_key_header or api_key_auth or api_key_body
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide it in X-API-Key header, Authorization header, or request body."
        )
    
    # Check if API key exists and is active
    key_doc = api_keys_collection.find_one({"key": api_key, "active": True})
    
    if not key_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key"
        )
    
    # Update last_used timestamp
    api_keys_collection.update_one(
        {"_id": key_doc["_id"]},
        {"$set": {"last_used": datetime.utcnow()}}
    )
    
    return key_doc

def create_api_key(name: str) -> str:
    """Create a new API key for a client"""
    import secrets
    api_key = secrets.token_urlsafe(32)
    
    key_doc = {
        "key": api_key,
        "name": name,
        "active": True,
        "created_at": datetime.utcnow(),
        "last_used": None
    }
    
    api_keys_collection.insert_one(key_doc)
    return api_key

def deactivate_api_key(api_key: str) -> bool:
    """Deactivate an API key"""
    result = api_keys_collection.update_one(
        {"key": api_key},
        {"$set": {"active": False}}
    )
    return result.modified_count > 0


