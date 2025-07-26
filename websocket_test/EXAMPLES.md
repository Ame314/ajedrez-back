# 💡 Ejemplos de Uso - WebSocket Testing

## 🎯 Escenarios de Prueba Comunes

### 1. ⚡ Verificación Rápida del Sistema

**Cuando usar:** Cada vez que hagas cambios al código y quieras verificar que no rompiste nada.

**Comando:**

```bash
python quick_test.py
```

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

### 2. 🎮 Simulación de Partida Completa

**Cuando usar:** Para probar el flujo completo de una partida entre dos jugadores.

**Comando:**

```bash
python test_full_game.py
```

**Qué verás:**

1. Dos jugadores hacen login simultáneamente
2. Ambos se conectan por WebSocket
3. El sistema los empareja automáticamente
4. Se inicia una partida con colores asignados
5. Se simula un movimiento de ajedrez
6. Se prueba el chat entre jugadores

### 3. 🔧 Testing Manual Detallado

**Cuando usar:** Para debugging específico o probar funcionalidades paso a paso.

**Comando:**

```bash
python test_websockets.py
```

**Ejemplo de sesión interactiva:**

```
=== TESTER DE WEBSOCKETS AJEDREZ ===

Email: test@example.com
Password: password123
✅ Login exitoso
✅ Conectado al WebSocket

Comando: ping
📤 Enviado: {'type': 'ping'}
📥 Recibido: {'type': 'pong'}

Comando: find
📤 Enviado: {'type': 'find_match', 'elo': 1200}
ℹ️ Buscando partida...

Comando: cancel
📤 Enviado: {'type': 'cancel_match'}
📥 Recibido: {'type': 'match_cancelled'}

Comando: quit
🔌 Conexión cerrada
```

### 4. 🌐 Testing Visual con Navegador

**Cuando usar:** Para testing manual con interfaz visual y debugging de mensajes.

**Pasos:**

1. Abre `websocket_tester.html` en tu navegador
2. Introduce las credenciales:
   - Email: `test@example.com`
   - Password: `password123`
3. Haz clic en "Login y Obtener Token"
4. Haz clic en "Conectar WebSocket"
5. Usa los botones para probar diferentes funcionalidades

## 🎪 Escenarios Específicos de Testing

### Escenario 1: Probar Autenticación

**Objetivo:** Verificar que el sistema de login funciona correctamente.

**Método:** Manual con curl

```bash
# Login exitoso
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'

# Debería retornar algo como:
# {"mensaje":"Login exitoso","access_token":"eyJhbGciOiJIUzI1NiIs...","token_type":"bearer"}

# Login fallido
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "wrongpassword"}'

# Debería retornar:
# {"detail":"Credenciales inválidas"}
```

### Escenario 2: Matchmaking con Múltiples Usuarios

**Objetivo:** Probar que el sistema empareja jugadores correctamente.

**Método:** Abrir dos terminales y ejecutar simultaneamente:

**Terminal 1:**

```bash
python test_websockets.py
# Introducir: test@example.com / password123
# Comando: find
```

**Terminal 2:**

```bash
python test_websockets.py  
# Introducir: player2@example.com / password123
# Comando: find
```

**Resultado esperado:** Ambos jugadores deberían recibir un mensaje `game_start` con el mismo `game_id`.

### Escenario 3: Chat Durante Partida

**Objetivo:** Verificar que el chat funciona entre jugadores.

**Prerequisito:** Tener una partida activa (usar Escenario 2)

**En Terminal 1:**

```
Comando: chat <game_id> Hola! Como estas?
```

**En Terminal 2 deberías ver:**

```
📥 Recibido: {'type': 'chat', 'player': 'testuser', 'message': 'Hola! Como estas?'}
```

### Escenario 4: Movimientos de Ajedrez

**Objetivo:** Probar que los movimientos se sincronizan entre jugadores.

**Prerequisito:** Partida activa con jugador de blancas conocido

**Jugador con blancas:**

```
Comando: move <game_id>
```

**Ambos jugadores deberían recibir:**

