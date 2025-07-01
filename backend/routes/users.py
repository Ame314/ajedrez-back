from fastapi import APIRouter, Request
from models.user import User
from models.login import LoginRequest

router = APIRouter()

@router.post("/registrar")
async def create_user(user: User, request: Request):
    db = request.app.state.db

    # Verifica si ya existe el email
    existing_email = await db.users.find_one({"email": user.email})
    if existing_email:
        return {"mensaje": "Ya existe un usuario con este correo electrónico"}

    # Verifica si ya existe el username
    existing_username = await db.users.find_one({"username": user.username})
    if existing_username:
        return {"mensaje": "Nombre de usuario ya está en uso"}

    # Insertar nuevo usuario
    result = await db.users.insert_one(user.dict())
    return {
        "mensaje": "Usuario registrado correctamente",
        "id": str(result.inserted_id)
    }

@router.post("/login")
async def login_user(login: LoginRequest, request: Request):
    db = request.app.state.db
    user = await db.users.find_one({"email": login.email})

    if not user:
        return {"mensaje": "Usuario no encontrado"}

    if user["password"] != login.password:
        return {"mensaje": "Contraseña incorrecta"}

    return {
        "mensaje": "Login exitoso",
        "user_id": str(user["_id"]),
        "username": user["username"]
    }
