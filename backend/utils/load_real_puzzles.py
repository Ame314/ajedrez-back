#!/usr/bin/env python3
"""
Script para cargar puzzles desde los archivos JSON proporcionados
"""
import asyncio
import sys
import os
import json
import chess
import chess.pgn
from io import StringIO

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dependencies import get_database
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_fen_from_pgn(pgn_string: str, initial_ply: int) -> str:
    """Extrae la FEN desde un PGN en el ply específico"""
    try:
        pgn_io = StringIO(pgn_string)
        game = chess.pgn.read_game(pgn_io)
        
        if not game:
            return chess.STARTING_FEN
        
        board = game.board()
        move_count = 0
        
        for move in game.mainline_moves():
            if move_count >= initial_ply:
                break
            board.push(move)
            move_count += 1
        
        return board.fen()
        
    except Exception as e:
        logger.error(f"Error extrayendo FEN del PGN: {e}")
        return chess.STARTING_FEN

async def load_puzzles_from_json():
    """Carga puzzles desde los archivos JSON proporcionados"""
    try:
        db = await get_database()
        puzzle_collection = db["puzzles"]
        
        # Limpiar todos los puzzles existentes
        await puzzle_collection.delete_many({})
        logger.info("Puzzles anteriores eliminados")
        
        # Archivos JSON con sus categorías correspondientes
        json_files = {
            "daily": "/app/PuzzlesMockup_Diarios.json",
            "easiest": "/app/PuzzlesMockup_Faciles.json", 
            "normal": "/app/PuzzlesMockup_Intermedio.json",
            "hardest": "/app/PuzzlesMockup_Dificiles.json"
        }
        
        total_loaded = 0
        
        for category, file_path in json_files.items():
            try:
                logger.info(f"Cargando puzzles de categoría: {category}")
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Manejar estructura diferente para diarios (objeto único vs array)
                if category == "daily":
                    puzzle_data = [data]  # Convertir a array para procesamiento uniforme
                else:
                    puzzle_data = data
                
                for i, item in enumerate(puzzle_data):
                    try:
                        game_data = item.get("game", {})
                        puzzle_info = item.get("puzzle", {})
                        
                        # Extraer FEN desde PGN
                        pgn_string = game_data.get("pgn", "")
                        initial_ply = puzzle_info.get("initialPly", 0)
                        fen = extract_fen_from_pgn(pgn_string, initial_ply)
                        
                        # Formatear el puzzle para la base de datos
                        db_puzzle = {
                            "puzzle_id": puzzle_info.get("id", f"{category}_{i}"),
                            "fen": fen,
                            "moves": " ".join(puzzle_info.get("solution", [])),
                            "rating": puzzle_info.get("rating", 1500),
                            "themes": ",".join(puzzle_info.get("themes", [])),
                            "game_url": f"https://lichess.org/{game_data.get('id', '')}",
                            "category": category,
                            "description": get_description_from_themes(puzzle_info.get("themes", [])),
                            "turn": fen.split()[1] if fen else "w"
                        }
                        
                        await puzzle_collection.insert_one(db_puzzle)
                        total_loaded += 1
                        logger.info(f"Puzzle {db_puzzle['puzzle_id']} cargado en categoría {category}")
                        
                    except Exception as e:
                        logger.error(f"Error procesando puzzle {i} de {category}: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error cargando archivo {file_path}: {e}")
                continue
        
        logger.info(f"Carga completada. Total de puzzles cargados: {total_loaded}")
        
        # Mostrar estadísticas por categoría
        for category in json_files.keys():
            count = await puzzle_collection.count_documents({"category": category})
            logger.info(f"Categoría {category}: {count} puzzles")
        
    except Exception as e:
        logger.error(f"Error en la carga de puzzles: {e}")

def get_description_from_themes(themes):
    """Obtiene una descripción basada en los temas del puzzle"""
    theme_descriptions = {
        "mateIn1": "Mate en 1",
        "mateIn2": "Mate en 2", 
        "mateIn3": "Mate en 3",
        "mate": "Mate",
        "sacrifice": "Sacrificio",
        "fork": "Tenedor",
        "pin": "Clavada",
        "skewer": "Pincho",
        "discoveredAttack": "Ataque descubierto",
        "attraction": "Atracción",
        "deflection": "Desviación",
        "promotion": "Promoción",
        "endgame": "Final",
        "middlegame": "Medio juego",
        "opening": "Apertura",
        "crushing": "Aplastante",
        "advantage": "Ventaja",
        "kingsideAttack": "Ataque al rey",
        "advancedPawn": "Peón avanzado",
        "pawnEndgame": "Final de peones",
        "trappedPiece": "Pieza atrapada",
        "clearance": "Despeje"
    }
    
    for theme in themes:
        if theme in theme_descriptions:
            return theme_descriptions[theme]
    
    return "Encuentra el mejor movimiento"

if __name__ == "__main__":
    asyncio.run(load_puzzles_from_json())