```
📥 Recibido: {
  'type': 'move', 
  'move': {
    'from_square': 'e2', 
    'to_square': 'e4', 
    'piece': 'P', 
    'san': 'e4',
    'fen': 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1'
  },
  'player': 'testuser',
  'current_turn': 'black',
  'game_status': 'active'
}
```

### Escenario 5: Manejo de Desconexiones

**Objetivo:** Verificar que el sistema maneja correctamente las desconexiones.

**Método:**

1. Iniciar partida entre dos jugadores (Escenario 2)
2. Cerrar abruptamente uno de los terminales (Ctrl+C)
3. En el otro terminal debería aparecer:

```
📥 Recibido: {'type': 'opponent_disconnected', 'message': 'testuser se ha desconectado'}
```

## 🐛 Debugging de Problemas Específicos

### Problema: Ping no recibe Pong

**Síntomas:**

```
📤 Enviado: {'type': 'ping'}
⏰ Timeout esperando mensaje (5.0s)
```

**Debugging:**

1. Verificar que el backend está ejecutándose:

```bash
curl http://localhost:8000/
```

2. Verificar logs del backend:

```bash
docker logs fastapi_backend -f
```

3. Probar con websocket_tester.html para ver si es problema del script

### Problema: Matchmaking no funciona

**Síntomas:**

```
📤 Enviado: {'type': 'find_match', 'elo': 1200}
⏰ Timeout esperando mensaje (5.0s)
```

**Debugging:**

1. Verificar que hay al menos dos usuarios conectados simultaneamente
2. Revisar logs del backend para errores en el matchmaking
3. Probar con `test_full_game.py` que automatiza este proceso

### Problema: Chat no llega al otro jugador

**Síntomas:**

- Un jugador envía chat pero el otro no lo recibe

**Debugging:**

1. Verificar que ambos jugadores están en la misma partida (mismo game_id)
2. Verificar que la partida está activa:

```bash
curl http://localhost:8000/active-games
```

3. Probar enviar desde el websocket_tester.html

## 📊 Interpretación de Logs

### Logs Normales del Backend (Docker)

**Login exitoso:**

```
INFO: Usuario testuser conectado
```

**Matchmaking exitoso:**

```
INFO: Match creado entre testuser y player2
INFO: Game ID: f659262a-3fb2-4593-8dfd-39212953582f
```

**Movimiento válido:**

```
INFO: Movimiento válido de testuser en game f659262a-3fb2-4593-8dfd-39212953582f
```

### Logs de Error Comunes

**Token inválido:**

```
WARNING: Token inválido para conexión WebSocket
```

**Jugador no encontrado:**

```
ERROR: Usuario no encontrado en base de datos
```

**Movimiento inválido:**

```
WARNING: Movimiento inválido de testuser: no es su turno
```

## 🎯 Tests Automatizados vs Manuales

### Usa Tests Automatizados Para

- ✅ Verificación rápida después de cambios de código
- ✅ Testing de regresión
- ✅ CI/CD pipelines
- ✅ Testing de carga básico

### Usa Tests Manuales Para

- ✅ Debugging de problemas específicos
- ✅ Testing de nuevas funcionalidades
- ✅ Validación de UX
- ✅ Testing exploratorio

## 🔧 Personalización de Tests

### Cambiar Timeouts

En cualquier script Python, modificar:

```python
# Para conexiones más lentas
WEBSOCKET_TIMEOUT = 10.0  # Default: 5.0

# Para testing de carga
MATCHMAKING_TIMEOUT = 30.0  # Default: 5.0
```

### Añadir Más Usuarios de Prueba

```bash
# Crear usuarios adicionales
for i in {3..10}; do
  curl -X POST "http://localhost:8000/registrar" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"player$i\", \"email\": \"player$i@example.com\", \"password\": \"password123\"}"
done
```

### Testing de Carga Simple

**Ejecutar múltiples instancias:**

```bash
# Terminal 1
python test_full_game.py

# Terminal 2  
python test_full_game.py

# Terminal 3
python test_full_game.py
```

Esto simulará múltiples partidas simultaneas.

---

**💡 Con estos ejemplos puedes probar exhaustivamente cualquier aspecto de tu sistema WebSocket de ajedrez.**
