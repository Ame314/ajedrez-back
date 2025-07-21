# /backend/models/login.py
from pydantic import BaseModel, EmailStr
from pydantic import BaseModel

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
