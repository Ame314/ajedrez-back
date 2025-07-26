from fastapi import APIRouter, Request
from models.game import Game
from models.live_game import LiveGame, Move
from datetime import datetime
from utils.websocket_manager import manager

router = APIRouter()

def calcular_nuevo_elo(rating_a, rating_b, resultado):
    # resultado: 1.0 si gana A, 0.5 tablas, 0.0 derrota
    K = 32
    expected_score = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    return int(rating_a + K * (resultado - expected_score))

@router.post("/guardar-partida")
async def save_game(game: Game, request: Request):
    db = request.app.state.db
    game.date_played = datetime.utcnow()

    # Buscar usuarios
    white = await db.users.find_one({"username": game.white_player})
    black = await db.users.find_one({"username": game.black_player})

    if not white or not black:
        return {"error": "Uno o ambos jugadores no existen"}

    # Calcular resultado numérico para blancos
    resultado_blancos = {"1-0": 1.0, "0-1": 0.0, "1/2": 0.5}[game.result_code]

    # Calcular nuevos ELO
    nuevo_elo_blancos = calcular_nuevo_elo(white["elo"], black["elo"], resultado_blancos)
    nuevo_elo_negras = calcular_nuevo_elo(black["elo"], white["elo"], 1 - resultado_blancos)

    # Guardar partida
    partida_dict = game.dict()
    partida_dict["white_elo"] = white["elo"]
    partida_dict["black_elo"] = black["elo"]
    partida_dict["winner"] = (
        game.white_player if game.result_code == "1-0"
        else game.black_player if game.result_code == "0-1"
        else "draw"
    )

    result = await db.games.insert_one(partida_dict)

    # Actualizar usuarios
    await db.users.update_one(
        {"username": game.white_player},
        {"$set": {"elo": nuevo_elo_blancos},
         "$inc": {
             "games_played": 1,
             "games_won": 1 if game.result_code == "1-0" else 0,
             "games_lost": 1 if game.result_code == "0-1" else 0,
             "games_drawn": 1 if game.result_code == "1/2" else 0
         }}
    )

    await db.users.update_one(
        {"username": game.black_player},
        {"$set": {"elo": nuevo_elo_negras},
         "$inc": {
             "games_played": 1,
             "games_won": 1 if game.result_code == "0-1" else 0,
             "games_lost": 1 if game.result_code == "1-0" else 0,
             "games_drawn": 1 if game.result_code == "1/2" else 0
         }}
    )

    return {
        "mensaje": "Partida guardada",
        "id": str(result.inserted_id),
        "nuevo_elo_blancos": nuevo_elo_blancos,
        "nuevo_elo_negras": nuevo_elo_negras
    }


@router.get("/partidas/{username}")
async def obtener_partidas(request: Request, username: str):
    db = request.app.state.db
    partidas = await db.games.find({
        "$or": [{"white_player": username}, {"black_player": username}]
    }).to_list(None)
    return [{**p, "_id": str(p["_id"])} for p in partidas]

@router.post("/finalizar-partida-vivo")
async def finalizar_partida_vivo(request: Request, game_id: str):
    """Finaliza una partida en vivo y la guarda en la base de datos"""
    db = request.app.state.db
    
    if game_id not in manager.active_games:
        return {"error": "Partida no encontrada"}
    
    live_game = manager.active_games[game_id]
    
    # Crear objeto Game para guardar
    game_data = {
        "white_player": live_game["white_player"],
        "black_player": live_game["black_player"],
        "white_elo": live_game["white_elo"],
        "black_elo": live_game["black_elo"],
        "moves": [move["san"] for move in live_game["moves"]],  # Solo notación SAN
        "result_code": live_game["result"],
        "winner": live_game["winner"] or "draw",
        "date_played": live_game["created_at"]
    }
    
    # Calcular resultado numérico para blancos
    resultado_blancos = {"1-0": 1.0, "0-1": 0.0, "1/2-1/2": 0.5}.get(live_game["result"], 0.5)
    
    # Calcular nuevos ELO
    white_elo = live_game["white_elo"]
    black_elo = live_game["black_elo"]
    
    nuevo_elo_blancos = calcular_nuevo_elo(white_elo, black_elo, resultado_blancos)
    nuevo_elo_negras = calcular_nuevo_elo(black_elo, white_elo, 1 - resultado_blancos)
    
    # Guardar partida en la base de datos
    result = await db.games.insert_one(game_data)
    
    # Actualizar estadísticas de usuarios
    white_player = live_game["white_player"]
    black_player = live_game["black_player"]
    
    await db.users.update_one(
        {"username": white_player},
        {"$set": {"elo": nuevo_elo_blancos},
         "$inc": {
             "games_played": 1,
             "games_won": 1 if live_game["result"] == "1-0" else 0,
             "games_lost": 1 if live_game["result"] == "0-1" else 0,
             "games_drawn": 1 if live_game["result"] == "1/2-1/2" else 0
         }}
    )

    await db.users.update_one(
        {"username": black_player},
        {"$set": {"elo": nuevo_elo_negras},
         "$inc": {
             "games_played": 1,
             "games_won": 1 if live_game["result"] == "0-1" else 0,
             "games_lost": 1 if live_game["result"] == "1-0" else 0,
             "games_drawn": 1 if live_game["result"] == "1/2-1/2" else 0
         }}
    )
    
    # Remover partida de partidas activas
    del manager.active_games[game_id]
    if white_player in manager.user_to_game:
        del manager.user_to_game[white_player]
    if black_player in manager.user_to_game:
        del manager.user_to_game[black_player]
    
    return {
        "mensaje": "Partida finalizada y guardada",
        "id": str(result.inserted_id),
        "nuevo_elo_blancos": nuevo_elo_blancos,
        "nuevo_elo_negras": nuevo_elo_negras
    }
