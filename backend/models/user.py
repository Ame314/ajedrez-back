# backend/models/user.py
from pydantic import BaseModel, EmailStr, Field
from typing import Literal

class User(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: Literal["admin", "user"] = "user"
    elo: int = Field(..., ge=1200)  # mínimo 1200
