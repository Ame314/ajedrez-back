## /backend/routes/users.py
from fastapi import APIRouter, Request, HTTPException
from models.user import User
from models.login import LoginRequest
from utils.auth import hash_password, verify_password, create_access_token
from datetime import timedelta

router = APIRouter()

@router.post("/registrar")
async def create_user(user: User, request: Request):
    db = request.app.state.db

    # Validaciones previas
    if await db.users.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Correo ya registrado")
    if await db.users.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Nombre de usuario en uso")

    # Hashear contraseña
    user_dict = user.dict()
    user_dict["password"] = hash_password(user.password)

    result = await db.users.insert_one(user_dict)
    return {"mensaje": "Usuario registrado", "id": str(result.inserted_id)}

@router.post("/login")
async def login_user(login: LoginRequest, request: Request):
    db = request.app.state.db
    user = await db.users.find_one({"email": login.email})

    if not user or not verify_password(login.password, user["password"]):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    token = create_access_token({
        "username": user["username"],
        "email": user["email"],
        "role": user.get("role", "user")
    })

    return {
        "mensaje": "Login exitoso",
        "access_token": token,
        "token_type": "bearer"
    }

@router.get("/perfil/{username}")
async def perfil_usuario(username: str, request: Request):
    db = request.app.state.db

    usuario = await db.users.find_one({"username": username})
    if not usuario:
        return {"error": "Usuario no encontrado"}

    partidas = await db.games.find({
        "$or": [
            {"white_player": username},
            {"black_player": username}
        ]
    }).to_list(None)

    total_partidas = len(partidas)
    victorias = sum(1 for p in partidas if p.get("winner") == username)
    derrotas = sum(1 for p in partidas if p.get("winner") and p.get("winner") != username and p.get("winner") != "draw")
    tablas = sum(1 for p in partidas if p.get("winner") == "draw")

    return {
        "username": username,
        "elo": usuario.get("elo"),
        "total_partidas": total_partidas,
        "victorias": victorias,
        "derrotas": derrotas,
        "tablas": tablas,
        "historial": [{ "id": str(p["_id"]), "vs": p["black_player"] if p["white_player"] == username else p["white_player"], "resultado": p["result"] } for p in partidas]
    }
