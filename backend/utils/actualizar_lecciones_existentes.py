# Actualizar lecciones existentes con campos faltantes
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime

async def actualizar_lecciones_existentes():
    """
    Script para actualizar lecciones existentes y añadir campos faltantes
    """
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.chess_app
    
    try:
        # Buscar lecciones que no tienen fecha_creacion o creador
        lecciones_sin_actualizar = []
        async for leccion in db.lecciones.find({
            "$or": [
                {"fecha_creacion": {"$exists": False}},
                {"creador": {"$exists": False}}
            ]
        }):
            lecciones_sin_actualizar.append(leccion)
        
        print(f"Encontradas {len(lecciones_sin_actualizar)} lecciones para actualizar")
        
        # Actualizar cada lección
        for leccion in lecciones_sin_actualizar:
            update_data = {}
            
            # Añadir fecha_creacion si no existe
            if "fecha_creacion" not in leccion:
                update_data["fecha_creacion"] = "2024-01-01T00:00:00"
            
            # Añadir creador si no existe
            if "creador" not in leccion:
                update_data["creador"] = "sistema"
            
            # Actualizar la lección
            await db.lecciones.update_one(
                {"_id": leccion["_id"]},
                {"$set": update_data}
            )
            
            print(f"Actualizada lección: {leccion.get('titulo', 'Sin título')}")
        
        print("¡Actualización completada!")
        
    except Exception as e:
        print(f"Error actualizando lecciones: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(actualizar_lecciones_existentes())
