from fastapi import APIRouter, Request
from models.game import Game
from datetime import datetime

router = APIRouter()

@router.post("/guardar-partida")
async def save_game(game: Game, request: Request):
    db = request.app.state.db
    game.date_played = datetime.utcnow()

    partida_dict = game.dict()
    partida_dict["jugadores"] = [game.user, game.opponent]

    result = await db.games.insert_one(partida_dict)
    return {"mensaje": "Partida guardada", "id": str(result.inserted_id)}


@router.get("/partidas/{username}")
async def obtener_partidas(request: Request, username: str):
    db = request.app.state.db
    partidas = await db.games.find({"jugadores": username}).to_list(None)
    return [{**p, "_id": str(p["_id"])} for p in partidas]
