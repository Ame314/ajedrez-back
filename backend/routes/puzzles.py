from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

router = APIRouter(prefix="/puzzles", tags=["puzzles"])

# Datos de ejemplo para puzzles
SAMPLE_PUZZLES = {
    "daily": [
        {
            "id": "daily_1",
            "fen": "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
            "moves": "d1h5 g6h5 c4f7",
            "rating": 1200,
            "turn": "w",
            "description": "Mate en 2 movimientos",
            "category": "daily"
        },
        {
            "id": "daily_2", 
            "fen": "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/3P1N2/PPP2PPP/RNBQK2R w KQkq - 0 5",
            "moves": "c4f7 e8f7 d1h5",
            "rating": 1300,
            "turn": "w", 
            "description": "Sacrificio de alfil",
            "category": "daily"
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
            "category": "easiest"
        },
        {
            "id": "easiest_2",
            "fen": "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
            "moves": "g1f3",
            "rating": 800,
            "turn": "w",
            "description": "Desarrolla el caballo",
            "category": "easiest"
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
            "category": "normal"
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
            "category": "hardest"
        }
    ]
}

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
    """Obtiene puzzles de una categoría específica"""
    if category_id not in SAMPLE_PUZZLES:
        raise HTTPException(status_code=404, detail=f"Categoría '{category_id}' no encontrada")
    
    return SAMPLE_PUZZLES[category_id]

@router.get("/test")
async def test_puzzles():
    """Endpoint de prueba para puzzles"""
    return {"message": "Sistema de puzzles funcionando", "status": "OK"}
