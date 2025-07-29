from fastapi import APIRouter, HTTPException, Request, Body
from bson import ObjectId
from utils.stockfish_analysis import analizar_movimientos, convertir_a_uci
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


@router.post("/juga-stockfish")
def jugar_con_stockfish(movimientos: list[str] = Body(...)):
    movimientos_uci = convertir_a_uci(movimientos)

    if not movimientos_uci:
        raise HTTPException(status_code=400, detail="Movimientos inválidos")

    stockfish.set_position(movimientos_uci)

    jugada_stockfish = stockfish.get_best_move()

    if not jugada_stockfish:
        return {"mensaje": "La partida ha terminado o no se puede continuar"}

    movimientos_uci.append(jugada_stockfish)
    stockfish.set_position(movimientos_uci)

    return {
        "jugada_stockfish": jugada_stockfish,
        "fen": stockfish.get_fen_position(),
        "movimientos_totales": movimientos + [jugada_stockfish],
        "comentario": f"Stockfish juega {jugada_stockfish}"
    }


@router.post("/analizar-tablero")
def sugerencias_de_jugada(movimientos: list[str] = Body(...)):
    movimientos_uci = convertir_a_uci(movimientos)

    if not movimientos_uci and movimientos:
        raise HTTPException(status_code=400, detail="Movimientos inválidos")

    stockfish.set_position(movimientos_uci)

    # Determinar el turno actual en base al número de movimientos
    turno = "blancas" if len(movimientos_uci) % 2 == 0 else "negras"

    mejores_jugadas = stockfish.get_top_moves(3)

    return {
        "turno_actual": turno,
        "mejores_jugadas": mejores_jugadas,
        "fen": stockfish.get_fen_position(),
        "comentario": f"Las mejores jugadas para las {turno} son: " +
                      ", ".join([f"{m['Move']} (eval: {m['Centipawn']})" for m in mejores_jugadas])
    }
