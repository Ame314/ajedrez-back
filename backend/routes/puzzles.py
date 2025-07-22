from fastapi import APIRouter, Request, HTTPException
from bson import ObjectId

router = APIRouter()


def clean_document(doc):
    doc['_id'] = str(doc['_id'])
    return doc



@router.get("/puzzles")
async def get_puzzles(request: Request):
    db = request.app.state.db
    puzzles_cursor = db.puzzles.find().limit(50)
    puzzles = await puzzles_cursor.to_list(length=50)
    return [clean_document(p) for p in puzzles]


@router.get("/puzzle/asignar/{username}")
async def asignar_un_puzzle(username: str, request: Request):
    db = request.app.state.db
    user = await db.users.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    elo = user.get("elo", 800)

    if elo < 800:
        dificultad = "easy"
    elif elo <= 1400:
        dificultad = "medium"
    else:
        dificultad = "hard"

    # Buscar un puzzle aleatorio
    puzzle_cursor = db.puzzles.aggregate([
        {"$match": {"difficulty": dificultad}},
        {"$sample": {"size": 1}}
    ])
    puzzle_list = await puzzle_cursor.to_list(length=1)

    if not puzzle_list:
        raise HTTPException(status_code=404, detail="No hay puzzles disponibles")

    puzzle = puzzle_list[0]

    return {
        "puzzle_id": str(puzzle["_id"]),
        "fen": puzzle["FEN"],
        "rating": puzzle["Rating"],
        "dificultad": dificultad,
        "game_url": puzzle["GameUrl"]
    }



@router.post("/puzzle/resuelto")
async def puzzle_resuelto(request: Request, data: dict):
    db = request.app.state.db
    username = data.get("username")
    puzzle_id = data.get("puzzle_id")

    if not username or not puzzle_id:
        raise HTTPException(status_code=400, detail="Faltan datos")

    user = await db.users.find_one({"username": username})
    puzzle = await db.puzzles.find_one({"_id": ObjectId(puzzle_id)})

    if not user or not puzzle:
        raise HTTPException(status_code=404, detail="Usuario o puzzle no encontrado")

    dificultad = puzzle.get("difficulty", "medium")

    if dificultad == "easy":
        ganancia = 5
    elif dificultad == "medium":
        ganancia = 10
    else:
        ganancia = 20

    await db.users.update_one(
        {"username": username},
        {"$inc": {"elo": ganancia}}
    )

    await db.users.update_one(
        {"username": username},
        {"$push": {
            "historial_puzzles": {
                "puzzle_id": str(puzzle["_id"]),
                "dificultad": dificultad
            }
        }}
    )

    return {
        "mensaje": f"¡Puzzle resuelto! Ganaste +{ganancia} ELO.",
        "elo_anterior": user.get("elo", 800),
        "elo_actual": user.get("elo", 800) + ganancia
    }
