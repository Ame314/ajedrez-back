# /backend/models/game.py
from pydantic import BaseModel
from typing import List
from datetime import datetime

class Game(BaseModel):
    user: str
    opponent: str
    moves: List[str]
    result: str
    date_played: datetime
