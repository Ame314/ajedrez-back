from pydantic import BaseModel, EmailStr
from typing import Literal

class User(BaseModel):
    username: str
    email: EmailStr
    password: str  # hashed
    role: Literal["user", "profesor", "admin"] = "user"
    elo: int = 1200

    games_played: int = 0
    games_won: int = 0
    games_lost: int = 0
    games_drawn: int = 0
