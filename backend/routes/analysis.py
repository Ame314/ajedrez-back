from fastapi import APIRouter, HTTPException, Request, Body
from pydantic import BaseModel
from typing import Optional
from bson import ObjectId
from utils.stockfish_analysis import analizar_movimientos, convertir_a_uci, get_stockfish

router = APIRouter()

# Modelo para el request de Stockfish
class StockfishRequest(BaseModel):
    movimientos: list[str]
    dificultad: Optional[str] = "intermedio"

# Configuraciones de dificultad
DIFFICULTY_SETTINGS = {
    "principiante": {
        "depth": 1,
        "elo": 800,
        "descripcion": "Nivel principiante (~800 ELO) - Ideal para jugadores que están aprendiendo",
        "tiempo": 0.1
    },
    "intermedio": {
        "depth": 8,
        "elo": 1500,
        "descripcion": "Nivel intermedio (~1500 ELO) - Para jugadores con conocimientos básicos",
        "tiempo": 0.5
    },
    "experto": {
        "depth": 15,
        "elo": 2200,
        "descripcion": "Nivel experto (~2200 ELO) - Para jugadores avanzados",
        "tiempo": 1.0
    },
    "gran_maestro": {
        "depth": 20,
        "elo": 2800,
        "descripcion": "Nivel gran maestro (~2800 ELO) - Máximo desafío",
        "tiempo": 2.0
    }
}


@router.get("/game/{game_id}/move/{move_index}")
async def analyze_game_move(game_id: str, move_index: int, request: Request):
    """Analizar un movimiento específico de una partida guardada"""
    # Verificar que Stockfish esté disponible
    stockfish = get_stockfish()
    if stockfish is None:
        raise HTTPException(status_code=503, detail="Motor de análisis no disponible. Stockfish no está instalado.")
    
    db = request.app.state.db

    # Buscar la partida
    partida = None
    try:
        oid = ObjectId(game_id)
        partida = await db.games.find_one({"_id": oid})
    except Exception as e:
        print(f"Error al crear ObjectId: {e}")

    if not partida:
        # Intentar buscar con string por si acaso
        partida = await db.games.find_one({"_id": game_id})

    if not partida:
        raise HTTPException(status_code=404, detail="Partida no encontrada")

    movimientos_raw = partida.get("moves") or partida.get("movimientos")
    if not movimientos_raw:
        raise HTTPException(status_code=400, detail="La partida no tiene movimientos")

    # Parsear movimientos
    if isinstance(movimientos_raw, str):
        movimientos = movimientos_raw.strip().split(' ')
    elif isinstance(movimientos_raw, list):
        if len(movimientos_raw) == 1 and isinstance(movimientos_raw[0], str):
            movimientos = movimientos_raw[0].strip().split(' ')
        else:
            movimientos = [str(m).strip("'\"") for m in movimientos_raw]
    else:
        raise HTTPException(status_code=400, detail="Formato de movimientos no válido")

    # Filtrar movimientos vacíos
    movimientos = [m for m in movimientos if m.strip()]

    if move_index < 0 or move_index > len(movimientos):
        raise HTTPException(status_code=400, detail="Índice de movimiento fuera de rango")

    try:
        # Convertir los movimientos hasta el índice especificado a UCI
        movimientos_hasta_indice = movimientos[:move_index]
        movimientos_uci = convertir_a_uci(movimientos_hasta_indice)
        
        # Configurar posición en Stockfish
        stockfish.set_position(movimientos_uci)
        stockfish.set_depth(15)  # Profundidad para análisis detallado
        
        # Obtener evaluación de la posición
        evaluation = stockfish.get_evaluation()
        
        # Obtener el mejor movimiento
        best_move = stockfish.get_best_move()
        
        # Obtener línea principal (hasta 10 movimientos)
        principal_variation = []
        if best_move:
            try:
                # Hacer una copia temporal para obtener la línea principal
                temp_moves = movimientos_uci + [best_move]
                stockfish.set_position(temp_moves)
                
                # Obtener algunos movimientos de la línea principal
                for _ in range(5):  # Hasta 5 movimientos más
                    next_move = stockfish.get_best_move()
                    if next_move:
                        principal_variation.append(next_move)
                        temp_moves.append(next_move)
                        stockfish.set_position(temp_moves)
                    else:
                        break
                        
                # Restaurar posición original
                stockfish.set_position(movimientos_uci)
            except:
                pass
        
        # Obtener las mejores jugadas alternativas
        top_moves = stockfish.get_top_moves(3)
        
        return {
            "move_index": move_index,
            "position_fen": stockfish.get_fen_position(),
            "evaluation": evaluation,
            "best_move": best_move,
            "pv": principal_variation,
            "top_moves": top_moves,
            "depth": 15,
            "analysis_complete": True
        }
        
    except Exception as e:
        print(f"Error analizando movimiento: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al analizar el movimiento: {str(e)}")


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
def jugar_con_stockfish(request: StockfishRequest):
    # Obtener instancia de Stockfish
    stockfish = get_stockfish()
    
    # Verificar que Stockfish esté disponible
    if stockfish is None:
        raise HTTPException(status_code=500, detail="Motor de análisis no disponible")
    
    movimientos = request.movimientos
    dificultad = request.dificultad
    
    print(f"Movimientos recibidos: {movimientos}")
    print(f"Dificultad seleccionada: {dificultad}")
    
    # Validar entrada
    if not isinstance(movimientos, list):
        raise HTTPException(status_code=400, detail="Se esperaba una lista de movimientos")
    
    # Validar dificultad
    if dificultad not in DIFFICULTY_SETTINGS:
        raise HTTPException(status_code=400, detail=f"Dificultad '{dificultad}' no válida. Opciones: {list(DIFFICULTY_SETTINGS.keys())}")
    
    # Configurar dificultad
    difficulty_config = DIFFICULTY_SETTINGS[dificultad]
    stockfish.set_depth(difficulty_config["depth"])
    
    print(f"Configurando Stockfish - Profundidad: {difficulty_config['depth']}, ELO aproximado: {difficulty_config['elo']}")
    
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
                "movimientos_totales": movimientos,
                "dificultad": dificultad,
                "elo_aproximado": difficulty_config["elo"]
            }

        # Aplicar el movimiento de Stockfish para obtener la nueva posición
        nuevos_movimientos_uci = movimientos_uci + [jugada_stockfish]
        stockfish.set_position(nuevos_movimientos_uci)
        nuevo_fen = stockfish.get_fen_position()

        return {
            "jugada_stockfish": jugada_stockfish,
            "fen": nuevo_fen,
            "movimientos_totales": movimientos + [jugada_stockfish],
            "comentario": f"Stockfish ({difficulty_config['elo']} ELO) juega {jugada_stockfish}",
            "dificultad": dificultad,
            "elo_aproximado": difficulty_config["elo"]
        }
    
    except Exception as e:
        print(f"Error en jugar_con_stockfish: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al procesar con Stockfish: {str(e)}")


@router.get("/stockfish-dificultades")
def obtener_dificultades():
    """Endpoint para obtener información sobre los niveles de dificultad disponibles"""
    return {
        "dificultades": DIFFICULTY_SETTINGS,
        "descripcion": "Niveles de dificultad disponibles para Stockfish",
        "niveles_disponibles": list(DIFFICULTY_SETTINGS.keys())
    }


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
