#!/usr/bin/env python3
"""
Script para cargar puzzles desde Lichess a la base de datos MongoDB
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.lichess_puzzle_service import lichess_service, PuzzleDifficulty
from dependencies import get_database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def load_puzzles_to_database():
    """Carga puzzles desde Lichess a la base de datos"""
    try:
        db = await get_database()
        puzzle_collection = db["puzzles"]
        
        # Limpiar puzzles existentes (opcional)
        # await puzzle_collection.delete_many({})
        # logger.info("Puzzles existentes eliminados")
        
        # Cargar puzzles para cada dificultad
        difficulties = [
            (PuzzleDifficulty.EASIEST, 20),
            (PuzzleDifficulty.NORMAL, 20),
            (PuzzleDifficulty.HARDEST, 20)
        ]
        
        total_loaded = 0
        
        for difficulty, count in difficulties:
            logger.info(f"Cargando {count} puzzles de dificultad {difficulty.value}...")
            
            for i in range(count):
                try:
                    # Obtener puzzle desde Lichess
                    puzzle_data = await lichess_service.get_puzzle_by_difficulty(difficulty)
                    
                    if puzzle_data:
                        # Formatear para la base de datos
                        db_puzzle = {
                            "puzzle_id": puzzle_data.get("puzzle_id"),
                            "fen": puzzle_data.get("fen"),
                            "moves": " ".join(puzzle_data.get("solution", [])),
                            "rating": puzzle_data.get("rating", 1500),
                            "themes": ",".join(puzzle_data.get("themes", [])),
                            "game_url": puzzle_data.get("game_url", ""),
                            "category": difficulty.value
                        }
                        
                        # Verificar si ya existe
                        existing = await puzzle_collection.find_one({"puzzle_id": db_puzzle["puzzle_id"]})
                        if not existing:
                            await puzzle_collection.insert_one(db_puzzle)
                            total_loaded += 1
                            logger.info(f"Puzzle {db_puzzle['puzzle_id']} cargado ({total_loaded} total)")
                        else:
                            logger.info(f"Puzzle {db_puzzle['puzzle_id']} ya existe")
                    
                    # Rate limiting
                    await asyncio.sleep(1.5)
                    
                except Exception as e:
                    logger.error(f"Error cargando puzzle {i+1} de {difficulty.value}: {e}")
                    continue
        
        # Cargar puzzle diario
        logger.info("Cargando puzzle diario...")
        try:
            daily_puzzle = await lichess_service.get_daily_puzzle()
            if daily_puzzle:
                db_puzzle = {
                    "puzzle_id": daily_puzzle.get("puzzle_id"),
                    "fen": daily_puzzle.get("fen"),
                    "moves": " ".join(daily_puzzle.get("solution", [])),
                    "rating": daily_puzzle.get("rating", 1500),
                    "themes": ",".join(daily_puzzle.get("themes", [])),
                    "game_url": daily_puzzle.get("game_url", ""),
                    "category": "daily"
                }
                
                # Reemplazar puzzle diario existente
                await puzzle_collection.replace_one(
                    {"category": "daily"}, 
                    db_puzzle, 
                    upsert=True
                )
                total_loaded += 1
                logger.info("Puzzle diario cargado")
        except Exception as e:
            logger.error(f"Error cargando puzzle diario: {e}")
        
        logger.info(f"Carga completada. Total de puzzles cargados: {total_loaded}")
        
        # Mostrar estadísticas
        total_puzzles = await puzzle_collection.count_documents({})
        logger.info(f"Total de puzzles en la base de datos: {total_puzzles}")
        
    except Exception as e:
        logger.error(f"Error en la carga de puzzles: {e}")

if __name__ == "__main__":
    asyncio.run(load_puzzles_to_database())
