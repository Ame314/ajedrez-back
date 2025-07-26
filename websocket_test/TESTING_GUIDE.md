# 📋 Guía Detallada de Testing WebSockets

## 🎯 Objetivos de las Pruebas

Esta guía explica cómo usar cada herramienta de testing y qué esperar de cada una.

## 🔧 Configuración Inicial

### 1. Levantar el Backend

```bash
cd ajedrez-back
docker-compose up -d
```

### 2. Verificar que está funcionando

```bash
curl http://localhost:8000/
# Debería retornar: {"mensaje":"Servidor Escolar de Ajedrez activo"}
```

### 3. Crear usuarios de prueba

```bash
# Usuario 1
curl -X POST "http://localhost:8000/registrar" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "password123"}'

# Usuario 2  
curl -X POST "http://localhost:8000/registrar" \
  -H "Content-Type: application/json" \
  -d '{"username": "player2", "email": "player2@example.com", "password": "password123"}'
```

## 🧪 Herramientas de Testing

### 1. ⚡ Prueba Rápida (`quick_test.py`)

**Propósito:** Verificación rápida de que el sistema funciona básicamente.

**Uso:**

```bash
python quick_test.py
```

**Qué hace:**

1. Hace login con credenciales predefinidas
2. Conecta al WebSocket usando el token JWT
3. Envía un ping y espera pong
4. Busca una partida (sin esperar oponente)
5. Cancela la búsqueda

**Resultado esperado:**

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
ℹ️ Sin respuesta de cancelación

🎉 === TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE ===
```

### 2. 🎮 Partida Completa (`test_full_game.py`)

**Propósito:** Simular una partida completa entre dos jugadores.

**Uso:**

```bash
python test_full_game.py
```

**Qué hace:**

1. Crea dos instancias de jugador
2. Ambos hacen login simultaneamente
3. Ambos se conectan por WebSocket
4. Ambos buscan partida
5. El sistema los empareja automáticamente
6. Simula un movimiento de ajedrez
7. Prueba el chat entre jugadores

**Resultado esperado:**

```
🎯 === PRUEBA DE PARTIDA COMPLETA ===
1️⃣ Login de jugadores...
✅ Jugador1 - Login exitoso
✅ Jugador2 - Login exitoso
2️⃣ Conectando WebSockets...
✅ Jugador1 - WebSocket conectado
✅ Jugador2 - WebSocket conectado
3️⃣ Buscando partida...
4️⃣ Esperando inicio de partida...
🎮 Jugador1 - Juega como white en partida f659262a-3fb2-4593-8dfd-39212953582f
🎮 Jugador2 - Juega como black en partida f659262a-3fb2-4593-8dfd-39212953582f
5️⃣ Simulando movimientos...
🔵 Jugador1 juega con blancas
✅ Jugador1 - Recibió el movimiento
✅ Jugador2 - Recibió el movimiento
6️⃣ Probando chat...
✅ Chat funciona correctamente
🎉 === PRUEBA COMPLETA FINALIZADA ===
```

### 3. 🔧 Testing Interactivo (`test_websockets.py`)

**Propósito:** Control manual completo para debugging y pruebas personalizadas.

**Uso:**

```bash
python test_websockets.py
```

**Flujo interactivo:**

1. Te pide email y password
2. Hace login y conecta WebSocket
3. Te da un prompt con comandos disponibles

**Comandos disponibles:**

- `ping` - Probar ping/pong
- `find` - Buscar partida  
- `cancel` - Cancelar búsqueda
- `move <game_id>` - Hacer movimiento de prueba
- `chat <game_id> <mensaje>` - Enviar chat
- `resign <game_id>` - Rendirse
- `quit` - Salir

**Ejemplo de sesión:**

```
=== TESTER DE WEBSOCKETS AJEDREZ ===

Email: test@example.com
Password: password123
✅ Login exitoso para test@example.com
✅ Conectado al WebSocket

Comandos disponibles:
1. ping - Probar ping
2. find - Buscar partida
3. cancel - Cancelar búsqueda
...

Comando: ping
📤 Enviado: {'type': 'ping'}
📥 Recibido: {'type': 'pong'}

