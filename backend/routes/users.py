## /backend/routes/users.py
from fastapi import APIRouter, Request, HTTPException, Depends
from models.user import User, PasswordResetRequest, PasswordResetConfirm
from models.login import LoginRequest
from utils.auth import hash_password, verify_password, create_access_token
from utils.smtp import generate_reset_token, send_reset_email, create_reset_record, verify_reset_token, mark_token_as_used
from dependencies import get_current_user
from bson import ObjectId
from datetime import timedelta, datetime

router = APIRouter()

@router.post("/registrar")
async def create_user(user: User, request: Request):
    db = request.app.state.db

    # Validaciones previas
    if await db.users.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Correo ya registrado")
    if await db.users.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="Nombre de usuario en uso")

    # Forzar rol a "user" - solo estudiantes pueden registrarse
    user_dict = user.dict()
    user_dict["role"] = "user"  # Forzamos el rol a usuario siempre
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
        "role": user.get("role", "user"),
        "id": str(user["_id"])
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

@router.get("/estadisticas/{username}")
async def obtener_estadisticas_usuario(username: str, request: Request):
    db = request.app.state.db
    
    # Buscar usuario
    usuario = await db.users.find_one({"username": username})
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Obtener todas las partidas del usuario
    partidas = await db.games.find({
        "$or": [
            {"white_player": username},
            {"black_player": username}
        ]
    }).to_list(None)
    
    # Separar partidas contra IA de partidas contra humanos
    partidas_humanos = [p for p in partidas if not p.get("vs_ai", False)]
    
    # Calcular estadísticas solo de partidas contra humanos
    total_partidas = len(partidas_humanos)
    victorias = sum(1 for p in partidas_humanos if p.get("winner") == username)
    derrotas = sum(1 for p in partidas_humanos if p.get("winner") and p.get("winner") != username and p.get("winner") != "draw")
    tablas = sum(1 for p in partidas_humanos if p.get("winner") == "draw")
    winrate = round((victorias / total_partidas * 100), 1) if total_partidas > 0 else 0
    
    # Calcular tiempo total jugado (estimación basada solo en partidas contra humanos)
    tiempo_estimado_minutos = total_partidas * 15  # Estimamos 15 min por partida
    horas = tiempo_estimado_minutos // 60
    minutos = tiempo_estimado_minutos % 60
    tiempo_total = f"{horas}h {minutos}m"
    
    # Obtener puzzles resueltos
    puzzles_correctos = usuario.get("puzzles_resueltos_correctamente", 0)
    puzzles_incorrectos = usuario.get("puzzles_resueltos_incorrectamente", 0)
    total_puzzles = puzzles_correctos + puzzles_incorrectos
    
    # Obtener ELO actual
    elo_actual = usuario.get("elo", 1200)
    
    # Calcular logros
    logros = []
    
    # Primera partida
    logros.append({
        "name": "Primera Partida",
        "description": "Juega tu primera partida",
        "earned": total_partidas > 0
    })
    
    # Primera victoria
    logros.append({
        "name": "Primera Victoria",
        "description": "Gana tu primera partida",
        "earned": victorias > 0
    })
    
    # Puzzle Master
    logros.append({
        "name": "Aprendiz de Puzzles", 
        "description": "Resuelve 5 puzzles",
        "earned": puzzles_correctos >= 5
    })
    
    # Estratega
    logros.append({
        "name": "Estratega",
        "description": "Gana 5 partidas", 
        "earned": victorias >= 5
    })
    
    # Maestro de Puzzles
    logros.append({
        "name": "Maestro de Puzzles",
        "description": "Resuelve 25 puzzles correctamente",
        "earned": puzzles_correctos >= 25
    })
    
    # Veterano
    logros.append({
        "name": "Veterano",
        "description": "Juega 20 partidas",
        "earned": total_partidas >= 20
    })
    
    # Invencible
    logros.append({
        "name": "Campeón",
        "description": "Gana 10 partidas",
        "earned": victorias >= 10
    })
    
    # Perfeccionista
    logros.append({
        "name": "Perfeccionista",
        "description": "Resuelve 50 puzzles correctamente",
        "earned": puzzles_correctos >= 50
    })
    
    # Persistente
    logros.append({
        "name": "Persistente",
        "description": "Juega 50 partidas",
        "earned": total_partidas >= 50
    })
    
    # Leyenda
    logros.append({
        "name": "Leyenda",
        "description": "Alcanza 1600 ELO",
        "earned": elo_actual >= 1600
    })
    
    # Gran Maestro
    logros.append({
        "name": "Gran Maestro",
        "description": "Alcanza 1800 ELO",
        "earned": elo_actual >= 1800
    })
    
    # Imparable
    logros.append({
        "name": "Imparable",
        "description": "Gana 25 partidas",
        "earned": victorias >= 25
    })
    
    # Obtener partidas contra IA para logros de Stockfish
    partidas_ia = [p for p in partidas if p.get("vs_ai", False)]
    
    # Verificar victorias contra Stockfish por dificultad
    vencio_principiante = any(
        p.get("winner") == username and p.get("ai_difficulty") == "principiante"
        for p in partidas_ia
    )
    vencio_intermedio = any(
        p.get("winner") == username and p.get("ai_difficulty") == "intermedio"
        for p in partidas_ia
    )
    vencio_experto = any(
        p.get("winner") == username and p.get("ai_difficulty") == "experto"
        for p in partidas_ia
    )
    vencio_gran_maestro = any(
        p.get("winner") == username and p.get("ai_difficulty") == "gran_maestro"
        for p in partidas_ia
    )
    
    # Logros de Stockfish
    logros.append({
        "name": "Vencedor Principiante",
        "description": "Vence al bot Stockfish en dificultad principiante",
        "earned": vencio_principiante
    })
    
    logros.append({
        "name": "Vencedor Intermedio",
        "description": "Vence al bot Stockfish en dificultad intermedio",
        "earned": vencio_intermedio
    })
    
    logros.append({
        "name": "Vencedor Experto",
        "description": "Vence al bot Stockfish en dificultad experto",
        "earned": vencio_experto
    })
    
    logros.append({
        "name": "Domador de Máquinas",
        "description": "Vence al bot Stockfish en dificultad gran maestro",
        "earned": vencio_gran_maestro
    })
    
    # Obtener historial reciente de rating (últimas 10 partidas SOLO contra humanos)
    partidas_humanos_recientes = sorted(partidas_humanos, key=lambda x: x.get("date_played", datetime.min) if x.get("date_played") else datetime.min, reverse=True)[:10]
    historial_rating = []
    
    for i, partida in enumerate(reversed(partidas_humanos_recientes)):
        # Simular cambios de ELO basado en resultados (solo partidas contra humanos)
        if partida.get("winner") == username:
            cambio = 25
        elif partida.get("winner") == "draw":
            cambio = 0
        else:
            cambio = -25
            
        elo_en_partida = elo_actual - (cambio * i)
        historial_rating.append({
            "partida": len(partidas_humanos_recientes) - i,
            "elo": max(800, elo_en_partida)  # ELO mínimo de 800
        })
    
    # Obtener partidas recientes (TODAS las partidas, incluyendo IA)
    partidas_recientes = sorted(partidas, key=lambda x: x.get("date_played", datetime.min) if x.get("date_played") else datetime.min, reverse=True)
    
    # Calcular fecha de registro
    fecha_registro = usuario.get("fecha_registro")
    if fecha_registro:
        if isinstance(fecha_registro, str):
            try:
                fecha_registro = datetime.fromisoformat(fecha_registro.replace('Z', '+00:00'))
            except:
                fecha_registro = None
        elif not isinstance(fecha_registro, datetime):
            fecha_registro = None
    else:
        # Si no hay fecha, usar la fecha de creación del ObjectId
        if "_id" in usuario:
            try:
                fecha_registro = usuario["_id"].generation_time
            except:
                fecha_registro = datetime.utcnow() - timedelta(days=30)
        else:
            fecha_registro = datetime.utcnow() - timedelta(days=30)
    
    # Calcular última conexión basada en la partida más reciente
    ultima_conexion = None
    if partidas:
        partida_reciente = max(partidas, key=lambda x: x.get("date_played", datetime.min) if x.get("date_played") else datetime.min)
        if partida_reciente.get("date_played"):
            ultima_conexion = partida_reciente["date_played"]
    
    if not ultima_conexion:
        # Simular última conexión si no hay partidas
        import random
        hours_ago = random.randint(1, 48)
        ultima_conexion = datetime.utcnow() - timedelta(hours=hours_ago)
    
    # Determinar estado de conexión
    if isinstance(ultima_conexion, datetime):
        hours_since_last = (datetime.utcnow() - ultima_conexion).total_seconds() / 3600
        if hours_since_last < 1:
            estado_conexion = "en línea"
        elif hours_since_last < 24:
            estado_conexion = "activo"
        elif hours_since_last < 168:  # 1 semana
            estado_conexion = "inactivo"
        else:
            estado_conexion = "ausente"
    else:
        estado_conexion = "desconocido"

    return {
        "usuario": {
            "username": username,
            "elo": elo_actual,
            "rol": usuario.get("role", "user"),
            "fecha_registro": fecha_registro.isoformat() if fecha_registro else None,
            "ultima_conexion": ultima_conexion.isoformat() if ultima_conexion else None,
            "estado_conexion": estado_conexion
        },
        "estadisticas": {
            "partidas_jugadas": total_partidas,
            "victorias": victorias,
            "derrotas": derrotas,
            "tablas": tablas,
            "winrate": winrate,
            "puzzles_resueltos": puzzles_correctos,
            "puzzles_totales": total_puzzles,
            "tiempo_total": tiempo_total
        },
        "logros": logros,
        "historial_rating": historial_rating,
        "partidas_recientes": [{
            "id": str(p["_id"]),
            "oponente": p["black_player"] if p["white_player"] == username else p["white_player"],
            "resultado": "Victoria" if p.get("winner") == username else "Derrota" if p.get("winner") and p.get("winner") != "draw" else "Tablas",
            "color": "Blancas" if p["white_player"] == username else "Negras",
            "fecha": p.get("date_played", "").strftime("%d/%m/%Y") if p.get("date_played") else "Sin fecha"
        } for p in partidas_recientes]
    }

