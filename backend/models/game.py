# /backend/models/game.py
from pydantic import BaseModel
from typing import List, Literal
from datetime import datetime

class Game(BaseModel):
    white_player: str
    black_player: str
    white_elo: int
    black_elo: int
    moves: List[str]
    result_code: Literal["1-0", "0-1", "1/2"]  # Resultado estándar ajedrecístico
    winner: str  # Puede ser el nombre del ganador o "draw"
    date_played: datetime