Comando: find
📤 Enviado: {'type': 'find_match', 'elo': 1200}
ℹ️ Buscando partida...

Comando: quit
🛑 Interrumpido por usuario
🔌 Conexión cerrada
```

### 4. 🌐 Interfaz Web (`websocket_tester.html`)

**Propósito:** Interfaz visual para testing manual y debugging.

**Uso:**

1. Abre el archivo en tu navegador
2. Completa los campos de login
3. Usa los botones para probar funcionalidades

**Características:**

- **Sección 1:** Login y obtención de token
- **Sección 2:** Conexión WebSocket
- **Sección 3:** Visualización de mensajes en tiempo real
- **Sección 4:** Botones para pruebas rápidas
- **Sección 5:** Envío de mensajes personalizados

**Credenciales de prueba:**

- Email: `test@example.com`
- Password: `password123`

## 🐛 Debugging y Solución de Problemas

### Error: Connection Refused

```
❌ Error de conexión: [Errno 111] Connection refused
```

**Causa:** El backend no está ejecutándose.

**Solución:**

```bash
# Verificar contenedores
docker-compose ps

# Si no están ejecutándose
docker-compose up -d

# Verificar logs
docker logs fastapi_backend
```

### Error: Token Inválido

```
❌ Error en login: {"detail": "Credenciales inválidas"}
```

**Causa:** Usuario no existe o contraseña incorrecta.

**Solución:**

```bash
# Crear el usuario
curl -X POST "http://localhost:8000/registrar" \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "password123"}'
```

### Error: WebSocket Connection Closed

```
❌ Error conectando WebSocket: server rejected WebSocket connection: HTTP 403
```

**Causa:** Token JWT inválido o expirado.

**Solución:**

1. Verificar que el login fue exitoso
2. Usar un token recién obtenido
3. Verificar que el endpoint WebSocket esté funcionando

### Error: Timeout en Mensajes

```
⏰ Timeout esperando mensaje (5.0s)
```

**Causa:** El servidor no responde o está sobrecargado.

**Solución:**

1. Verificar logs del backend
2. Aumentar timeout en los scripts
3. Reiniciar el backend si es necesario

## 📊 Interpretación de Resultados

### ✅ Sistema Funcionando Correctamente

**Indicadores positivos:**

- Login exitoso con token JWT
- Conexión WebSocket establecida
- Ping/Pong responde inmediatamente
- Matchmaking acepta solicitudes
- Movimientos se sincronizan entre jugadores
- Chat funciona en tiempo real

### ⚠️ Problemas Menores

**Síntomas:**

- Timeouts ocasionales
- Mensajes que llegan con retraso
- Cancelaciones que no responden

**Acciones:**

- Verificar carga del sistema
- Revisar logs para errores
- Probar con menos concurrencia

### ❌ Sistema No Funcional

**Síntomas:**

- No se puede hacer login
- WebSocket rechaza conexiones
- No hay respuesta a ningún mensaje
- Errores 500 del servidor

**Acciones:**

1. Reiniciar completamente el backend
2. Verificar base de datos MongoDB
3. Revisar logs detalladamente
4. Verificar configuración de red

## 🔄 Flujo de Testing Recomendado

### Para Desarrollo Diario

1. `quick_test.py` - Verificación rápida (30 segundos)

### Para Testing de Funcionalidades

1. `test_full_game.py` - Prueba completa (1 minuto)
2. `websocket_tester.html` - Prueba manual específica

### Para Debugging Detallado

1. `test_websockets.py` - Control manual completo

### Para Testing de Carga

1. Ejecutar múltiples instancias de `test_full_game.py` simultaneamente

## 📝 Personalización de Tests

### Modificar Credenciales

En cualquier script, cambiar:

```python
# Cambiar estas líneas
email = "test@example.com"
password = "password123"
```

### Modificar URL del Servidor

```python
# En la clase o al inicio del script
BASE_URL = "http://localhost:8000"  # Cambiar si es necesario
```

### Añadir Nuevas Pruebas

1. Copiar uno de los scripts existentes
2. Modificar la lógica según tus necesidades
3. Documentar la nueva funcionalidad

---

**🎯 Con estas herramientas puedes probar exhaustivamente tu sistema de WebSockets sin necesidad de un frontend completo.**