# ===== ENDPOINTS DEL PANEL DE ADMINISTRADOR/PROFESOR =====

@router.get("/admin/estudiantes")
async def obtener_estudiantes(request: Request, current_user: dict = Depends(get_current_user)):
    """Obtener lista de estudiantes - solo para profesores"""
    if current_user.get("role") != "profesor":
        raise HTTPException(status_code=403, detail="Acceso denegado - Solo profesores")
    
    db = request.app.state.db
    estudiantes = await db.users.find({"role": "user"}).to_list(None)
    
    # Limpiar datos sensibles y preparar respuesta
    for estudiante in estudiantes:
        estudiante["_id"] = str(estudiante["_id"])
        estudiante.pop("password", None)  # Remover contraseña
        
    return estudiantes

@router.get("/admin/partidas")
async def obtener_partidas_admin(request: Request, current_user: dict = Depends(get_current_user)):
    """Obtener todas las partidas del sistema - solo para profesores"""
    if current_user.get("role") != "profesor":
        raise HTTPException(status_code=403, detail="Acceso denegado - Solo profesores")
    
    db = request.app.state.db
    partidas = await db.games.find().sort("timestamp", -1).limit(100).to_list(None)
    
    # Preparar datos de respuesta
    for partida in partidas:
        partida["_id"] = str(partida["_id"])
        
    return partidas

@router.get("/admin/estadisticas-generales")
async def obtener_estadisticas_generales(request: Request, current_user: dict = Depends(get_current_user)):
    """Obtener estadísticas generales del sistema - solo para profesores"""
    if current_user.get("role") != "profesor":
        raise HTTPException(status_code=403, detail="Acceso denegado - Solo profesores")
    
    db = request.app.state.db
    
    # Contar usuarios
    total_estudiantes = await db.users.count_documents({"role": "user"})
    
    # Contar partidas
    total_partidas = await db.games.count_documents({})
    
    # Estadísticas de puzzles (agregar cuando se implemente)
    total_puzzles = await db.puzzles.count_documents({}) if "puzzles" in await db.list_collection_names() else 0
    
    # Calcular ELO promedio
    pipeline = [
        {"$match": {"role": "user"}},
        {"$group": {"_id": None, "average_elo": {"$avg": "$elo"}}}
    ]
    result = await db.users.aggregate(pipeline).to_list(1)
    elo_promedio = int(result[0]["average_elo"]) if result else 1200
    
    # Actividad reciente (últimas 24 horas)
    hace_24h = datetime.now() - timedelta(hours=24)
    partidas_recientes = await db.games.count_documents({
        "timestamp": {"$gte": hace_24h.isoformat()}
    })
    
    return {
        "total_estudiantes": total_estudiantes,
        "total_partidas": total_partidas,
        "total_puzzles": total_puzzles,
        "average_elo": elo_promedio,
        "partidas_24h": partidas_recientes
    }

