# 🏫 Backend del Servidor Escolar de Ajedrez

API backend desarrollada con FastAPI para un sistema educativo de ajedrez que incluye análisis de partidas, puzzles, lecciones y gestión de usuarios.

## 🚀 Inicio Rápido

### Prerrequisitos

- Python 3.11 o superior
- Docker Desktop
- macOS con Homebrew (para la instalación automática de Stockfish)

### Instalación y Ejecución

1. **Clonar el repositorio:**

```bash
git clone <url-del-repositorio>
cd ajedrez-back
```

2. **Ejecutar el entorno de desarrollo:**

```bash
./start_dev.sh
```

Este script automaticamente:

- ✅ Verifica que Docker esté ejecutándose
- ✅ Instala Stockfish si no está presente (macOS con Homebrew)
- ✅ Levanta MongoDB en Docker
- ✅ Instala las dependencias de Python
- ✅ Inicia el servidor FastAPI en <http://localhost:8000>

3. **Para detener el entorno:**

```bash
./stop_dev.sh
```

## 🌐 Endpoints Principales

- **API Root:** <http://localhost:8000>
- **Documentación:** <http://localhost:8000/docs>
- **Ejercicios de Lichess:** <http://localhost:8000/ejercicios>
- **Análisis de partidas:** <http://localhost:8000/api/analisis/{partida_id}>

## 🏗️ Estructura del Proyecto

```
backend/
├── main.py              # Aplicación principal FastAPI
├── config.py            # Configuración y variables de entorno
├── requirements.txt     # Dependencias de Python
├── .env                 # Variables de entorno locales
├── models/              # Modelos de datos Pydantic
├── routes/              # Endpoints de la API
│   ├── users.py         # Gestión de usuarios
│   ├── games.py         # Partidas de ajedrez
│   ├── puzzles.py       # Puzzles y ejercicios
│   ├── analysis.py      # Análisis con Stockfish
│   └── websockets.py    # Conexiones en tiempo real
└── utils/               # Utilidades y helpers
    ├── auth.py          # Autenticación JWT
    ├── stockfish_analysis.py  # Análisis de partidas
    └── websocket_manager.py   # Gestión WebSocket
```

## 🔧 Configuración

El archivo `.env` contiene las variables de entorno necesarias:

```env
# SMTP para emails
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=tu_email@gmail.com
SMTP_PASSWORD=tu_app_password

# Frontend URL
FRONTEND_URL=http://localhost:3000

# Base de datos MongoDB
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=ajedrez_db
```

## 🐳 Despliegue con Docker

Para usar el entorno completo con Docker:

```bash
docker-compose up --build
```

Esto levantará:

- MongoDB en puerto 27017
- Backend FastAPI en puerto 8000

## 🧩 Dependencias Principales

- **FastAPI:** Framework web moderno y rápido
- **Motor:** Driver asíncrono de MongoDB
- **Stockfish:** Motor de ajedrez para análisis
- **python-chess:** Biblioteca para manejar lógica de ajedrez
- **uvicorn:** Servidor ASGI para FastAPI
- **PyJWT:** Tokens de autenticación
- **python-dotenv:** Manejo de variables de entorno

## 🔍 Análisis de Partidas

El sistema utiliza Stockfish para analizar partidas de ajedrez:

- Evaluación de posiciones
- Sugerencias de mejores jugadas
- Comentarios automáticos sobre la calidad de las jugadas
- Detección de errores y blunders

## 📝 Notas de Desarrollo

- El servidor se ejecuta con recarga automática en modo desarrollo
- Stockfish se instala automáticamente en macOS con Homebrew
- MongoDB se ejecuta en contenedor Docker para facilitar el desarrollo
- Las rutas de API están organizadas por funcionalidad

## 🛠️ Solución de Problemas

### Error "Stockfish no encontrado"

```bash
brew install stockfish
```

### Error "Puerto 8000 en uso"

```bash
./stop_dev.sh
```

### Error de conexión a MongoDB

```bash
docker-compose restart mongo
```

## 📊 API Documentation

Una vez que el servidor esté ejecutándose, visita:

- **Swagger UI:** <http://localhost:8000/docs>
- **ReDoc:** <http://localhost:8000/redoc>

⚙️ INICIO DEL PROYECTO

1. 🐳 Crear contenedores con Docker Compose
docker-compose up --build
Para: construir y levantar los contenedores (FastAPI + MongoDB).

Usar --build si hiciste cambios en el Dockerfile.

2. 🔁 Reiniciar contenedores

docker-compose down
Para: apagar todos los servicios.

docker-compose up -d
Para: levantarlos otra vez en segundo plano (-d = detached).

🧪 PRUEBAS Y DEBUG
3. 🐳 Ver contenedores en ejecución

docker ps
4. 📜 Ver logs del backend

docker logs fastapi_backend -f
Muestra los logs en tiempo real de tu app FastAPI.

5. 🧠 Acceder al contenedor de MongoDB

docker exec -it mongodb mongosh
Abre la terminal interactiva para trabajar directamente con MongoDB.

🧩 BASE DE DATOS: COMANDOS EN mongosh
6. 📂 Ver bases de datos
show dbs
7. 📁 Cambiar de base
use ajedrez_db
8. 📄 Ver colecciones
show collections
9. 📦 Consultar datos de usuarios
db.users.find().pretty()
10. 🎮 Consultar partidas por usuario

db.games.find({ jugadores: "ame" }).pretty()
11. ❌ Borrar un documento

db.games.deleteOne({ _id: ObjectId("tu_id_aqui") })

🛠️ FASTAPI: ESTRUCTURA Y USO
12. 🛣️ Rutas principales
POST /registrar → Crea usuario

POST /login → Inicia sesión

POST /guardar-partida → Guarda partida

GET /partidas/{username} → Devuelve partidas del jugador (si es user o opponent)

Arquitectura del proyecto

/backend

Librerías que vamos a usar:
pip install python-jose[cryptography] passlib[bcrypt] python-multipart

por cierto, para alguien que quiera ejecutar el proyecto tiene que descargar los ejercicios de aca: <https://database.lichess.org/#evals>
por dios, no meter todo eso a la bdd de docker que se cae el servicio, para hacerlo se ejecutan los scrips que están en /backend/utils/cargar_lecciones.py. con eso vas a cargar solo 1000 líneas, la idea es cargar más pero no demasiado que se cae el contenedor ya que el archivo pesa como 24GB, para ls puzzles es igual en la ruta: /backend/utils/cargar_puzzles.py pero aca si carga todo que solo son 2GB y algo ese si está en el proyecto
