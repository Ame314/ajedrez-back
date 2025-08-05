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
    
    # Calcular estadísticas de partidas
    total_partidas = len(partidas)
    victorias = sum(1 for p in partidas if p.get("winner") == username)
    derrotas = sum(1 for p in partidas if p.get("winner") and p.get("winner") != username and p.get("winner") != "draw")
    tablas = sum(1 for p in partidas if p.get("winner") == "draw")
    winrate = round((victorias / total_partidas * 100), 1) if total_partidas > 0 else 0
    
    # Calcular tiempo total jugado (estimación basada en partidas)
    tiempo_estimado_minutos = total_partidas * 15  # Estimamos 15 min por partida
    horas = tiempo_estimado_minutos // 60
    minutos = tiempo_estimado_minutos % 60
    tiempo_total = f"{horas}h {minutos}m"
    
    # Obtener puzzles resueltos
    puzzles_correctos = usuario.get("puzzles_resueltos_correctamente", 0)
    puzzles_incorrectos = usuario.get("puzzles_resueltos_incorrectamente", 0)
    total_puzzles = puzzles_correctos + puzzles_incorrectos
    
    # Calcular logros
    logros = []
    
    # Primera partida
    logros.append({
        "name": "Primera Partida",
        "description": "Juega tu primera partida",
        "earned": total_partidas > 0
    })
    
    # Puzzle Master
    logros.append({
        "name": "Puzzle Master", 
        "description": "Resuelve 10 puzzles",
        "earned": puzzles_correctos >= 10
    })
    
    # Estratega
    logros.append({
        "name": "Estratega",
        "description": "Gana 5 partidas consecutivas", 
        "earned": victorias >= 5
    })
    
    # Veterano
    logros.append({
        "name": "Veterano",
        "description": "Juega 50 partidas",
        "earned": total_partidas >= 50
    })
    
    # Maestro de Puzzles
    logros.append({
        "name": "Maestro de Puzzles",
        "description": "Resuelve 100 puzzles correctamente",
        "earned": puzzles_correctos >= 100
    })
    
    # Invencible
    logros.append({
        "name": "Invencible",
        "description": "Gana 20 partidas",
        "earned": victorias >= 20
    })
    
    # Obtener historial reciente de rating (últimas 10 partidas)
    partidas_recientes = sorted(partidas, key=lambda x: x.get("timestamp", 0), reverse=True)[:10]
    historial_rating = []
    elo_actual = usuario.get("elo", 1200)
    
    for i, partida in enumerate(reversed(partidas_recientes)):
        # Simular cambios de ELO basado en resultados
        if partida.get("winner") == username:
            cambio = 25
        elif partida.get("winner") == "draw":
            cambio = 0
        else:
            cambio = -25
            
        elo_en_partida = elo_actual - (cambio * i)
        historial_rating.append({
            "partida": len(partidas_recientes) - i,
            "elo": max(800, elo_en_partida)  # ELO mínimo de 800
        })
    
    return {
        "usuario": {
            "username": username,
            "elo": elo_actual,
            "rol": usuario.get("role", "user")
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
            "fecha": p.get("timestamp", "")
        } for p in partidas_recientes[:5]]
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
    
    # Calcular última conexión (basado en la partida más reciente)
    ultima_conexion = "No disponible"
    if todas_las_partidas:
        partida_reciente = max(todas_las_partidas, key=lambda x: x.get("timestamp", ""))
        if partida_reciente.get("timestamp"):
            try:
                fecha_partida = datetime.fromisoformat(partida_reciente["timestamp"].replace("Z", "+00:00"))
                ultima_conexion = fecha_partida.strftime("%d/%m/%Y %H:%M")
            except:
                ultima_conexion = "No disponible"
    
    # Obtener fecha de registro
    fecha_registro = "No disponible"
    if usuario.get("created_at"):
        try:
            fecha_creacion = datetime.fromisoformat(usuario["created_at"].replace("Z", "+00:00"))
            fecha_registro = fecha_creacion.strftime("%d/%m/%Y")
        except:
            fecha_registro = "No disponible"
    
    return {
        "partidas_jugadas": partidas_jugadas,
        "partidas_ganadas": partidas_ganadas,
        "partidas_perdidas": partidas_perdidas,
        "partidas_empatadas": partidas_empatadas,
        "puzzles_resueltos": puzzles_resueltos,
        "lecciones_completadas": lecciones_completadas,
        "fecha_registro": fecha_registro,
        "ultima_conexion": ultima_conexion,
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
        
        # Obtener todas las lecciones de la base de datos
        lecciones = []
        async for leccion in db.lecciones.find({}):
            leccion["_id"] = str(leccion["_id"])
            lecciones.append(leccion)
        
        # Si no hay lecciones en BD, devolver lecciones por defecto
        if not lecciones:
            lecciones_default = [
                {
                    "_id": "1",
                    "id": 1,
                    "titulo": "Introducción al Ajedrez",
                    "descripcion": "Aprende los fundamentos básicos del ajedrez",
                    "contenido": "El ajedrez es un juego de estrategia que se juega en un tablero de 8x8 casillas...",
                    "quiz": [
                        {
                            "pregunta": "¿Cuántas casillas tiene un tablero de ajedrez?",
                            "opciones": ["32", "64", "48", "56"],
                            "respuesta_correcta": 1
                        }
                    ],
                    "dificultad": "Principiante",
                    "orden": 1
                },
                {
                    "_id": "2", 
                    "id": 2,
                    "titulo": "Movimiento de las Piezas",
                    "descripcion": "Aprende cómo se mueve cada pieza",
                    "contenido": "Cada pieza en el ajedrez tiene su propio patrón de movimiento único...",
                    "quiz": [
                        {
                            "pregunta": "¿Cuál es la única pieza que puede saltar sobre otras?",
                            "opciones": ["Rey", "Caballo", "Alfil", "Torre"],
                            "respuesta_correcta": 1
                        }
                    ],
                    "dificultad": "Principiante",
                    "orden": 2
                }
            ]
            return {"lecciones": lecciones_default}
        
        return {"lecciones": lecciones}
        
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
