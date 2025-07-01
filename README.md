# ajedrez-back

⚙️ INICIO DEL PROYECTO
1. 🐳 Crear contenedores con Docker Compose
bash
Copiar
Editar
docker-compose up --build
Para: construir y levantar los contenedores (FastAPI + MongoDB).

Usar --build si hiciste cambios en el Dockerfile.

2. 🔁 Reiniciar contenedores
bash
Copiar
Editar
docker-compose down
Para: apagar todos los servicios.

bash
Copiar
Editar
docker-compose up -d
Para: levantarlos otra vez en segundo plano (-d = detached).

🧪 PRUEBAS Y DEBUG
3. 🐳 Ver contenedores en ejecución
bash
Copiar
Editar
docker ps
4. 📜 Ver logs del backend
bash
Copiar
Editar
docker logs fastapi_backend -f
Muestra los logs en tiempo real de tu app FastAPI.

5. 🧠 Acceder al contenedor de MongoDB
bash
Copiar
Editar
docker exec -it mongodb mongosh
Abre la terminal interactiva para trabajar directamente con MongoDB.

🧩 BASE DE DATOS: COMANDOS EN mongosh
6. 📂 Ver bases de datos
js
Copiar
Editar
show dbs
7. 📁 Cambiar de base
js
Copiar
Editar
use ajedrez_db
8. 📄 Ver colecciones
js
Copiar
Editar
show collections
9. 📦 Consultar datos de usuarios
js
Copiar
Editar
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