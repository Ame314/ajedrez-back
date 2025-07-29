import chess
from stockfish import Stockfish

# Ruta al ejecutable de Stockfish dentro del contenedor Docker
stockfish = Stockfish(path="/usr/local/bin/stockfish", depth=15)

# Función para convertir jugadas de notación algebraica (SAN) a notación UCI
def convertir_a_uci(movimientos: list[str]) -> list[str]:
    tablero = chess.Board()
    jugadas_uci = []

    for mov in movimientos:
        try:
            jugada = tablero.parse_san(mov.strip())  # "e4" → objeto jugada
            jugadas_uci.append(jugada.uci())         # objeto jugada → "e2e4"
            tablero.push(jugada)
        except Exception as e:
            print(f"Jugada inválida: {mov} - {e}")
            break

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
    movimientos_uci = convertir_a_uci(movimientos)

    if not movimientos_uci:
        return [{"error": "No se pudieron convertir las jugadas"}]

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
