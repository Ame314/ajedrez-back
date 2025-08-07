import chess
from stockfish import Stockfish
import os

# Variable global para la instancia de Stockfish
_stockfish_instance = None

# Función para inicializar Stockfish de forma segura
def init_stockfish():
    # Función para probar si Stockfish funciona en una ruta
    def test_stockfish_path(path):
        try:
            # Crear instancia temporal para probar
            temp_stockfish = Stockfish(path=path, depth=15)
            # Verificar que funcione haciendo una llamada simple
            temp_stockfish.get_fen_position()
            return True
        except Exception:
            return False
    
    # Lista de posibles rutas donde puede estar Stockfish
    possible_paths = [
        "/usr/games/stockfish",         # Instalación apt en contenedor Docker
        "/usr/local/bin/stockfish",     # Instalación manual/compilada
        "/opt/homebrew/bin/stockfish",  # macOS con Homebrew (Apple Silicon)
        "/usr/bin/stockfish",           # Linux estándar
        "stockfish"                     # PATH del sistema
    ]
    
    # Intentar con cada ruta
    for path in possible_paths:
        if test_stockfish_path(path):
            try:
                stockfish = Stockfish(path=path, depth=15)
                print(f"Stockfish inicializado correctamente en: {path}")
                return stockfish
            except Exception as e:
                print(f"Error al inicializar Stockfish en {path}: {e}")
                continue
        else:
            print(f"Stockfish no funciona en: {path}")
    
    print("No se pudo inicializar Stockfish en ninguna ubicación")
    return None

# Función para obtener la instancia de Stockfish (lazy loading)
def get_stockfish():
    global _stockfish_instance
    if _stockfish_instance is None:
        _stockfish_instance = init_stockfish()
    return _stockfish_instance

# Función para convertir jugadas de notación algebraica (SAN) a notación UCI
def convertir_a_uci(movimientos: list[str]) -> list[str]:
    tablero = chess.Board()
    jugadas_uci = []

    print(f"Convirtiendo movimientos SAN a UCI: {movimientos}")

    for i, mov in enumerate(movimientos):
        try:
            mov_limpio = mov.strip()
            print(f"Procesando movimiento {i+1}: '{mov_limpio}' en posición FEN: {tablero.fen()}")
            
            jugada = tablero.parse_san(mov_limpio)  # "e4" → objeto jugada
            uci_move = jugada.uci()                 # objeto jugada → "e2e4"
            jugadas_uci.append(uci_move)
            tablero.push(jugada)
            
            print(f"Movimiento {i+1} convertido: '{mov_limpio}' → '{uci_move}'")
            
        except Exception as e:
            print(f"Error al procesar movimiento {i+1} '{mov}': {e}")
            print(f"FEN en el momento del error: {tablero.fen()}")
            print(f"Movimientos válidos disponibles: {list(tablero.legal_moves)}")
            break

    print(f"Conversión completada. Movimientos UCI: {jugadas_uci}")
    return jugadas_uci

# Función para generar comentarios automáticos
def generar_comentario(eval_antes, eval_despues, best_move, move):
    cp_antes = eval_antes.get("value", 0)
    cp_despues = eval_despues.get("value", 0)

    diff = cp_despues - cp_antes

    if move == best_move:
        return "¡Excelente jugada!"
    elif diff > 50:
        return "Buena jugada"
    elif diff < -300:
        return "Error grave"
    elif diff < -100:
        return "Jugada dudosa"
    else:
        return "Podría ser mejor"

# Función principal de análisis
def analizar_movimientos(movimientos: list[str]):
    # Obtener instancia de Stockfish
    stockfish = get_stockfish()
    
    # Verificar que Stockfish esté disponible
    if stockfish is None:
        return [{"error": "Motor de análisis no disponible. Stockfish no está instalado."}]
    
    movimientos_uci = convertir_a_uci(movimientos)

    if not movimientos_uci:
        return [{"error": "No se pudieron convertir las jugadas"}]

    try:
        stockfish.set_position([])  # resetea el tablero
        analisis = []

        for i, move in enumerate(movimientos_uci):
            eval_antes = stockfish.get_evaluation()
            best_move = stockfish.get_best_move()

            stockfish.make_moves_from_current_position([move])
            eval_despues = stockfish.get_evaluation()

            comentario = generar_comentario(eval_antes, eval_despues, best_move, move)

            analisis.append({
                "jugada_num": i + 1,
                "jugada_real": movimientos[i],      # como se ingresó originalmente
                "jugada_uci": move,                 # como se interpreta
                "mejor_jugada": best_move,
                "evaluacion_antes": eval_antes,
                "evaluacion_despues": eval_despues,
                "comentario": comentario
            })

        return analisis
    
    except Exception as e:
        return [{"error": f"Error durante el análisis: {str(e)}"}]
