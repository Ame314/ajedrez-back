from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any

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

@router.get("/test")
async def test_puzzles():
    """Endpoint de prueba para puzzles"""
    return {"message": "Sistema de puzzles funcionando", "status": "OK"}
