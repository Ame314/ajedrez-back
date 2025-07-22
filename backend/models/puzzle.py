from pydantic import BaseModel

class PuzzleRequest(BaseModel):
    PuzzleId: str
    FEN: str
    Moves: str
    Rating: int
    Themes: str
    GameUrl: str
