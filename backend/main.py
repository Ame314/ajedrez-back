# backend/main.py
# Este es el punto de entrada de tu aplicación FastAPI
# Aquí se configuran las rutas, la conexión a la base de datos y CORS
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi.middleware.cors import CORSMiddleware
import httpx

from routes import users, games

app = FastAPI()

# Configuración de CORS
# CORS para permitir peticiones desde tu frontend
# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <-- PERMITE CUALQUIER ORIGEN 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Conexión a Mongo
@app.on_event("startup")
async def startup_db_client():
    client = AsyncIOMotorClient("mongodb://mongo:27017")
    app.state.db = client.ajedrez_db  # Esto es lo importante

@app.on_event("shutdown")
async def shutdown_db_client():
    app.state.db.client.close()

# Rutas base
@app.get("/")
async def root():
    return {"mensaje": "Servidor Escolar de Ajedrez activo"}

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
