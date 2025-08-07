from fastapi import APIRouter, HTTPException, Request, Body
from bson import ObjectId
from utils.stockfish_analysis import analizar_movimientos, convertir_a_uci, get_stockfish

router = APIRouter()


@router.get("/analisis/{partida_id}")
async def analizar_partida(partida_id: str, request: Request):
    # Verificar que Stockfish esté disponible
    if stockfish is None:
        raise HTTPException(status_code=503, detail="Motor de análisis no disponible. Stockfish no está instalado.")
    
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
    # Obtener instancia de Stockfish
    stockfish = get_stockfish()
    
    # Verificar que Stockfish esté disponible
    if stockfish is None:
        raise HTTPException(status_code=500, detail="Motor de análisis no disponible")
    
    print(f"Movimientos recibidos: {movimientos}")
    
    # Validar entrada
    if not isinstance(movimientos, list):
        raise HTTPException(status_code=400, detail="Se esperaba una lista de movimientos")
    
    # Convertir movimientos a UCI
    movimientos_uci = convertir_a_uci(movimientos)
    print(f"Movimientos UCI: {movimientos_uci}")

    # Verificar que la conversión fue exitosa
    if len(movimientos) > 0 and len(movimientos_uci) == 0:
        raise HTTPException(status_code=400, detail="No se pudieron convertir los movimientos a UCI")
    
    # Si hay movimientos pero la conversión falló parcialmente
    if len(movimientos) > 0 and len(movimientos_uci) != len(movimientos):
        print(f"Advertencia: Se esperaban {len(movimientos)} movimientos UCI, pero se obtuvieron {len(movimientos_uci)}")

    try:
        # Configurar posición en Stockfish
        stockfish.set_position(movimientos_uci)
        
        # Verificar que la posición es válida
        current_fen = stockfish.get_fen_position()
        if not current_fen:
            raise HTTPException(status_code=400, detail="Posición de ajedrez inválida")
        
        print(f"FEN actual en Stockfish: {current_fen}")

        # Obtener el mejor movimiento
        jugada_stockfish = stockfish.get_best_move()
        print(f"Mejor movimiento de Stockfish: {jugada_stockfish}")

        if not jugada_stockfish:
            return {
                "mensaje": "La partida ha terminado o no se puede continuar",
                "fen": current_fen,
                "movimientos_totales": movimientos
            }

        # Aplicar el movimiento de Stockfish para obtener la nueva posición
        nuevos_movimientos_uci = movimientos_uci + [jugada_stockfish]
        stockfish.set_position(nuevos_movimientos_uci)
        nuevo_fen = stockfish.get_fen_position()

        return {
            "jugada_stockfish": jugada_stockfish,
            "fen": nuevo_fen,
            "movimientos_totales": movimientos + [jugada_stockfish],
            "comentario": f"Stockfish juega {jugada_stockfish}"
        }
    
    except Exception as e:
        print(f"Error en jugar_con_stockfish: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar con Stockfish: {str(e)}")


@router.post("/analizar-tablero")
def sugerencias_de_jugada(movimientos: list[str] = Body(...)):
    # Obtener instancia de Stockfish
    stockfish = get_stockfish()
    
    # Verificar que Stockfish esté disponible
    if stockfish is None:
        raise HTTPException(status_code=500, detail="Motor de análisis no disponible")
    
    movimientos_uci = convertir_a_uci(movimientos)

    if not movimientos_uci and movimientos:
        raise HTTPException(status_code=400, detail="Movimientos inválidos")

    try:
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
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar con Stockfish: {str(e)}")
