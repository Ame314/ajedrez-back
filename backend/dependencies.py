from fastapi import Depends, HTTPException, Header
from jose import JWTError
from utils.auth import decode_token
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URL, DATABASE_NAME

# Cliente de MongoDB global
_mongo_client = None
_database = None

async def get_database():
    """Obtiene la instancia de la base de datos MongoDB"""
    global _mongo_client, _database
    
    if _database is None:
        _mongo_client = AsyncIOMotorClient(MONGODB_URL)
        _database = _mongo_client[DATABASE_NAME]
    
    return _database

async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Token inválido")

    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=403, detail="Token inválido o expirado")

    return payload  # contiene username, role, etc.
