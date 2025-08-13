from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from utils.puzzle_database import get_puzzles_by_category
from utils.lichess_puzzle_service import lichess_service

router = APIRouter(prefix="/puzzles", tags=["puzzles"])

@router.get("/categories")
async def get_puzzle_categories():
    """Obtiene las categorías de puzzles disponibles"""
    return {
        "categories": [
            {
                "id": "daily",
                "name": "Puzzle Diario",
                "description": "Un nuevo puzzle cada día"
            },
            {
                "id": "easiest",
                "name": "Más Fácil",
                "description": "Puzzles para principiantes (Rating 800-1200)"
            },
            {
                "id": "normal",
                "name": "Normal",
                "description": "Puzzles de dificultad media (Rating 1200-1800)"
            },
            {
                "id": "hardest",
                "name": "Más Difícil",
                "description": "Puzzles avanzados (Rating 1800-2500)"
            }
        ]
    }

@router.get("/category/{category_id}")
async def get_puzzles_by_category_endpoint(category_id: str):
    """Obtiene puzzles de una categoría específica desde la base de datos"""
    try:
        # Primero intentar obtener desde la base de datos
        puzzles = await get_puzzles_by_category(category_id)
        
        if puzzles and len(puzzles) > 0:
            return puzzles
        
        # Si no hay puzzles en la BD, usar fallback con Lichess
        if category_id == "daily":
            daily_puzzle = await lichess_service.get_daily_puzzle()
            if daily_puzzle:
                formatted_puzzle = format_lichess_puzzle(daily_puzzle, category_id)
                return [formatted_puzzle]
        
        # Para otras categorías, obtener múltiples puzzles
        lichess_puzzles = await lichess_service.get_multiple_puzzles(count=5)
        
        # Filtrar por rating según la categoría
        rating_ranges = {
            "easiest": (800, 1200),
            "normal": (1200, 1800), 
            "hardest": (1800, 2500)
        }
        
        min_rating, max_rating = rating_ranges.get(category_id, (1200, 1800))
        
        formatted_puzzles = []
        for puzzle in lichess_puzzles:
            rating = puzzle.get("rating", 1500)
            if min_rating <= rating <= max_rating:
                formatted_puzzle = format_lichess_puzzle(puzzle, category_id)
                formatted_puzzles.append(formatted_puzzle)
        
        # Si no hay puzzles en el rango, usar todos los puzzles obtenidos
        if not formatted_puzzles:
            formatted_puzzles = [format_lichess_puzzle(p, category_id) for p in lichess_puzzles]
        
        return formatted_puzzles
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo puzzles: {str(e)}")

def format_lichess_puzzle(puzzle_data: dict, category_id: str) -> dict:
    """Formatea un puzzle de Lichess al formato esperado por el frontend"""
    solution_moves = puzzle_data.get("solution", [])
    moves_string = " ".join(solution_moves) if solution_moves else ""
    
    # Obtener el primer tema como descripción
    themes = puzzle_data.get("themes", [])
    description = "Encuentra el mejor movimiento"
    if themes:
        theme_descriptions = {
            "mate": "Mate",
            "mateIn1": "Mate en 1",
            "mateIn2": "Mate en 2", 
            "mateIn3": "Mate en 3",
            "sacrifice": "Sacrificio",
            "fork": "Tenedor",
            "pin": "Clavada",
            "skewer": "Pincho",
            "discoveredAttack": "Ataque descubierto",
            "attraction": "Atracción",
            "deflection": "Desviación",
            "promotion": "Promoción",
            "endgame": "Final"
        }
        description = theme_descriptions.get(themes[0], themes[0].replace("_", " ").title())
    
    # Determinar el turno desde la FEN
    fen = puzzle_data.get("fen", "")
    turn = "w"
    if fen:
        fen_parts = fen.split(" ")
        if len(fen_parts) > 1:
            turn = fen_parts[1]
    
    return {
        "id": puzzle_data.get("puzzle_id", f"lichess_{category_id}"),
        "fen": fen,
        "moves": moves_string,
        "rating": puzzle_data.get("rating", 1500),
        "turn": turn,
        "description": description,
        "category": category_id,
        "themes": themes
    }

@router.get("/test")
async def test_puzzles():
    """Endpoint de prueba para puzzles"""
    return {"message": "Sistema de puzzles funcionando", "status": "OK"}
