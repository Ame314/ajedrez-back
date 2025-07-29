from pydantic import BaseModel
from typing import List

class Aula(BaseModel):
    id: str  # ObjectId como string
    nombre: str
    descripcion: str
    profesor_id: str
    lecciones: List[str] = []
    usuarios: List[str] = []
