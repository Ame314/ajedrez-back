from pydantic import BaseModel
from typing import List, Optional

class Leccion(BaseModel):
    id: str
    titulo: str
    contenido: str  # Texto o HTML o Markdown
    ejercicios: Optional[List[str]] = []  # IDs de ejercicios si los hay
    aula_id: str
    asignada_a: List[str] = []  # IDs de usuarios a los que se asignó
