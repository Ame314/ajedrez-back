# ajedrez-back

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

por cierto, para alguien que quiera ejecutar el proyecto tiene que descargar los ejercicios de aca: https://database.lichess.org/#evals
por dios, no meter todo eso a la bdd de docker que se cae el servicio, para hacerlo se ejecutan los scrips que están en /backend/utils/cargar_lecciones.py. con eso vas a cargar solo 1000 líneas, la idea es cargar más pero no demasiado que se cae el contenedor ya que el archivo pesa como 24GB, para ls puzzles es igual en la ruta: /backend/utils/cargar_puzzles.py pero aca si carga todo que solo son 2GB y algo ese si está en el proyecto 
