# /backend/models/live_game.py
from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime

class Move(BaseModel):
    from_square: str  # e2, e4, etc.
    to_square: str
    piece: str  # K, Q, R, B, N, P
    promotion: Optional[str] = None  # Para promociones de peones
    san: str  # Notación algebraica estándar
    fen: str  # Estado del tablero después del movimiento

class LiveGame(BaseModel):
    game_id: str
    white_player: str
    black_player: str
    white_elo: int
    black_elo: int
    current_turn: Literal["white", "black"] = "white"
    moves: List[Move] = []
    status: Literal["waiting", "active", "paused", "finished"] = "waiting"
    result: Optional[Literal["1-0", "0-1", "1/2-1/2", "*"]] = "*"
    winner: Optional[str] = None
    time_control: dict = {"white_time": 600, "black_time": 600}  # Tiempo en segundos
    created_at: datetime
    updated_at: datetime

class GameMessage(BaseModel):
    type: Literal["move", "chat", "offer_draw", "resign", "time_update", "game_start", "game_end"]
    data: dict
    player: str
    timestamp: datetime = datetime.utcnow()

class MoveMessage(BaseModel):
    type: Literal["move"] = "move"
    move: Move
    player: str

class ChatMessage(BaseModel):
    type: Literal["chat"] = "chat"
    message: str
    player: str

class GameAction(BaseModel):
    type: Literal["offer_draw", "resign", "accept_draw", "decline_draw"]
    player: str
