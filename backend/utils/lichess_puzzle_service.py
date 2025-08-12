import httpx
import asyncio
import random
from typing import List, Optional
from models.puzzle_model import PuzzleResponse, PuzzleDifficulty
import logging

logger = logging.getLogger(__name__)

class LichessPuzzleService:
    """Servicio para obtener puzzles de la API de Lichess"""
    
    def __init__(self):
        self.base_url = "https://lichess.org/api/puzzle"
        self.daily_url = "https://lichess.org/api/puzzle/daily"
        self.rate_limit_delay = 1  # 1 segundo entre requests
        
    async def _make_request(self, url: str) -> Optional[dict]:
        """Hace una request a la API de Lichess con rate limiting"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                await asyncio.sleep(self.rate_limit_delay)
                return response.json()
        except Exception as e:
            logger.error(f"Error en request a Lichess: {e}")
            return None
    
    async def get_daily_puzzle(self) -> Optional[dict]:
        """Obtiene el puzzle diario de Lichess"""
        try:
            data = await self._make_request(self.daily_url)
            if data:
                # Procesamos la respuesta para obtener los datos necesarios
                puzzle_data = data.get("puzzle", {})
                game_data = data.get("game", {})
                
                return {
                    "puzzle_id": puzzle_data.get("id"),
                    "rating": puzzle_data.get("rating", 1500),
                    "solution": puzzle_data.get("solution", []),
                    "fen": puzzle_data.get("fen", ""),
                    "moves": puzzle_data.get("moves", []),
                    "themes": puzzle_data.get("themes", []),
                    "game_url": game_data.get("url", "")
                }
            return None
        except Exception as e:
            logger.error(f"Error obteniendo puzzle diario: {e}")
            return None
    
    async def get_puzzle_by_difficulty(self, difficulty: PuzzleDifficulty) -> Optional[dict]:
        """Obtiene un puzzle según la dificultad especificada"""
        try:
            # Mapeo de dificultades a rangos de rating
            rating_ranges = {
                PuzzleDifficulty.EASIEST: (800, 1200),
                PuzzleDifficulty.NORMAL: (1200, 1800),
                PuzzleDifficulty.HARDEST: (1800, 2500)
            }
            
            min_rating, max_rating = rating_ranges.get(difficulty, (1200, 1800))
            
            # Lichess no tiene filtros directos por rating, usamos el endpoint general
            data = await self._make_request(self.base_url)
            if data:
                puzzle_data = data.get("puzzle", {})
                game_data = data.get("game", {})
                
                return {
                    "puzzle_id": puzzle_data.get("id"),
                    "rating": puzzle_data.get("rating", 1500),
                    "solution": puzzle_data.get("solution", []),
                    "fen": puzzle_data.get("fen", ""),
                    "moves": puzzle_data.get("moves", []),
                    "themes": puzzle_data.get("themes", []),
                    "game_url": game_data.get("url", "")
                }
            return None
        except Exception as e:
            logger.error(f"Error obteniendo puzzle de dificultad {difficulty}: {e}")
            return None
    
    async def get_multiple_puzzles(self, count: int = 3) -> List[dict]:
        """Obtiene múltiples puzzles"""
        puzzles = []
        for _ in range(count):
            puzzle = await self._make_request(self.base_url)
            if puzzle:
                puzzle_data = puzzle.get("puzzle", {})
                game_data = puzzle.get("game", {})
                
                processed_puzzle = {
                    "puzzle_id": puzzle_data.get("id"),
                    "rating": puzzle_data.get("rating", 1500),
                    "solution": puzzle_data.get("solution", []),
                    "fen": puzzle_data.get("fen", ""),
                    "moves": puzzle_data.get("moves", []),
                    "themes": puzzle_data.get("themes", []),
                    "game_url": game_data.get("url", "")
                }
                puzzles.append(processed_puzzle)
            
            # Rate limiting entre requests
            await asyncio.sleep(self.rate_limit_delay)
            
        return puzzles
    
    async def get_all_weekly_puzzles(self) -> dict:
        """Obtiene todos los puzzles semanales por dificultad"""
        weekly_puzzles = {}
        
        for difficulty in [PuzzleDifficulty.EASIEST, PuzzleDifficulty.NORMAL, PuzzleDifficulty.HARDEST]:
            puzzles = []
            for _ in range(3):  # 3 puzzles por dificultad
                puzzle = await self.get_puzzle_by_difficulty(difficulty)
                if puzzle:
                    puzzles.append(puzzle)
                await asyncio.sleep(self.rate_limit_delay)
            
            weekly_puzzles[difficulty.value] = puzzles
            
        return weekly_puzzles

# Instancia global del servicio
lichess_service = LichessPuzzleService()
