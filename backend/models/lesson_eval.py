from typing import List, Optional
from pydantic import BaseModel

class PV(BaseModel):
    cp: Optional[int] = None  # centipawns, si no es mate
    mate: Optional[int] = None  # si es mate
    line: str

class Eval(BaseModel):
    knodes: int
    depth: int
    pvs: List[PV]

class LessonEval(BaseModel):
    fen: str
    evals: List[Eval]
