# backend/main.py

from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
import httpx

from routes import users, games, puzzles, lessons_eval, websockets

app = FastAPI()

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conexión a MongoDB local
@app.on_event("startup")
async def startup_db_client():
    client = AsyncIOMotorClient("mongodb://mongo:27017")
    app.state.db = client.ajedrez_db

@app.on_event("shutdown")
async def shutdown_db_client():
    app.state.db.client.close()

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
