## /backend/routes/users.py
from fastapi import APIRouter, Request, HTTPException
from models.user import User, PasswordResetRequest, PasswordResetConfirm
from models.login import LoginRequest
from utils.auth import hash_password, verify_password, create_access_token
from utils.smtp import generate_reset_token, send_reset_email, create_reset_record, verify_reset_token, mark_token_as_used
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
        "rol": usuario.get("role"),
        "elo": usuario.get("elo"),

        "partidas": {
            "total": total_partidas,
            "victorias": victorias,
            "derrotas": derrotas,
            "tablas": tablas,
            "historial": [{
                "id": str(p["_id"]),
                "vs": p["black_player"] if p["white_player"] == username else p["white_player"],
                "resultado": p.get("result", "desconocido")
            } for p in partidas]
        },

        "puzzles": {
            "resueltos_correctamente": usuario.get("puzzles_resueltos_correctamente", 0),
            "resueltos_incorrectamente": usuario.get("puzzles_resueltos_incorrectamente", 0),
            "historial": usuario.get("historial_puzzles", [])
        },

        "lecciones_vistas": usuario.get("lecciones_vistas", [])
    }

@router.post("/solicitar-restauracion")
async def request_password_reset(reset_request: PasswordResetRequest, request: Request):
    """
    Solicita la restauración de contraseña enviando un email
    """
    db = request.app.state.db
    
    # Buscar usuario por email
    user = await db.users.find_one({"email": reset_request.email})
    if not user:
        # Por seguridad, no revelamos si el email existe o no
        return {"mensaje": "Si el email está registrado, recibirás un enlace de restauración"}
    
    # Generar token de restauración
    token = generate_reset_token()
    
    # Crear registro en la base de datos
    success = await create_reset_record(db, reset_request.email, token)
    if not success:
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    
    # Enviar email
    email_sent = send_reset_email(reset_request.email, token, user["username"])
    if not email_sent:
        raise HTTPException(status_code=500, detail="Error enviando email")
    
    return {"mensaje": "Si el email está registrado, recibirás un enlace de restauración"}

@router.post("/restaurar-contrasena")
async def reset_password(reset_confirm: PasswordResetConfirm, request: Request):
    """
    Restaura la contraseña usando el token recibido por email
    """
    db = request.app.state.db
    
    # Verificar token
    email = await verify_reset_token(db, reset_confirm.token)
    if not email:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")
    
    # Buscar usuario
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Hashear nueva contraseña
    hashed_password = hash_password(reset_confirm.new_password)
    
    # Actualizar contraseña
    result = await db.users.update_one(
        {"email": email},
        {"$set": {"password": hashed_password}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=500, detail="Error actualizando contraseña")
    
    # Marcar token como usado
    await mark_token_as_used(db, reset_confirm.token)
    
    return {"mensaje": "Contraseña actualizada correctamente"}