@router.delete("/admin/estudiante/{student_id}")
async def eliminar_estudiante(student_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """Eliminar un estudiante - solo para profesores"""
    if current_user.get("role") != "profesor":
        raise HTTPException(status_code=403, detail="Acceso denegado - Solo profesores")
    
    db = request.app.state.db
    
    # Verificar que el usuario existe y es estudiante
    usuario = await db.users.find_one({"_id": ObjectId(student_id), "role": "user"})
    if not usuario:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    # Eliminar usuario
    await db.users.delete_one({"_id": ObjectId(student_id)})
    
    return {"mensaje": "Estudiante eliminado correctamente"}

@router.put("/admin/estudiante/{student_id}")
async def actualizar_estudiante(
    student_id: str, 
    datos: dict, 
    request: Request, 
    current_user: dict = Depends(get_current_user)
):
    """Actualizar datos de un estudiante - solo para profesores"""
    if current_user.get("role") != "profesor":
        raise HTTPException(status_code=403, detail="Acceso denegado - Solo profesores")
    
    db = request.app.state.db
    
    # Verificar que el usuario existe y es estudiante
    usuario = await db.users.find_one({"_id": ObjectId(student_id), "role": "user"})
    if not usuario:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    # Filtrar campos permitidos para actualizar
    campos_permitidos = {"username", "email", "elo"}
    datos_filtrados = {k: v for k, v in datos.items() if k in campos_permitidos}
    
    if datos_filtrados:
        await db.users.update_one(
            {"_id": ObjectId(student_id)},
            {"$set": datos_filtrados}
        )
    
    return {"mensaje": "Estudiante actualizado correctamente"}

@router.get("/admin/estudiante/{student_id}/detalles")
async def obtener_detalles_estudiante(
    student_id: str, 
    request: Request, 
    current_user: dict = Depends(get_current_user)
):
    """Obtener detalles completos de un estudiante - solo para profesores"""
    if current_user.get("role") != "profesor":
        raise HTTPException(status_code=403, detail="Acceso denegado - Solo profesores")
    
    db = request.app.state.db
    
    # Verificar que el usuario existe y es estudiante
    usuario = await db.users.find_one({"_id": ObjectId(student_id), "role": "user"})
    if not usuario:
        raise HTTPException(status_code=404, detail="Estudiante no encontrado")
    
    print(f"DEBUG: Procesando estudiante: {usuario['username']}")
    
    # Obtener estadísticas de partidas del estudiante
    partidas_como_blancas = await db.games.find({"white_player": usuario["username"]}).to_list(None)
    partidas_como_negras = await db.games.find({"black_player": usuario["username"]}).to_list(None)
    todas_las_partidas = partidas_como_blancas + partidas_como_negras
    
    print(f"DEBUG: Partidas encontradas: {len(todas_las_partidas)}")
    
    # Calcular estadísticas de partidas
    partidas_jugadas = len(todas_las_partidas)
    partidas_ganadas = len([p for p in todas_las_partidas if p.get("winner") == usuario["username"]])
    partidas_perdidas = len([p for p in todas_las_partidas if p.get("winner") and p.get("winner") != usuario["username"] and p.get("winner") != "draw"])
    partidas_empatadas = len([p for p in todas_las_partidas if p.get("winner") == "draw"])
    
    # Obtener estadísticas de puzzles
    puzzles_resueltos = usuario.get("puzzles_resueltos_correctamente", 0)
    
    # Obtener progreso de lecciones
    lecciones_completadas = len(usuario.get("progreso_lecciones", []))
    
    # Obtener fecha de registro usando ObjectId.generation_time
    fecha_registro = None
    try:
        # Usar el tiempo de generación del ObjectId como fecha de registro
        object_id = ObjectId(student_id)
        fecha_registro = object_id.generation_time.isoformat()
    except:
        # Si falla, intentar con created_at
        if usuario.get("created_at"):
            try:
                fecha_creacion = datetime.fromisoformat(usuario["created_at"].replace("Z", "+00:00"))
                fecha_registro = fecha_creacion.isoformat()
            except:
                fecha_registro = None
    
    return {
        "partidas_jugadas": partidas_jugadas,
        "partidas_ganadas": partidas_ganadas,
        "partidas_perdidas": partidas_perdidas,
        "partidas_empatadas": partidas_empatadas,
        "puzzles_resueltos": puzzles_resueltos,
        "lecciones_completadas": lecciones_completadas,
        "fecha_registro": fecha_registro,
        "elo_actual": usuario.get("elo", 1200),
        "email": usuario.get("email", ""),
        "username": usuario.get("username", "")
    }

# ===== ENDPOINT TEMPORAL PARA CREAR PROFESORES =====

@router.post("/crear-profesor-temporal")
async def crear_profesor_temporal(request: Request):
    """Endpoint temporal para crear un usuario profesor de prueba"""
    db = request.app.state.db
    
    # Eliminar profesor existente si existe
    await db.users.delete_many({"email": "profesor@chess.edu"})
    
    # Crear usuario profesor
    profesor_data = {
        "username": "profesor",
        "email": "profesor@chess.edu", 
        "password": hash_password("profesor123"),
        "role": "profesor",
        "elo": 1800,
        "games_played": 0,
        "games_won": 0,
        "games_lost": 0,
        "games_drawn": 0,
        "puzzles_resueltos_correctamente": 0,
        "puzzles_resueltos_incorrectamente": 0,
        "historial_puzzles": [],
        "aulas": [],
        "progreso_lecciones": []
    }
    
    result = await db.users.insert_one(profesor_data)
    
    return {
        "mensaje": "Usuario profesor creado exitosamente",
        "id": str(result.inserted_id),
        "credentials": {
            "email": "profesor@chess.edu",
            "password": "profesor123"
        }
    }

# Endpoints para lecciones
@router.get("/lecciones")
async def obtener_lecciones(
    request: Request,
    current_user=Depends(get_current_user)
):
    """
    Obtiene todas las lecciones disponibles para el usuario
    """
    try:
        db = request.app.state.db
        
        # Definir lecciones por defecto (siempre incluir)
        lecciones_default = [
            {
                "_id": "default_1",
                "id": 1,
                "titulo": "Fundamentos del Ajedrez",
                "descripcion": "Aprende las reglas básicas, el tablero y el movimiento de las piezas",
                "contenido": """
# Fundamentos del Ajedrez

## El Tablero de Ajedrez
El ajedrez se juega en un tablero cuadrado de 8x8 casillas (64 casillas en total). Las casillas alternan entre colores claros y oscuros. El tablero siempre debe colocarse de manera que cada jugador tenga una casilla blanca en la esquina inferior derecha.

## Las Piezas y sus Movimientos

### El Rey (♔ ♚)
- Es la pieza más importante del juego
- Se mueve una casilla en cualquier dirección (horizontal, vertical o diagonal)
- No puede moverse a una casilla atacada por el oponente
- Participa en el enroque, una jugada especial

### La Dama/Reina (♕ ♛)
- Es la pieza más poderosa
- Se mueve cualquier número de casillas en línea recta (horizontal, vertical o diagonal)
- Combina los movimientos de la torre y el alfil

### La Torre (♖ ♜)
- Se mueve cualquier número de casillas horizontal o verticalmente
- Participa en el enroque junto con el rey
- En el final de partida es muy poderosa

### El Alfil (♗ ♝)
- Se mueve cualquier número de casillas en diagonal
- Cada jugador tiene un alfil de casillas blancas y otro de casillas negras
- Los alfiles nunca cambian de color de casilla

### El Caballo (♘ ♞)
- Se mueve en forma de "L": dos casillas en una dirección y una casilla perpendicular
- Es la única pieza que puede "saltar" sobre otras piezas
- Siempre cambia de color de casilla en cada movimiento

### El Peón (♙ ♟)
- Se mueve una casilla hacia adelante (dos casillas en su primer movimiento)
- Captura en diagonal hacia adelante
- Puede promocionar al llegar al final del tablero
- Tiene movimientos especiales: captura al paso

## Objetivos del Juego
El objetivo es dar jaque mate al rey del oponente. Esto significa atacar al rey de tal manera que no pueda escapar en la siguiente jugada.

## Conceptos Básicos
- **Jaque**: Cuando el rey está siendo atacado
- **Jaque Mate**: Cuando el rey está en jaque y no puede escapar
- **Ahogado**: Cuando un jugador no tiene movimientos legales pero su rey no está en jaque (tablas)
- **Enroque**: Jugada especial que involucra al rey y una torre
                """,
                "video_url": "https://www.youtube.com/watch?v=OCSbzArwB10",
                "quiz": [
                    {
                        "pregunta": "¿Cuántas casillas tiene un tablero de ajedrez?",
                        "opciones": ["32", "64", "48", "56"],
                        "respuesta_correcta": 1
                    },
                    {
                        "pregunta": "¿Cuál es la única pieza que puede saltar sobre otras?",
                        "opciones": ["Rey", "Caballo", "Alfil", "Torre"],
                        "respuesta_correcta": 1
                    },
                    {
                        "pregunta": "¿En qué esquina debe estar la casilla blanca para cada jugador?",
                        "opciones": ["Inferior izquierda", "Superior derecha", "Inferior derecha", "Superior izquierda"],
                        "respuesta_correcta": 2
                    },
                    {
                        "pregunta": "¿Qué significa 'jaque mate'?",
                        "opciones": ["El rey está atacado", "El rey no puede moverse", "El rey está atacado y no puede escapar", "El juego termina en tablas"],
                        "respuesta_correcta": 2
                    }
                ],
                "dificultad": "Principiante",
                "orden": 1,
                "fecha_creacion": "2024-01-01T00:00:00",
                "creador": "sistema"
            },
            {
                "_id": "default_2", 
                "id": 2,
                "titulo": "Tácticas Básicas de Ajedrez",
                "descripcion": "Aprende las tácticas fundamentales: clavada, horquilla, ataque doble y descubierta",
                "contenido": """
# Tácticas Básicas de Ajedrez

Las tácticas son combinaciones de movimientos que te permiten ganar material o lograr una ventaja posicional. Dominar estas tácticas básicas es esencial para mejorar tu juego.

## 1. La Clavada (Pin)

### ¿Qué es una clavada?
Una clavada ocurre cuando una pieza no puede moverse (o no debe moverse) porque expondrías una pieza más valiosa detrás de ella a un ataque.

### Tipos de clavadas:
- **Clavada absoluta**: La pieza no puede moverse legalmente (como cuando un peón está clavado al rey)
- **Clavada relativa**: La pieza puede moverse, pero sería ventajoso para el oponente

### Ejemplo práctico:
Si tu alfil ataca al caballo del oponente que está delante de su rey, el caballo está "clavado" porque moverlo pondría al rey en jaque.

## 2. La Horquilla (Fork)

### ¿Qué es una horquilla?
Una horquilla es cuando una sola pieza ataca simultáneamente dos o más piezas enemigas.

### Horquillas comunes:
- **Horquilla de caballo**: El caballo ataca dos piezas a la vez
- **Horquilla de peón**: Un peón ataca dos piezas simultáneamente
- **Horquilla de dama**: La dama ataca múltiples objetivos

### Consejo táctico:
Los caballos son especialmente buenos para hacer horquillas debido a su movimiento único en "L".

## 3. El Ataque Doble

### Definición:
Un ataque doble ocurre cuando atacas dos objetivos diferentes con dos piezas distintas en el mismo movimiento.

### Estrategia:
Tu oponente solo puede defender uno de los dos ataques, permitiéndote ganar material en el siguiente movimiento.

## 4. El Ataque a la Descubierta

### ¿Cómo funciona?
Cuando mueves una pieza, "descubres" un ataque de otra pieza que estaba detrás de ella.

### Ventajas:
- La pieza que se mueve puede atacar un objetivo
- La pieza que "se descubre" ataca otro objetivo
- Es muy difícil de defender

## 5. El Jaque a la Descubierta

### Concepto avanzado:
Es un ataque a la descubierta donde la pieza descubierta da jaque al rey enemigo.

### Por qué es poderoso:
El oponente está obligado a salir del jaque, lo que te permite capturar con la pieza que moviste inicialmente.

## Consejos para Detectar Tácticas:

1. **Busca piezas desprotegidas**: Son objetivos fáciles para tácticas
2. **Identifica piezas sobrecargadas**: Piezas que defienden múltiples objetivos
3. **Observa la posición del rey**: Un rey expuesto es vulnerable a tácticas
4. **Cuenta los atacantes y defensores**: Si tienes más atacantes que defensores en una pieza, puedes ganar material

## Práctica Recomendada:
Resuelve problemas tácticos diariamente. Comienza con tácticas simples de 1-2 movimientos y gradualmente aumenta la dificultad.
                """,
                "video_url": "https://www.youtube.com/watch?v=Ao9iOeK_jvU",
                "quiz": [
                    {
                        "pregunta": "¿Qué es una clavada en ajedrez?",
                        "opciones": ["Cuando una pieza ataca a dos piezas", "Cuando una pieza no puede moverse sin exponer otra", "Cuando el rey está en jaque", "Cuando capturas una pieza"],
                        "respuesta_correcta": 1
                    },
                    {
                        "pregunta": "¿Cuál es la táctica donde una pieza ataca simultáneamente a dos objetivos?",
                        "opciones": ["Clavada", "Horquilla", "Ataque doble", "Descubierta"],
                        "respuesta_correcta": 1
                    },
                    {
                        "pregunta": "¿Qué pieza es especialmente buena para hacer horquillas?",
                        "opciones": ["Torre", "Alfil", "Caballo", "Peón"],
                        "respuesta_correcta": 2
                    },
                    {
                        "pregunta": "¿Qué sucede en un ataque a la descubierta?",
                        "opciones": ["Se mueve una pieza y revela el ataque de otra", "Se atacan dos piezas a la vez", "Se clava una pieza al rey", "Se da jaque mate"],
                        "respuesta_correcta": 0
                    },
                    {
                        "pregunta": "¿Por qué el jaque a la descubierta es especialmente poderoso?",
                        "opciones": ["Gana material inmediatamente", "El oponente debe salir del jaque obligatoriamente", "Es imposible de defender", "Termina la partida"],
                        "respuesta_correcta": 1
                    }
                ],
                "dificultad": "Principiante",
                "orden": 2,
                "fecha_creacion": "2024-01-01T00:00:00",
                "creador": "sistema"
            }
        ]
        
        # Para cada lección por defecto, verificar si existe una personalizada
        lecciones_default_finales = []
        for leccion_default in lecciones_default:
            default_id = leccion_default["_id"]
            
            # Buscar si existe una lección personalizada basada en esta por defecto
            # Mostrar a todos los estudiantes la primera lección personalizada encontrada
            leccion_personalizada = await db.lecciones.find_one({
                "basada_en_default": default_id
            })
            
            if leccion_personalizada:
                print(f"[DEBUG] Estudiante - Encontrada lección personalizada para {default_id}: {leccion_personalizada['_id']}")
                # Usar la lección personalizada en lugar de la por defecto
                leccion_personalizada["_id"] = str(leccion_personalizada["_id"])
                if "id" not in leccion_personalizada:
                    leccion_personalizada["id"] = leccion_personalizada["_id"]
                lecciones_default_finales.append(leccion_personalizada)
            else:
                print(f"[DEBUG] Estudiante - No se encontró lección personalizada para {default_id}, usando la por defecto")
                # Usar la lección por defecto original
                lecciones_default_finales.append(leccion_default)
        
        # Obtener lecciones creadas por profesores desde la BD (excluyendo personalizaciones)
        lecciones_profesores = []
        async for leccion in db.lecciones.find({}).sort("orden", 1):
            # Solo incluir lecciones que NO sean personalizaciones de lecciones por defecto
            if not leccion.get("basada_en_default"):
                leccion["_id"] = str(leccion["_id"])
                # Asegurar que todas las lecciones tengan un campo 'id' para navegación
                if "id" not in leccion:
                    leccion["id"] = leccion["_id"]
                # Asegurar campos para lecciones antiguas
                if "fecha_creacion" not in leccion:
                    leccion["fecha_creacion"] = "2024-01-01T00:00:00"
                if "creador" not in leccion:
                    leccion["creador"] = "profesor"
                lecciones_profesores.append(leccion)
        
        # Combinar lecciones (personalizadas/por defecto) + lecciones de profesores
        todas_las_lecciones = lecciones_default_finales.copy()
        
        # Ajustar el orden de las lecciones del profesor para evitar conflictos
        orden_max = max([l["orden"] for l in lecciones_default_finales]) if lecciones_default_finales else 0
        for leccion in lecciones_profesores:
            # Si la lección del profesor tiene orden que no conflicta con las por defecto, mantenerlo
            # Si no, ajustar el orden
            if leccion["orden"] <= orden_max:
                leccion["orden"] = orden_max + leccion["orden"]
            todas_las_lecciones.append(leccion)
        
        # Ordenar todas las lecciones por orden
        todas_las_lecciones.sort(key=lambda x: x["orden"])
        
        return {"lecciones": todas_las_lecciones}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo lecciones: {str(e)}")


@router.post("/lecciones/completar")
async def completar_leccion(
    leccion_data: dict,
    request: Request,
    current_user=Depends(get_current_user)
):
    """
    Marca una lección como completada para el usuario actual
    """
    try:
        db = request.app.state.db
        
        leccion_id = leccion_data.get("leccion_id")
        puntuacion = leccion_data.get("puntuacion", 0)
        
        if not leccion_id:
            raise HTTPException(status_code=400, detail="leccion_id es requerido")
        
        # Obtener el usuario actual
        usuario = await db.users.find_one({"_id": ObjectId(current_user["id"])})
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Verificar si ya completó esta lección
        progreso_lecciones = usuario.get("progreso_lecciones", [])
        leccion_existente = None
        
        for i, progreso in enumerate(progreso_lecciones):
            if progreso.get("leccion_id") == str(leccion_id):
                leccion_existente = i
                break
        
        nuevo_progreso = {
            "leccion_id": str(leccion_id),
            "completada": True,
            "puntuacion": puntuacion,
            "fecha_completada": datetime.now().isoformat()
        }
        
        # Si ya existe, actualizar; si no, agregar
        if leccion_existente is not None:
            progreso_lecciones[leccion_existente] = nuevo_progreso
        else:
            progreso_lecciones.append(nuevo_progreso)
        
        # Actualizar en la base de datos
        await db.users.update_one(
            {"_id": ObjectId(current_user["id"])},
            {
                "$set": {
                    "progreso_lecciones": progreso_lecciones
                }
            }
        )
        
        return {
            "mensaje": "Lección completada exitosamente",
            "leccion_id": leccion_id,
            "puntuacion": puntuacion
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error completando lección: {str(e)}")


@router.get("/progreso-lecciones")
async def obtener_progreso_lecciones(
    request: Request,
    current_user=Depends(get_current_user)
):
    """
    Obtiene el progreso de lecciones del usuario actual
    """
    try:
        db = request.app.state.db
        
        usuario = await db.users.find_one({"_id": ObjectId(current_user["id"])})
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        progreso_lecciones = usuario.get("progreso_lecciones", [])
        
        return {"progreso_lecciones": progreso_lecciones}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo progreso: {str(e)}")


# Endpoints administrativos para lecciones (solo profesores)
@router.post("/admin/lecciones")
async def crear_leccion(
    leccion_data: dict,
    request: Request,
    current_user=Depends(get_current_user)
):
    """
    Crea una nueva lección (solo profesores)
    """
    try:
        # Verificar que el usuario sea profesor
        if current_user.get("role") != "profesor":
            raise HTTPException(status_code=403, detail="Solo los profesores pueden crear lecciones")
        
        db = request.app.state.db
        
        # Validar datos requeridos
        required_fields = ["titulo", "descripcion", "contenido", "dificultad", "orden"]
        for field in required_fields:
            if not leccion_data.get(field):
                raise HTTPException(status_code=400, detail=f"El campo {field} es requerido")
        
        # Preparar datos de la lección
        nueva_leccion = {
            "titulo": leccion_data["titulo"],
            "descripcion": leccion_data["descripcion"],
            "contenido": leccion_data["contenido"],
            "dificultad": leccion_data["dificultad"],
            "orden": int(leccion_data["orden"]),
            "quiz": leccion_data.get("quiz", []),
            "video_url": leccion_data.get("video_url", ""),  # Campo opcional para video de YouTube
            "fecha_creacion": datetime.now().isoformat(),
            "creador": current_user["id"]
        }
        
        # Insertar en la base de datos
        result = await db.lecciones.insert_one(nueva_leccion)
        
        return {
            "mensaje": "Lección creada exitosamente",
            "id": str(result.inserted_id)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creando lección: {str(e)}")


@router.put("/admin/lecciones/{leccion_id}")
async def actualizar_leccion(
    leccion_id: str,
    leccion_data: dict,
    request: Request,
    current_user=Depends(get_current_user)
):
    """
    Actualiza una lección existente (solo profesores)
    Para lecciones por defecto, crea una nueva lección personalizada
    """
    try:
        # Verificar que el usuario sea profesor
        if current_user.get("role") != "profesor":
            raise HTTPException(status_code=403, detail="Solo los profesores pueden editar lecciones")
        
        db = request.app.state.db
        
        # Si es una lección por defecto, crear una nueva lección en lugar de editarla
        if leccion_id.startswith('default_'):
            print(f"[DEBUG] Editando lección por defecto: {leccion_id}")
            print(f"[DEBUG] Datos recibidos: {leccion_data}")
            
            # Preparar datos de la nueva lección basada en la por defecto
            nueva_leccion = {
                "titulo": leccion_data.get("titulo"),
                "descripcion": leccion_data.get("descripcion"),
                "contenido": leccion_data.get("contenido"),
                "dificultad": leccion_data.get("dificultad", "Principiante"),
                "orden": int(leccion_data.get("orden", 1)),
                "quiz": leccion_data.get("quiz", []),
                "video_url": leccion_data.get("video_url", ""),
                "fecha_creacion": datetime.now().isoformat(),
                "creador": current_user["id"],
                "basada_en_default": leccion_id  # Marca para saber que viene de una lección por defecto
            }
            
            print(f"[DEBUG] Nueva lección a crear: {nueva_leccion}")
            
            # Insertar la nueva lección
            result = await db.lecciones.insert_one(nueva_leccion)
            
            print(f"[DEBUG] Lección creada con ID: {str(result.inserted_id)}")
            
            return {
                "mensaje": "Nueva lección creada basada en la lección por defecto",
                "id": str(result.inserted_id),
                "original_default_id": leccion_id
            }
        
        # Para lecciones normales, proceder con la actualización tradicional
        # Verificar que la lección existe
        leccion = await db.lecciones.find_one({"_id": ObjectId(leccion_id)})
        if not leccion:
            raise HTTPException(status_code=404, detail="Lección no encontrada")
        
        # Preparar datos actualizados
        datos_actualizados = {
            "titulo": leccion_data.get("titulo", leccion["titulo"]),
            "descripcion": leccion_data.get("descripcion", leccion["descripcion"]),
            "contenido": leccion_data.get("contenido", leccion["contenido"]),
            "dificultad": leccion_data.get("dificultad", leccion["dificultad"]),
            "orden": int(leccion_data.get("orden", leccion["orden"])),
            "quiz": leccion_data.get("quiz", leccion.get("quiz", [])),
            "video_url": leccion_data.get("video_url", leccion.get("video_url", "")),
            "fecha_modificacion": datetime.now().isoformat(),
            "modificador": current_user["id"]
        }
        
        # Actualizar en la base de datos
        await db.lecciones.update_one(
            {"_id": ObjectId(leccion_id)},
            {"$set": datos_actualizados}
        )
        
        return {
            "mensaje": "Lección actualizada exitosamente",
            "id": leccion_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando lección: {str(e)}")


@router.delete("/admin/lecciones/{leccion_id}")
async def eliminar_leccion(
    leccion_id: str,
    request: Request,
    current_user=Depends(get_current_user)
):
    """
    Elimina una lección (solo profesores)
    """
    try:
        # Verificar que el usuario sea profesor
        if current_user.get("role") != "profesor":
            raise HTTPException(status_code=403, detail="Solo los profesores pueden eliminar lecciones")
        
        db = request.app.state.db
        
        # Si es una lección por defecto, simplemente retornamos éxito
        # (Las lecciones por defecto no se pueden eliminar realmente)
        if leccion_id.startswith('default_'):
            return {
                "mensaje": "Lección eliminada exitosamente",
                "id": leccion_id
            }
        
        # Para lecciones normales, verificar que existe y eliminar
        leccion = await db.lecciones.find_one({"_id": ObjectId(leccion_id)})
        if not leccion:
            raise HTTPException(status_code=404, detail="Lección no encontrada")
        
        # Eliminar la lección
        await db.lecciones.delete_one({"_id": ObjectId(leccion_id)})
        
        # También eliminar el progreso de esta lección de todos los usuarios
        await db.users.update_many(
            {},
            {"$pull": {"progreso_lecciones": {"leccion_id": leccion_id}}}
        )
        
        return {
            "mensaje": "Lección eliminada exitosamente",
            "id": leccion_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error eliminando lección: {str(e)}")


@router.get("/admin/lecciones")
async def listar_lecciones_admin(
    request: Request,
    current_user=Depends(get_current_user)
):
    """
    Lista todas las lecciones para administración (solo profesores)
    """
    try:
        # Verificar que el usuario sea profesor
        if current_user.get("role") != "profesor":
            raise HTTPException(status_code=403, detail="Solo los profesores pueden gestionar lecciones")
        
        db = request.app.state.db
        
        # Definir lecciones por defecto (siempre incluir)
        lecciones_default = [
            {
                "_id": "default_1",
                "id": 1,
                "titulo": "Fundamentos del Ajedrez",
                "descripcion": "Aprende las reglas básicas, el tablero y el movimiento de las piezas",
                "contenido": """
# Fundamentos del Ajedrez

## El Tablero de Ajedrez
El ajedrez se juega en un tablero cuadrado de 8x8 casillas (64 casillas en total). Las casillas alternan entre colores claros y oscuros. El tablero siempre debe colocarse de manera que cada jugador tenga una casilla blanca en la esquina inferior derecha.

## Las Piezas y sus Movimientos

### El Rey (♔ ♚)
- Es la pieza más importante del juego
- Se mueve una casilla en cualquier dirección (horizontal, vertical o diagonal)
- No puede moverse a una casilla atacada por el oponente
- Participa en el enroque, una jugada especial

### La Dama/Reina (♕ ♛)
- Es la pieza más poderosa
- Se mueve cualquier número de casillas en línea recta (horizontal, vertical o diagonal)
- Combina los movimientos de la torre y el alfil

### La Torre (♖ ♜)
- Se mueve cualquier número de casillas horizontal o verticalmente
- Participa en el enroque junto con el rey
- En el final de partida es muy poderosa

### El Alfil (♗ ♝)
- Se mueve cualquier número de casillas en diagonal
- Cada jugador tiene un alfil de casillas blancas y otro de casillas negras
- Los alfiles nunca cambian de color de casilla

### El Caballo (♘ ♞)
- Se mueve en forma de "L": dos casillas en una dirección y una casilla perpendicular
- Es la única pieza que puede "saltar" sobre otras piezas
- Siempre cambia de color de casilla en cada movimiento

### El Peón (♙ ♟)
- Se mueve una casilla hacia adelante (dos casillas en su primer movimiento)
- Captura en diagonal hacia adelante
- Puede promocionar al llegar al final del tablero
- Tiene movimientos especiales: captura al paso

## Objetivos del Juego
El objetivo es dar jaque mate al rey del oponente. Esto significa atacar al rey de tal manera que no pueda escapar en la siguiente jugada.

## Conceptos Básicos
- **Jaque**: Cuando el rey está siendo atacado
- **Jaque Mate**: Cuando el rey está en jaque y no puede escapar
- **Ahogado**: Cuando un jugador no tiene movimientos legales pero su rey no está en jaque (tablas)
- **Enroque**: Jugada especial que involucra al rey y una torre
                """,
                "video_url": "https://www.youtube.com/watch?v=OCSbzArwB10",
                "quiz": [
                    {
                        "pregunta": "¿Cuántas casillas tiene un tablero de ajedrez?",
                        "opciones": ["32", "64", "48", "56"],
                        "respuesta_correcta": 1
                    },
                    {
                        "pregunta": "¿Cuál es la única pieza que puede saltar sobre otras?",
                        "opciones": ["Rey", "Caballo", "Alfil", "Torre"],
                        "respuesta_correcta": 1
                    },
                    {
                        "pregunta": "¿En qué esquina debe estar la casilla blanca para cada jugador?",
                        "opciones": ["Inferior izquierda", "Superior derecha", "Inferior derecha", "Superior izquierda"],
                        "respuesta_correcta": 2
                    },
                    {
                        "pregunta": "¿Qué significa 'jaque mate'?",
                        "opciones": ["El rey está atacado", "El rey no puede moverse", "El rey está atacado y no puede escapar", "El juego termina en tablas"],
                        "respuesta_correcta": 2
                    }
                ],
                "dificultad": "Principiante",
                "orden": 1,
                "fecha_creacion": "2024-01-01T00:00:00",
                "creador": "sistema"
            },
            {
                "_id": "default_2", 
                "id": 2,
                "titulo": "Tácticas Básicas de Ajedrez",
                "descripcion": "Aprende las tácticas fundamentales: clavada, horquilla, ataque doble y descubierta",
                "contenido": """
# Tácticas Básicas de Ajedrez

Las tácticas son combinaciones de movimientos que te permiten ganar material o lograr una ventaja posicional. Dominar estas tácticas básicas es esencial para mejorar tu juego.

## 1. La Clavada (Pin)

### ¿Qué es una clavada?
Una clavada ocurre cuando una pieza no puede moverse (o no debe moverse) porque expondrías una pieza más valiosa detrás de ella a un ataque.

### Tipos de clavadas:
- **Clavada absoluta**: La pieza no puede moverse legalmente (como cuando un peón está clavado al rey)
- **Clavada relativa**: La pieza puede moverse, pero sería ventajoso para el oponente

### Ejemplo práctico:
Si tu alfil ataca al caballo del oponente que está delante de su rey, el caballo está "clavado" porque moverlo pondría al rey en jaque.

## 2. La Horquilla (Fork)

### ¿Qué es una horquilla?
Una horquilla es cuando una sola pieza ataca simultáneamente dos o más piezas enemigas.

### Horquillas comunes:
- **Horquilla de caballo**: El caballo ataca dos piezas a la vez
- **Horquilla de peón**: Un peón ataca dos piezas simultáneamente
- **Horquilla de dama**: La dama ataca múltiples objetivos

### Consejo táctico:
Los caballos son especialmente buenos para hacer horquillas debido a su movimiento único en "L".

## 3. El Ataque Doble

### Definición:
Un ataque doble ocurre cuando atacas dos objetivos diferentes con dos piezas distintas en el mismo movimiento.

### Estrategia:
Tu oponente solo puede defender uno de los dos ataques, permitiéndote ganar material en el siguiente movimiento.

## 4. El Ataque a la Descubierta

### ¿Cómo funciona?
Cuando mueves una pieza, "descubres" un ataque de otra pieza que estaba detrás de ella.

### Ventajas:
- La pieza que se mueve puede atacar un objetivo
- La pieza que "se descubre" ataca otro objetivo
- Es muy difícil de defender

## 5. El Jaque a la Descubierta

### Concepto avanzado:
Es un ataque a la descubierta donde la pieza descubierta da jaque al rey enemigo.

### Por qué es poderoso:
El oponente está obligado a salir del jaque, lo que te permite capturar con la pieza que moviste inicialmente.

## Consejos para Detectar Tácticas:

1. **Busca piezas desprotegidas**: Son objetivos fáciles para tácticas
2. **Identifica piezas sobrecargadas**: Piezas que defienden múltiples objetivos
3. **Observa la posición del rey**: Un rey expuesto es vulnerable a tácticas
4. **Cuenta los atacantes y defensores**: Si tienes más atacantes que defensores en una pieza, puedes ganar material

## Práctica Recomendada:
Resuelve problemas tácticos diariamente. Comienza con tácticas simples de 1-2 movimientos y gradualmente aumenta la dificultad.
                """,
                "video_url": "https://www.youtube.com/watch?v=Ao9iOeK_jvU",
                "quiz": [
                    {
                        "pregunta": "¿Qué es una clavada en ajedrez?",
                        "opciones": ["Cuando una pieza ataca a dos piezas", "Cuando una pieza no puede moverse sin exponer otra", "Cuando el rey está en jaque", "Cuando capturas una pieza"],
                        "respuesta_correcta": 1
                    },
                    {
                        "pregunta": "¿Cuál es la táctica donde una pieza ataca simultáneamente a dos objetivos?",
                        "opciones": ["Clavada", "Horquilla", "Ataque doble", "Descubierta"],
                        "respuesta_correcta": 1
                    },
                    {
                        "pregunta": "¿Qué pieza es especialmente buena para hacer horquillas?",
                        "opciones": ["Torre", "Alfil", "Caballo", "Peón"],
                        "respuesta_correcta": 2
                    },
                    {
                        "pregunta": "¿Qué sucede en un ataque a la descubierta?",
                        "opciones": ["Se mueve una pieza y revela el ataque de otra", "Se atacan dos piezas a la vez", "Se clava una pieza al rey", "Se da jaque mate"],
                        "respuesta_correcta": 0
                    },
                    {
                        "pregunta": "¿Por qué el jaque a la descubierta es especialmente poderoso?",
                        "opciones": ["Gana material inmediatamente", "El oponente debe salir del jaque obligatoriamente", "Es imposible de defender", "Termina la partida"],
                        "respuesta_correcta": 1
                    }
                ],
                "dificultad": "Principiante",
                "orden": 2,
                "fecha_creacion": "2024-01-01T00:00:00",
                "creador": "sistema"
            }
        ]
        
        # Obtener lecciones del profesor desde la BD
        lecciones_profesor = []
        async for leccion in db.lecciones.find({}).sort("orden", 1):
            leccion["_id"] = str(leccion["_id"])
            # Asegurar que todas las lecciones tengan un campo 'id' para navegación
            if "id" not in leccion:
                leccion["id"] = leccion["_id"]
            # Asegurar campos para lecciones antiguas
            if "fecha_creacion" not in leccion:
                leccion["fecha_creacion"] = "2024-01-01T00:00:00"
            if "creador" not in leccion:
                leccion["creador"] = "profesor"
            lecciones_profesor.append(leccion)
        
        # Obtener las lecciones ocultas del profesor
        usuario_id = ObjectId(current_user["id"])
        profesor = await db.users.find_one({"_id": usuario_id})
        lecciones_ocultas = profesor.get("lecciones_ocultas", []) if profesor else []
        
        # Para cada lección por defecto, verificar si existe una personalizada
        lecciones_default_finales = []
        for leccion_default in lecciones_default:
            default_id = leccion_default["_id"]
            
            # Saltar si está oculta
            if default_id in lecciones_ocultas:
                continue
                
            # Buscar si existe una lección personalizada basada en esta por defecto
            leccion_personalizada = await db.lecciones.find_one({
                "basada_en_default": default_id,
                "creador": current_user["id"]
            })
            
            if leccion_personalizada:
                print(f"[DEBUG] Encontrada lección personalizada para {default_id}: {leccion_personalizada['_id']}")
                # Usar la lección personalizada en lugar de la por defecto
                leccion_personalizada["_id"] = str(leccion_personalizada["_id"])
                if "id" not in leccion_personalizada:
                    leccion_personalizada["id"] = leccion_personalizada["_id"]
                lecciones_default_finales.append(leccion_personalizada)
            else:
                print(f"[DEBUG] No se encontró lección personalizada para {default_id}, usando la por defecto")
                # Usar la lección por defecto original
                lecciones_default_finales.append(leccion_default)
        
        # Combinar lecciones (personalizadas/por defecto) + lecciones del profesor
        todas_las_lecciones = lecciones_default_finales.copy()
        
        # Filtrar lecciones del profesor que no sean personalizaciones de por defecto
        lecciones_profesor_filtradas = [
            l for l in lecciones_profesor 
            if not l.get("basada_en_default")
        ]
        
        # Ajustar el orden de las lecciones del profesor para evitar conflictos
        orden_max = max([l["orden"] for l in lecciones_default_finales]) if lecciones_default_finales else 0
        for leccion in lecciones_profesor_filtradas:
            # Si la lección del profesor tiene orden que no conflicta con las por defecto, mantenerlo
            # Si no, ajustar el orden
            if leccion["orden"] <= orden_max:
                leccion["orden"] = orden_max + leccion["orden"]
            todas_las_lecciones.append(leccion)
        
        # Ordenar todas las lecciones por orden
        todas_las_lecciones.sort(key=lambda x: x["orden"])
        
        return {"lecciones": todas_las_lecciones}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo lecciones: {str(e)}")


@router.get("/lecciones/{leccion_id}")
async def obtener_leccion_individual(
    leccion_id: str,
    request: Request,
    current_user=Depends(get_current_user)
):
    """
    Obtiene una lección específica por ID
    """
    try:
        db = request.app.state.db
        
        leccion = None
        
        # Primero intentar buscar por ObjectId (lecciones creadas por profesores)
        try:
            leccion = await db.lecciones.find_one({"_id": ObjectId(leccion_id)})
            if leccion:
                leccion["_id"] = str(leccion["_id"])
        except:
            # Si falla, intentar buscar por ID numérico o string (lecciones por defecto)
            leccion = await db.lecciones.find_one({"id": int(leccion_id) if leccion_id.isdigit() else leccion_id})
            if not leccion:
                leccion = await db.lecciones.find_one({"_id": leccion_id})
        
        # Si no se encuentra en BD, verificar lecciones por defecto
        if not leccion:
            print(f"[DEBUG] Buscando lección: {leccion_id}")
            
            # Primero buscar si hay una lección personalizada para esta lección por defecto
            # Si leccion_id es numérico (1, 2, etc.), verificar si hay personalizada para default_1, default_2, etc.
            if leccion_id.isdigit():
                default_id = f"default_{leccion_id}"
                print(f"[DEBUG] Buscando lección personalizada para: {default_id}")
                
                # Buscar lección personalizada basada en esta por defecto
                # Mostrar a todos los estudiantes la primera lección personalizada encontrada
                leccion_personalizada = await db.lecciones.find_one({
                    "basada_en_default": default_id
                })
                
                if leccion_personalizada:
                    print(f"[DEBUG] Encontrada lección personalizada: {leccion_personalizada['_id']}")
                    leccion_personalizada["_id"] = str(leccion_personalizada["_id"])
                    if "id" not in leccion_personalizada:
                        leccion_personalizada["id"] = leccion_personalizada["_id"]
                    leccion = leccion_personalizada
                else:
                    print(f"[DEBUG] No se encontró lección personalizada, usando por defecto")
            
            # Si no encontramos lección personalizada, usar lecciones por defecto
            if not leccion:
                # Obtener lecciones por defecto
                lecciones_default = [
                {
                    "_id": "default_1",
                    "id": 1,
                    "titulo": "Fundamentos del Ajedrez",
                    "descripcion": "Aprende las reglas básicas, el tablero y el movimiento de las piezas",
                    "contenido": """
# Fundamentos del Ajedrez

## El Tablero de Ajedrez
El ajedrez se juega en un tablero cuadrado de 8x8 casillas (64 casillas en total). Las casillas alternan entre colores claros y oscuros. El tablero siempre debe colocarse de manera que cada jugador tenga una casilla blanca en la esquina inferior derecha.

## Las Piezas y sus Movimientos

### El Rey (♔ ♚)
- Es la pieza más importante del juego
- Se mueve una casilla en cualquier dirección (horizontal, vertical o diagonal)
- No puede moverse a una casilla atacada por el oponente
- Participa en el enroque, una jugada especial

### La Dama/Reina (♕ ♛)
- Es la pieza más poderosa
- Se mueve cualquier número de casillas en línea recta (horizontal, vertical o diagonal)
- Combina los movimientos de la torre y el alfil

### La Torre (♖ ♜)
- Se mueve cualquier número de casillas horizontal o verticalmente
- Participa en el enroque junto con el rey
- En el final de partida es muy poderosa

### El Alfil (♗ ♝)
- Se mueve cualquier número de casillas en diagonal
- Cada jugador tiene un alfil de casillas blancas y otro de casillas negras
- Los alfiles nunca cambian de color de casilla

### El Caballo (♘ ♞)
- Se mueve en forma de "L": dos casillas en una dirección y una casilla perpendicular
- Es la única pieza que puede "saltar" sobre otras piezas
- Siempre cambia de color de casilla en cada movimiento

### El Peón (♙ ♟)
- Se mueve una casilla hacia adelante (dos casillas en su primer movimiento)
- Captura en diagonal hacia adelante
- Puede promocionar al llegar al final del tablero
- Tiene movimientos especiales: captura al paso

## Objetivos del Juego
El objetivo es dar jaque mate al rey del oponente. Esto significa atacar al rey de tal manera que no pueda escapar en la siguiente jugada.

## Conceptos Básicos
- **Jaque**: Cuando el rey está siendo atacado
- **Jaque Mate**: Cuando el rey está en jaque y no puede escapar
- **Ahogado**: Cuando un jugador no tiene movimientos legales pero su rey no está en jaque (tablas)
- **Enroque**: Jugada especial que involucra al rey y una torre
                    """,
                    "video_url": "https://www.youtube.com/watch?v=OCSbzArwB10",
                    "quiz": [
                        {
                            "pregunta": "¿Cuántas casillas tiene un tablero de ajedrez?",
                            "opciones": ["32", "64", "48", "56"],
                            "respuesta_correcta": 1
                        },
                        {
                            "pregunta": "¿Cuál es la única pieza que puede saltar sobre otras?",
                            "opciones": ["Rey", "Caballo", "Alfil", "Torre"],
                            "respuesta_correcta": 1
                        },
                        {
                            "pregunta": "¿En qué esquina debe estar la casilla blanca para cada jugador?",
                            "opciones": ["Inferior izquierda", "Superior derecha", "Inferior derecha", "Superior izquierda"],
                            "respuesta_correcta": 2
                        },
                        {
                            "pregunta": "¿Qué significa 'jaque mate'?",
                            "opciones": ["El rey está atacado", "El rey no puede moverse", "El rey está atacado y no puede escapar", "El juego termina en tablas"],
                            "respuesta_correcta": 2
                        }
                    ],
                    "dificultad": "Principiante",
                    "orden": 1
                },
                {
                    "_id": "default_2", 
                    "id": 2,
                    "titulo": "Tácticas Básicas de Ajedrez",
                    "descripcion": "Aprende las tácticas fundamentales: clavada, horquilla, ataque doble y descubierta",
                    "contenido": """
# Tácticas Básicas de Ajedrez

Las tácticas son combinaciones de movimientos que te permiten ganar material o lograr una ventaja posicional. Dominar estas tácticas básicas es esencial para mejorar tu juego.

## 1. La Clavada (Pin)

### ¿Qué es una clavada?
Una clavada ocurre cuando una pieza no puede moverse (o no debe moverse) porque expondrías una pieza más valiosa detrás de ella a un ataque.

### Tipos de clavadas:
- **Clavada absoluta**: La pieza no puede moverse legalmente (como cuando un peón está clavado al rey)
- **Clavada relativa**: La pieza puede moverse, pero sería ventajoso para el oponente

### Ejemplo práctico:
Si tu alfil ataca al caballo del oponente que está delante de su rey, el caballo está "clavado" porque moverlo pondría al rey en jaque.

## 2. La Horquilla (Fork)

### ¿Qué es una horquilla?
Una horquilla es cuando una sola pieza ataca simultáneamente dos o más piezas enemigas.

### Horquillas comunes:
- **Horquilla de caballo**: El caballo ataca dos piezas a la vez
- **Horquilla de peón**: Un peón ataca dos piezas simultáneamente
- **Horquilla de dama**: La dama ataca múltiples objetivos

### Consejo táctico:
Los caballos son especialmente buenos para hacer horquillas debido a su movimiento único en "L".

## 3. El Ataque Doble

### Definición:
Un ataque doble ocurre cuando atacas dos objetivos diferentes con dos piezas distintas en el mismo movimiento.

### Estrategia:
Tu oponente solo puede defender uno de los dos ataques, permitiéndote ganar material en el siguiente movimiento.

## 4. El Ataque a la Descubierta

### ¿Cómo funciona?
Cuando mueves una pieza, "descubres" un ataque de otra pieza que estaba detrás de ella.

### Ventajas:
- La pieza que se mueve puede atacar un objetivo
- La pieza que "se descubre" ataca otro objetivo
- Es muy difícil de defender

## 5. El Jaque a la Descubierta

### Concepto avanzado:
Es un ataque a la descubierta donde la pieza descubierta da jaque al rey enemigo.

### Por qué es poderoso:
El oponente está obligado a salir del jaque, lo que te permite capturar con la pieza que moviste inicialmente.

## Consejos para Detectar Tácticas:

1. **Busca piezas desprotegidas**: Son objetivos fáciles para tácticas
2. **Identifica piezas sobrecargadas**: Piezas que defienden múltiples objetivos
3. **Observa la posición del rey**: Un rey expuesto es vulnerable a tácticas
4. **Cuenta los atacantes y defensores**: Si tienes más atacantes que defensores en una pieza, puedes ganar material

## Práctica Recomendada:
Resuelve problemas tácticos diariamente. Comienza con tácticas simples de 1-2 movimientos y gradualmente aumenta la dificultad.
                    """,
                    "video_url": "https://www.youtube.com/watch?v=Ao9iOeK_jvU",
                    "quiz": [
                        {
                            "pregunta": "¿Qué es una clavada en ajedrez?",
                            "opciones": ["Cuando una pieza ataca a dos piezas", "Cuando una pieza no puede moverse sin exponer otra", "Cuando el rey está en jaque", "Cuando capturas una pieza"],
                            "respuesta_correcta": 1
                        },
                        {
                            "pregunta": "¿Cuál es la táctica donde una pieza ataca simultáneamente a dos objetivos?",
                            "opciones": ["Clavada", "Horquilla", "Ataque doble", "Descubierta"],
                            "respuesta_correcta": 1
                        },
                        {
                            "pregunta": "¿Qué pieza es especialmente buena para hacer horquillas?",
                            "opciones": ["Torre", "Alfil", "Caballo", "Peón"],
                            "respuesta_correcta": 2
                        },
                        {
                            "pregunta": "¿Qué sucede en un ataque a la descubierta?",
                            "opciones": ["Se mueve una pieza y revela el ataque de otra", "Se atacan dos piezas a la vez", "Se clava una pieza al rey", "Se da jaque mate"],
                            "respuesta_correcta": 0
                        },
                        {
                            "pregunta": "¿Por qué el jaque a la descubierta es especialmente poderoso?",
                            "opciones": ["Gana material inmediatamente", "El oponente debe salir del jaque obligatoriamente", "Es imposible de defender", "Termina la partida"],
                            "respuesta_correcta": 1
                        }
                    ],
                    "dificultad": "Principiante",
                    "orden": 2
                }
                ]
                
                # Buscar en lecciones por defecto
                for leccion_default in lecciones_default:
                    if (leccion_default["_id"] == leccion_id or 
                        str(leccion_default["id"]) == leccion_id or
                        leccion_default["id"] == int(leccion_id) if leccion_id.isdigit() else False):
                        leccion = leccion_default
                        break
        
        if not leccion:
            raise HTTPException(status_code=404, detail="Lección no encontrada")
        
        return leccion
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo lección: {str(e)}")
