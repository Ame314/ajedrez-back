from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from utils.puzzle_database import get_puzzles_by_category
import sys
import os
import json
import chess
import chess.pgn
from io import StringIO
from dependencies import get_database
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

@router.post("/cargar-puzzles")
async def cargar_puzzles():
    """Carga puzzles desde los archivos JSON a la base de datos"""
    try:
        db = await get_database()
        puzzle_collection = db["puzzles"]
        
        # Limpiar todos los puzzles existentes
        delete_result = await puzzle_collection.delete_many({})
        logger.info(f"Puzzles anteriores eliminados: {delete_result.deleted_count}")
        
        # Archivos JSON con sus categorías correspondientes
        json_files = {
            "daily": "/app/PuzzlesMockup_Diarios.json",
            "easiest": "/app/PuzzlesMockup_Faciles.json", 
            "normal": "/app/PuzzlesMockup_Intermedio.json",
            "hardest": "/app/PuzzlesMockup_Dificiles.json"
        }
        
        total_loaded = 0
        results = {}
        
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
                
                category_count = 0
                
                for i, item in enumerate(puzzle_data):
                    try:
                        game_data = item.get("game", {})
                        puzzle_info = item.get("puzzle", {})
                        
                        # Extraer FEN desde PGN
                        pgn_string = game_data.get("pgn", "")
                        initial_ply = puzzle_info.get("initialPly", 0)
                        
                        # Obtener la posición correcta donde el usuario debe jugar
                        puzzle_id = puzzle_info.get("id", f"{category}_{i}")
                        solution = puzzle_info.get("solution", [])
                        fen, adjusted_solution = get_puzzle_position_for_user(pgn_string, initial_ply, solution, puzzle_id)
                        
                        # Formatear el puzzle para la base de datos
                        db_puzzle = {
                            "puzzle_id": puzzle_id,
                            "fen": fen,
                            "moves": " ".join(adjusted_solution),
                            "rating": puzzle_info.get("rating", 1500),
                            "themes": ",".join(puzzle_info.get("themes", [])),
                            "game_url": f"https://lichess.org/{game_data.get('id', '')}",
                            "category": category,
                            "description": get_description_from_themes(puzzle_info.get("themes", [])),
                            "turn": fen.split()[1] if fen else "w"
                        }
                        
                        await puzzle_collection.insert_one(db_puzzle)
                        total_loaded += 1
                        category_count += 1
                        logger.info(f"Puzzle {puzzle_id} cargado en categoría {category}")
                        
                    except Exception as e:
                        logger.error(f"Error procesando puzzle {i} de {category}: {e}")
                        continue
                
                results[category] = category_count
                        
            except Exception as e:
                logger.error(f"Error cargando archivo {file_path}: {e}")
                results[category] = 0
                continue
        
        logger.info(f"Carga completada. Total de puzzles cargados: {total_loaded}")
        
        # Verificar estadísticas finales
        for category in json_files.keys():
            count = await puzzle_collection.count_documents({"category": category})
            results[f"{category}_final"] = count
        
        return {
            "success": True,
            "message": f"Puzzles cargados exitosamente. Total: {total_loaded}",
            "total_loaded": total_loaded,
            "details": results
        }
            
    except Exception as e:
        logger.error(f"Error en la carga de puzzles: {e}")
        raise HTTPException(status_code=500, detail=f"Error cargando puzzles: {str(e)}")

@router.get("/estadisticas")
async def get_puzzle_stats():
    """Obtiene estadísticas de los puzzles cargados en la base de datos"""
    try:
        db = await get_database()
        puzzle_collection = db["puzzles"]
        
        # Contar puzzles por categoría
        categories = ["daily", "easiest", "normal", "hardest"]
        stats = {}
        total = 0
        
        for category in categories:
            count = await puzzle_collection.count_documents({"category": category})
            stats[category] = count
            total += count
        
        # Obtener algunos puzzles de ejemplo
        sample_puzzles = []
        for category in categories:
            sample = await puzzle_collection.find_one({"category": category})
            if sample:
                sample_puzzles.append({
                    "category": category,
                    "puzzle_id": sample.get("puzzle_id"),
                    "rating": sample.get("rating"),
                    "description": sample.get("description"),
                    "turn": sample.get("turn")
                })
        
        return {
            "total_puzzles": total,
            "by_category": stats,
            "sample_puzzles": sample_puzzles,
            "last_updated": "Recién cargado" if total > 0 else "No hay puzzles cargados"
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")

@router.post("/resolver-puzzle")
async def resolver_puzzle(puzzle_data: dict):
    """Registra cuando un usuario resuelve un puzzle"""
    try:
        from datetime import datetime
        from dependencies import get_database
        
        db = await get_database()
        
        # Obtener datos del request
        puzzle_id = puzzle_data.get("puzzle_id")
        username = puzzle_data.get("username")
        correcto = puzzle_data.get("correcto", False)
        tiempo = puzzle_data.get("tiempo", 0)
        
        if not puzzle_id or not username:
            return {"error": "puzzle_id y username son requeridos"}
        
        # Buscar usuario
        usuario = await db.users.find_one({"username": username})
        if not usuario:
            return {"error": "Usuario no encontrado"}
        
        # Registrar intento de puzzle
        puzzle_attempt = {
            "puzzle_id": puzzle_id,
            "username": username,
            "correcto": correcto,
            "tiempo": tiempo,
            "fecha": datetime.utcnow()
        }
        
        await db.puzzle_attempts.insert_one(puzzle_attempt)
        
        # Actualizar estadísticas del usuario
        if correcto:
            await db.users.update_one(
                {"username": username},
                {"$inc": {"puzzles_resueltos_correctamente": 1}}
            )
        else:
            await db.users.update_one(
                {"username": username},
                {"$inc": {"puzzles_resueltos_incorrectamente": 1}}
            )
        
        return {
            "success": True,
            "message": f"Puzzle {'resuelto correctamente' if correcto else 'resuelto incorrectamente'}",
            "tiempo": tiempo
        }
        
    except Exception as e:
        logger.error(f"Error registrando resolución de puzzle: {e}")
        return {"error": "Error interno del servidor"}
