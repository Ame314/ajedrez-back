# 🧪 WebSocket Testing Suite - Ajedrez Backend

Esta carpeta contiene todas las herramientas de testing para el sistema de WebSockets del backend de ajedrez.

## 📁 Archivos Incluidos

### 🌐 Interfaz Web

- **`websocket_tester.html`** - Interfaz web interactiva para testing manual

### 🐍 Scripts Python

- **`quick_test.py`** - Prueba rápida de funcionalidades básicas
- **`test_full_game.py`** - Simulación completa de partida entre dos jugadores
- **`test_websockets.py`** - Script interactivo para pruebas detalladas
- **`test_automated.py`** - Suite de pruebas automatizadas

### 📚 Documentación

- **`README.md`** - Este archivo
- **`TESTING_GUIDE.md`** - Guía detallada de testing
- **`EXAMPLES.md`** - Ejemplos de uso

## 🚀 Inicio Rápido

### Prerequisitos

1. Backend ejecutándose en `http://localhost:8000`
2. MongoDB ejecutándose
3. Al menos un usuario registrado

### Configurar Entorno

```bash
# Activar entorno virtual
.venv\Scripts\activate

# Instalar dependencias
pip install websockets requests
```

### Crear Usuarios de Prueba

```bash
# Usuario 1
curl -X POST "http://localhost:8000/registrar" -H "Content-Type: application/json" -d "{\"username\": \"testuser\", \"email\": \"test@example.com\", \"password\": \"password123\"}"

# Usuario 2
curl -X POST "http://localhost:8000/registrar" -H "Content-Type: application/json" -d "{\"username\": \"player2\", \"email\": \"player2@example.com\", \"password\": \"password123\"}"
```

## 🛠️ Herramientas de Testing

### 1. 🌐 Interfaz Web (`websocket_tester.html`)

**Uso:** Abre el archivo en tu navegador web

**Características:**

- ✅ Login visual
- ✅ Conexión WebSocket
- ✅ Pruebas de ping/pong
- ✅ Búsqueda de partidas
- ✅ Envío de movimientos
- ✅ Chat en tiempo real
- ✅ Mensajes personalizados

**Credenciales de prueba:**

- Email: `test@example.com`
- Password: `password123`

### 2. ⚡ Prueba Rápida (`quick_test.py`)

**Uso:**

```bash
python quick_test.py
```

**Qué prueba:**

- ✅ Login automático
- ✅ Conexión WebSocket
- ✅ Ping/Pong
- ✅ Búsqueda de partida
- ✅ Cancelación de búsqueda

**Duración:** ~10 segundos

### 3. 🎮 Partida Completa (`test_full_game.py`)

**Uso:**

```bash
python test_full_game.py
```

**Qué simula:**

- ✅ Dos jugadores conectándose
- ✅ Matchmaking automático
- ✅ Inicio de partida
- ✅ Movimientos de ajedrez
- ✅ Chat durante la partida
- ✅ Sincronización en tiempo real

**Duración:** ~15 segundos

### 4. 🔧 Testing Interactivo (`test_websockets.py`)

**Uso:**

```bash
python test_websockets.py
```

**Características:**

- ✅ Modo interactivo con comandos
- ✅ Control manual de todas las funciones
- ✅ Debugging detallado
- ✅ Pruebas personalizadas

**Comandos disponibles:**

- `ping` - Probar ping
- `find` - Buscar partida
- `cancel` - Cancelar búsqueda
- `move <game_id>` - Hacer movimiento
- `chat <game_id> <mensaje>` - Enviar chat
- `resign <game_id>` - Rendirse
- `quit` - Salir

### 5. 🤖 Suite Automatizada (`test_automated.py`)

**Uso:**

```bash
python test_automated.py
```

**Qué incluye:**

- ✅ Todas las pruebas básicas
- ✅ Manejo de errores
- ✅ Timeouts configurables
- ✅ Reporte detallado
- ✅ Validación de respuestas

## 📊 Resultados Esperados

### ✅ Funcionamiento Correcto

```
🚀 === PRUEBA RÁPIDA DE WEBSOCKETS ===
1️⃣ Haciendo login...
✅ Token obtenido: eyJhbGciOiJIUzI1NiIsInR5cCI6Ik...
2️⃣ Conectando WebSocket...
✅ WebSocket conectado
3️⃣ Enviando ping...
✅ Recibido: {'type': 'pong'}
4️⃣ Buscando partida...
ℹ️ Sin respuesta inmediata (normal sin otro jugador)
5️⃣ Cancelando búsqueda...
✅ Cancelación: {'type': 'match_cancelled'}

🎉 === TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE ===
```

### ❌ Problemas Comunes

1. **Error de conexión:**

   ```
   ❌ Error de conexión: [Errno 111] Connection refused
   ```

   **Solución:** Verificar que el backend esté ejecutándose

2. **Token inválido:**

   ```
   ❌ Error en login: {"detail": "Credenciales inválidas"}
   ```

   **Solución:** Verificar credenciales o crear usuario

3. **WebSocket rechazado:**

   ```
   ❌ Error conectando WebSocket: server rejected WebSocket connection: HTTP 403
   ```

   **Solución:** Verificar token JWT válido

## 🔧 Configuración Avanzada

### Variables de Entorno

```python
# Cambiar URL del servidor
BASE_URL = "http://localhost:8000"  # Modificar en cada script

# Timeouts personalizados
WEBSOCKET_TIMEOUT = 5.0
LOGIN_TIMEOUT = 10.0
```

### Debugging

Para ver más detalles, activar modo verbose en los scripts:

```python
DEBUG = True  # Añadir al inicio de cualquier script
```

## 🆘 Solución de Problemas

### Backend No Responde

```bash
# Verificar contenedores
docker-compose ps

# Ver logs
docker logs fastapi_backend

# Reiniciar servicios
docker-compose down && docker-compose up -d
```

### WebSocket Desconectado

```bash
# Verificar estado del contenedor
docker logs fastapi_backend -f

# Probar endpoint REST
curl http://localhost:8000/
```

### Usuarios No Existen

```bash
# Crear usuarios de prueba
curl -X POST "http://localhost:8000/registrar" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "password123"}'
```

## 📝 Contribuir

Para añadir nuevas pruebas:

1. Crear nuevo archivo en `websocket_test/`
2. Seguir el patrón de los scripts existentes
3. Documentar en este README
4. Probar con diferentes escenarios

## 🎯 Funcionalidades Probadas

| Funcionalidad | quick_test | test_full_game | websocket_tester | test_websockets |
|--------------|------------|----------------|------------------|-----------------|
| Login        | ✅         | ✅             | ✅               | ✅              |
| WebSocket    | ✅         | ✅             | ✅               | ✅              |
| Ping/Pong    | ✅         | ✅             | ✅               | ✅              |
| Matchmaking  | ✅         | ✅             | ✅               | ✅              |
| Movimientos  | ❌         | ✅             | ✅               | ✅              |
| Chat         | ❌         | ✅             | ✅               | ✅              |
| Rendición    | ❌         | ❌             | ✅               | ✅              |
| Interactivo  | ❌         | ❌             | ✅               | ✅              |

---

**🎉 ¡Tu sistema de WebSockets está completamente funcional y probado!**
