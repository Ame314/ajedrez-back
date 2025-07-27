from pydantic import BaseModel, EmailStr
from typing import Literal, List, Dict

class User(BaseModel):
    username: str
    email: EmailStr
    password: str  # hashed
    role: Literal["user", "profesor", "admin"] = "user"
    elo: int = 1200

    # Estadísticas generales
    games_played: int = 0
    games_won: int = 0
    games_lost: int = 0
    games_drawn: int = 0

    # Historial de puzzles
    puzzles_resueltos_correctamente: int = 0
    puzzles_resueltos_incorrectamente: int = 0
    historial_puzzles: List[Dict] = []

    # Lecciones vistas o asignadas
    lecciones_vistas: List[str] = []  # IDs o títulos de las lecciones

    # Campos adicionales según el rol
    aulas: List[str] = []  # Si es profesor, IDs o nombres de sus aulas
    solicitudes_aula: List[str] = []  # Alumnos solicitantes, si es profesor

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
