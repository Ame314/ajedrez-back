from pymongo import MongoClient

client = MongoClient("mongodb://mongodb:27017/")
db = client.ajedrez_db

partidas = db.games.find({})

for partida in partidas:
    # Obtener movimientos en lista y limpiarlos
    moves = partida.get("moves") or partida.get("movimientos") or []
    if isinstance(moves, list) and moves:
        # Si los movimientos están en una sola cadena separada por comas
        if len(moves) == 1 and isinstance(moves[0], str) and ("," in moves[0] or " " in moves[0]):
            # separa por comas o espacios
            if "," in moves[0]:
                moves = [m.strip() for m in moves[0].split(",")]
            else:
                moves = moves[0].split()
    else:
        moves = []

    # Normalizar resultado
    result = partida.get("result") or partida.get("resultado") or ""
    result = result.lower().strip()

    # Determinar jugadores
    user = partida.get("user") or partida.get("username") or ""
    opponent = partida.get("opponent") or ""

    # Definir ganador y resultado en notación ajedrecística
    if result in ["victoria", "win"]:
        winner = user
        loser = opponent
        result_code = "1-0"  # usuario blancas gana
        white_player = user
        black_player = opponent
    elif result in ["derrota", "lose", "loss"]:
        winner = opponent
        loser = user
        result_code = "0-1"  # negras ganan
        white_player = user
        black_player = opponent
    elif result in ["draw", "tablas", "empate"]:
        winner = "draw"
        result_code = "1/2-1/2"
        white_player = user
        black_player = opponent
    else:
        # Si no reconoce el resultado, lo ignora para no dañar datos
        print(f"Resultado desconocido para partida {_id}, saltando...")
        continue

    # Asignar elo base (puedes adaptar para sacar elo real luego)
    white_elo = 1200
    black_elo = 1200

    # Crear el documento actualizado
    partida_actualizada = {
        "white_player": white_player,
        "black_player": black_player,
        "white_elo": white_elo,
        "black_elo": black_elo,
        "moves": moves,
        "result": result_code,
        "winner": winner,
        "date_played": partida.get("date_played")
    }

    # Actualizar el documento en MongoDB
    db.games.update_one({"_id": partida["_id"]}, {"$set": partida_actualizada})

print("Actualización completada.")
