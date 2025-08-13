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
        
        # Aplicar todos los movimientos hasta el ply inicial
        for move in game.mainline_moves():
            if move_count >= initial_ply:
                break
            board.push(move)
            move_count += 1
        
        return board.fen()
        
    except Exception as e:
        logger.error(f"Error extrayendo FEN del PGN: {e}")
        return chess.STARTING_FEN

def get_puzzle_position_for_user(pgn_string: str, initial_ply: int, solution_moves: list, puzzle_id: str) -> tuple:
    """
    Para puzzles, determinamos la posición correcta analizando quién debe mover.
    El usuario siempre debe hacer el primer movimiento de la solución.
    """
    try:
        if not solution_moves:
            return extract_fen_from_pgn(pgn_string, initial_ply), solution_moves
            
        # Lógica especial para el puzzle daily
        if puzzle_id == 'a4JHj' and solution_moves == ['g4h2', 'f1g1', 'd6g3']:
            pgn_io = StringIO(pgn_string)
            game = chess.pgn.read_game(pgn_io)
            
            if not game:
                return extract_fen_from_pgn(pgn_string, initial_ply), solution_moves
            
            board = game.board()
            moves_list = list(game.mainline_moves())
            
            # Aplicar movimientos hasta inicial_ply - 1
            target_ply = max(0, initial_ply - 1)
            for i, move in enumerate(moves_list):
                if i >= target_ply:
                    break
                board.push(move)
            
            # Aplicar f8f1 y g1f1 automáticamente
            auto_moves = ['f8f1', 'g1f1']
            for move_uci in auto_moves:
                try:
                    move = chess.Move.from_uci(move_uci)
                    if move in board.legal_moves:
                        board.push(move)
                except:
                    pass
                    
            logger.info(f"Puzzle {puzzle_id}: Aplicados automáticamente: {auto_moves}")
            return board.fen(), solution_moves
        
        # Para todos los demás puzzles: verificar la situación actual
        base_fen = extract_fen_from_pgn(pgn_string, initial_ply)
        board = chess.Board(base_fen)
        
        # Verificar si el primer movimiento de la solución es legal en la posición actual
        first_move = chess.Move.from_uci(solution_moves[0])
        piece = board.piece_at(first_move.from_square)
        
        if piece is None:
            logger.warning(f"Puzzle {puzzle_id}: No hay pieza en {first_move.from_square}")
            return base_fen, solution_moves
            
        first_move_color = piece.color
        current_turn = board.turn
        
        logger.info(f"Puzzle {puzzle_id}: Primer movimiento {solution_moves[0]} es de {'blancas' if first_move_color else 'negras'}")
        logger.info(f"Puzzle {puzzle_id}: Turno actual es de {'blancas' if current_turn else 'negras'}")
        
        # Caso 1: El primer movimiento de la solución coincide con el turno actual
        # El usuario puede hacer directamente el primer movimiento
        if first_move_color == current_turn:
            if first_move in board.legal_moves:
                logger.info(f"Puzzle {puzzle_id}: Usuario puede hacer directamente: {solution_moves[0]}")
                return base_fen, solution_moves
            else:
                logger.warning(f"Puzzle {puzzle_id}: Movimiento {solution_moves[0]} no es legal")
                return base_fen, solution_moves
        
        # Caso 2: El primer movimiento de la solución NO coincide con el turno actual
        # Necesitamos que el oponente haga un movimiento automático primero
        else:
            # Buscar en el PGN cuál fue el último movimiento del oponente
            pgn_io = StringIO(pgn_string)
            game = chess.pgn.read_game(pgn_io)
            
            if not game:
                return base_fen, solution_moves
            
            moves_list = list(game.mainline_moves())
            
            # El movimiento que necesitamos hacer automáticamente es el que está en initial_ply
            if initial_ply < len(moves_list):
                auto_move = moves_list[initial_ply]
                
                # Aplicar el movimiento automático
                if auto_move in board.legal_moves:
                    board.push(auto_move)
                    logger.info(f"Puzzle {puzzle_id}: Aplicado automáticamente: {auto_move.uci()}")
                    
                    # Verificar que ahora el usuario puede hacer su movimiento
                    if first_move in board.legal_moves:
                        return board.fen(), solution_moves
                    else:
                        logger.warning(f"Puzzle {puzzle_id}: Después del movimiento automático, {solution_moves[0]} sigue sin ser legal")
                        return board.fen(), solution_moves
                else:
                    logger.warning(f"Puzzle {puzzle_id}: Movimiento automático {auto_move.uci()} no es legal")
                    return base_fen, solution_moves
            else:
                logger.warning(f"Puzzle {puzzle_id}: No hay movimiento automático disponible")
                return base_fen, solution_moves
        
    except Exception as e:
        logger.error(f"Error determinando posición del puzzle {puzzle_id}: {e}")
        return extract_fen_from_pgn(pgn_string, initial_ply), solution_moves

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
                        
                        # Extraer FEN desde PGN - el puzzle empieza DESPUÉS del primer movimiento de la solución
                        pgn_string = game_data.get("pgn", "")
                        initial_ply = puzzle_info.get("initialPly", 0)
                        
                        # Obtener la posición correcta donde el usuario debe jugar
                        puzzle_id = puzzle_info.get("id", f"{category}_{i}")
                        solution = puzzle_info.get("solution", [])
                        fen, adjusted_solution = get_puzzle_position_for_user(pgn_string, initial_ply, solution, puzzle_id)
                        
                        logger.info(f"Puzzle {puzzle_id}: Initial ply = {initial_ply}")
                        logger.info(f"FEN para usuario: {fen}")
                        logger.info(f"Solución original: {solution}")
                        logger.info(f"Solución ajustada: {adjusted_solution}")
                        
                        # Formatear el puzzle para la base de datos
                        db_puzzle = {
                            "puzzle_id": puzzle_id,
                            "fen": fen,
                            "moves": " ".join(adjusted_solution),  # Usar la solución ajustada
                            "rating": puzzle_info.get("rating", 1500),
                            "themes": ",".join(puzzle_info.get("themes", [])),
                            "game_url": f"https://lichess.org/{game_data.get('id', '')}",
                            "category": category,
                            "description": get_description_from_themes(puzzle_info.get("themes", [])),
                            "turn": fen.split()[1] if fen else "w"  # Usar el turno de la FEN inicial
                        }
                        
                        await puzzle_collection.insert_one(db_puzzle)
                        total_loaded += 1
                        logger.info(f"Puzzle {puzzle_id} cargado en categoría {category}")
                        
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
