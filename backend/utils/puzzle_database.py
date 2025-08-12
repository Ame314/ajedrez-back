from dependencies import get_database
from models.puzzle_model import PuzzleModel
from typing import List, Dict, Any
import random

async def get_puzzles_by_category(category_id: str) -> List[Dict[str, Any]]:
    """
    Obtiene puzzles de una categoría específica
    """
    db = get_database()
    puzzle_collection = db["puzzles"]
    
    try:
        # Determinar el rango de rating según la categoría
        rating_ranges = {
            "daily": {"min": 800, "max": 2500},  # Rango amplio para puzzle diario
            "easiest": {"min": 800, "max": 1200},
            "normal": {"min": 1200, "max": 1800},
            "hardest": {"min": 1800, "max": 2500}
        }
        
        rating_range = rating_ranges.get(category_id, {"min": 800, "max": 2500})
        
        # Buscar puzzles en el rango de rating
        query = {
            "rating": {
                "$gte": rating_range["min"], 
                "$lte": rating_range["max"]
            }
        }
        
        # Obtener puzzles de la base de datos
        puzzles_cursor = puzzle_collection.find(query).limit(20)
        puzzles = await puzzles_cursor.to_list(length=20)
        
        # Si no hay puzzles en la base de datos, crear puzzles de ejemplo
        if not puzzles:
            puzzles = create_sample_puzzles(category_id)
        
        # Convertir ObjectId a string y formatear datos
        formatted_puzzles = []
        for puzzle in puzzles:
            if "_id" in puzzle:
                puzzle["_id"] = str(puzzle["_id"])
            
            formatted_puzzle = {
                "id": puzzle.get("_id", f"sample_{category_id}_{len(formatted_puzzles)}"),
                "fen": puzzle.get("fen", ""),
                "moves": puzzle.get("moves", ""),
                "rating": puzzle.get("rating", 1000),
                "turn": puzzle.get("fen", "").split()[1] if puzzle.get("fen") else "w",
                "description": puzzle.get("description", "Encuentra el mejor movimiento"),
                "category": category_id
            }
            formatted_puzzles.append(formatted_puzzle)
        
        return formatted_puzzles
        
    except Exception as e:
        print(f"Error obteniendo puzzles de {category_id}: {str(e)}")
        # En caso de error, devolver puzzles de ejemplo
        return create_sample_puzzles(category_id)

def create_sample_puzzles(category_id: str) -> List[Dict[str, Any]]:
    """
    Crea puzzles de ejemplo para testing
    """
    sample_puzzles = {
        "daily": [
            {
                "id": "daily_1",
                "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
                "moves": "d1h5 g6h5 c4f7",
                "rating": 1200,
                "turn": "w",
                "description": "Mate en 2 movimientos",
                "category": category_id
            }
        ],
        "easiest": [
            {
                "id": "easiest_1",
                "fen": "rnbqkb1r/pppp1ppp/5n2/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
                "moves": "f1c4",
                "rating": 900,
                "turn": "w",
                "description": "Desarrolla el alfil",
                "category": category_id
            },
            {
                "id": "easiest_2",
                "fen": "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
                "moves": "g1f3",
                "rating": 800,
                "turn": "w",
                "description": "Desarrolla el caballo",
                "category": category_id
            }
        ],
        "normal": [
            {
                "id": "normal_1",
                "fen": "r1bq1rk1/ppp2ppp/2n2n2/2bpp3/2B1P3/3P1N2/PPP2PPP/RNBQ1RK1 w - - 0 6",
                "moves": "c4f7 f8f7 d1h5",
                "rating": 1400,
                "turn": "w",
                "description": "Sacrificio de alfil",
                "category": category_id
            }
        ],
        "hardest": [
            {
                "id": "hardest_1",
                "fen": "2rr3k/pp3pp1/1nnqbN1p/3ppN2/2nPP3/2P1B3/PPQ2PPP/R4RK1 w - - 0 1",
                "moves": "f6h7 g8h7 f5g7",
                "rating": 2000,
                "turn": "w",
                "description": "Combinación táctica compleja",
                "category": category_id
            }
        ]
    }
    
    return sample_puzzles.get(category_id, sample_puzzles["easiest"])