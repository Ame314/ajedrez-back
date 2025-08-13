from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from utils.puzzle_database import get_puzzles_by_category

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
        puzzles = await get_puzzles_by_category(category_id)
        
        if not puzzles or len(puzzles) == 0:
            raise HTTPException(status_code=404, detail=f"No se encontraron puzzles para la categoría: {category_id}")
        
        return puzzles
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo puzzles: {str(e)}")

@router.get("/test")
async def test_puzzles():
    """Endpoint de prueba para puzzles"""
    return {"message": "Sistema de puzzles funcionando", "status": "OK"}
