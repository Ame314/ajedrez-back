from fastapi import APIRouter, Request, Depends, HTTPException
from bson import ObjectId
from models.aula import Aula
from models.user import User
from models.leccion import Leccion
from auth import get_current_user  # Asegúrate de tener esta función

router = APIRouter()

@router.post("/aulas")
async def crear_aula(aula: Aula, request: Request, current_user: User = Depends(get_current_user)):
    if current_user.role != "profesor":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    result = await request.app.state.db.aulas.insert_one(aula.dict())
    return {"mensaje": "Aula creada", "id": str(result.inserted_id)}

@router.get("/aulas")
async def obtener_aulas(request: Request):
    db = request.app.state.db
    aulas = await db.aulas.find().to_list(100)
    for aula in aulas:
        aula["_id"] = str(aula["_id"])
    return aulas    

@router.get("/aulas/{aula_id}")
async def obtener_aula(aula_id: str, request: Request):
    db = request.app.state.db
    aula = await db.aulas.find_one({"_id": ObjectId(aula_id)})
    if not aula:
        raise HTTPException(status_code=404, detail="Aula no encontrada")
    aula["_id"] = str(aula["_id"])
    return aula

@router.post("/aulas/{aula_id}/unirse")
async def unirse_aula(aula_id: str, request: Request, current_user: User = Depends(get_current_user)):
    await request.app.state.db.aulas.update_one(
        {"_id": ObjectId(aula_id)},
        {"$addToSet": {"usuarios": current_user.id}}
    )
    await request.app.state.db.users.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$addToSet": {"aulas": aula_id}}
    )
    return {"mensaje": "Unido al aula"}

@router.post("/aulas/{aula_id}/lecciones")
async def crear_leccion(leccion: Leccion, aula_id: str, request: Request, current_user: User = Depends(get_current_user)):
    if current_user.role != "profesor":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    leccion.aula_id = aula_id
    result = await request.app.state.db.lecciones.insert_one(leccion.dict())
    await request.app.state.db.aulas.update_one(
        {"_id": ObjectId(aula_id)},
        {"$addToSet": {"lecciones": str(result.inserted_id)}}
    )
    return {"mensaje": "Lección creada", "id": str(result.inserted_id)}

@router.get("/aulas/{aula_id}/lecciones")
async def obtener_lecciones(aula_id: str, request: Request):
    lecciones = await request.app.state.db.lecciones.find({"aula_id": aula_id}).to_list(100)
    for leccion in lecciones:
        leccion["_id"] = str(leccion["_id"])
    return lecciones

@router.post("/lecciones/{leccion_id}/asignar/{user_id}")
async def asignar_leccion(leccion_id: str, user_id: str, request: Request, current_user: User = Depends(get_current_user)):
    if current_user.role != "profesor":
        raise HTTPException(status_code=403, detail="No autorizado")
    
    await request.app.state.db.lecciones.update_one(
        {"_id": ObjectId(leccion_id)},
        {"$addToSet": {"asignada_a": user_id}}
    )
    return {"mensaje": "Lección asignada"}

@router.post("/lecciones/{leccion_id}/completar")
async def completar_leccion(leccion_id: str, request: Request, current_user: User = Depends(get_current_user)):
    await request.app.state.db.users.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$addToSet": {"progreso_lecciones": leccion_id}}
    )
    return {"mensaje": "Lección marcada como completada"}

@router.get("/aulas/{aula_id}/progreso")
async def progreso_por_aula(aula_id: str, request: Request):
    users = await request.app.state.db.users.find({"aulas": aula_id}).to_list(100)
    lecciones = await request.app.state.db.lecciones.find({"aula_id": aula_id}).to_list(100)

    progreso = []
    for user in users:
        completadas = set(user.get("progreso_lecciones", []))
        completadas_count = 0
        for l in lecciones:
            l_id_str = str(l["_id"])
            if l_id_str in completadas:
                completadas_count += 1
        progreso.append({
            "usuario": user["username"],
            "completadas": completadas_count,
            "total": len(lecciones)
        })

    return progreso
