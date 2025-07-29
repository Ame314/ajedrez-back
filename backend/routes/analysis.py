from fastapi import APIRouter, HTTPException, Request
from bson import ObjectId
from utils.stockfish_analysis import analizar_movimientos
from stockfish import Stockfish

stockfish = Stockfish(path="/usr/local/bin/stockfish", depth=15)

router = APIRouter()

@router.get("/analisis/{partida_id}")
async def analizar_partida(partida_id: str, request: Request):
    db = request.app.state.db

    partida = None
    try:
        oid = ObjectId(partida_id)
        partida = await db.games.find_one({"_id": oid})
    except Exception as e:
        print(f"Error al crear ObjectId: {e}")

    if not partida:
        # Intentar buscar con string por si acaso
        partida = await db.games.find_one({"_id": partida_id})

    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")

    movimientos_raw = partida.get("moves") or partida.get("movimientos")
    if not movimientos_raw:
        raise HTTPException(status_code=400, detail="La partida no tiene movimientos")

    if isinstance(movimientos_raw, list) and len(movimientos_raw) == 1 and isinstance(movimientos_raw[0], str):
        movimientos = movimientos_raw[0].replace(" ", "").split(",")
    else:
        movimientos = [m.strip("'\"") for m in movimientos_raw]

    analisis = analizar_movimientos(movimientos)
    return {"analisis": analisis}
