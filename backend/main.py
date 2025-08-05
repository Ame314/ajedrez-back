# backend/main.py

from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
from config import MONGODB_URL, DATABASE_NAME

from routes import users, games, puzzles, lessons_eval, websockets, analysis

app = FastAPI()

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexión a MongoDB con manejo robusto de errores
@app.on_event("startup")
async def startup_db_client():
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            print(f"Intento {attempt + 1}/{max_retries} - Conectando a MongoDB en: {MONGODB_URL}")
            client = AsyncIOMotorClient(MONGODB_URL, serverSelectionTimeoutMS=5000)
            
            # Verificar la conexión
            await client.admin.command('ping')
            
            app.state.db = client[DATABASE_NAME]
            print(f"✅ Conexión exitosa a MongoDB - Base de datos: {DATABASE_NAME}")
            return
            
        except Exception as e:
            print(f"❌ Error conectando a MongoDB (intento {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                print(f"Reintentando en {retry_delay} segundos...")
                await asyncio.sleep(retry_delay)
            else:
                print("❌ No se pudo conectar a MongoDB después de varios intentos")
                raise e

@app.on_event("shutdown")
async def shutdown_db_client():
    if hasattr(app.state, 'db'):
        app.state.db.client.close()
        print("✅ Conexión a MongoDB cerrada")

# Ruta simple de prueba
@app.get("/")
async def root():
    return {"mensaje": "Servidor Escolar de Ajedrez activo"}

# Obtener ejercicio diario de Lichess
@app.get("/ejercicios")
async def get_lichess_exercises():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://lichess.org/api/puzzle/daily",
            headers={"Accept": "application/json"}
        )
        return response.json()

# Montar routers
app.include_router(users.router)
app.include_router(games.router)
app.include_router(puzzles.router)
app.include_router(lessons_eval.router)
app.include_router(websockets.router)
app.include_router(analysis.router, prefix="/api")
