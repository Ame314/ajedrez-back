from fastapi import Depends, HTTPException, Header
from jose import JWTError
from utils.auth import decode_token

async def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Token inválido")

    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(status_code=403, detail="Token inválido o expirado")

    return payload  # contiene username, role, etc.
