#!/usr/bin/env python3
"""
Script de prueba para WebSockets del backend de ajedrez
Requiere: pip install websockets requests
"""

import asyncio
import websockets
import json
import requests
import sys
from typing import Optional

class ChessWebSocketTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.ws_url = base_url.replace("http", "ws")
        self.token = None
        self.websocket = None
        self.username = None

    async def login_user(self, email: str, password: str) -> bool:
        """Hacer login y obtener token"""
        try:
            response = requests.post(f"{self.base_url}/login", json={
                "email": email,
                "password": password
            })
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.username = email  # Guardar el email como identificador
                print(f"✅ Login exitoso para {email}")
                return True
            else:
                print(f"❌ Error en login: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            return False

    async def connect_websocket(self) -> bool:
        """Conectar al WebSocket"""
        if not self.token:
            print("❌ No hay token disponible")
            return False
        
        try:
            uri = f"{self.ws_url}/ws/{self.token}"
            self.websocket = await websockets.connect(uri)
            print(f"✅ Conectado al WebSocket: {uri}")
            return True
        except Exception as e:
            print(f"❌ Error conectando WebSocket: {e}")
            return False

    async def send_message(self, message: dict):
        """Enviar mensaje al WebSocket"""
        if not self.websocket:
            print("❌ WebSocket no conectado")
            return
        
        try:
            await self.websocket.send(json.dumps(message))
            print(f"📤 Enviado: {message}")
        except Exception as e:
            print(f"❌ Error enviando mensaje: {e}")

    async def listen_messages(self):
        """Escuchar mensajes del WebSocket"""
        if not self.websocket:
            print("❌ WebSocket no conectado")
            return
        
        try:
            async for message in self.websocket:
                data = json.loads(message)
                print(f"📥 Recibido: {data}")
        except websockets.exceptions.ConnectionClosed:
            print("🔌 Conexión WebSocket cerrada")
        except Exception as e:
            print(f"❌ Error escuchando mensajes: {e}")

    async def test_ping(self):
        """Probar ping/pong"""
        await self.send_message({"type": "ping"})

    async def test_find_match(self, elo: int = 1200):
        """Probar búsqueda de partida"""
        await self.send_message({
            "type": "find_match",
            "elo": elo
        })

    async def test_cancel_match(self):
        """Probar cancelar búsqueda"""
        await self.send_message({"type": "cancel_match"})

    async def test_move(self, game_id: str):
        """Probar movimiento"""
        await self.send_message({
            "type": "move",
            "game_id": game_id,
            "move": {
                "from_square": "e2",
                "to_square": "e4",
                "piece": "P",
                "san": "e4",
                "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
            }
        })

    async def test_chat(self, game_id: str, message: str):
        """Probar chat"""
        await self.send_message({
            "type": "chat",
            "game_id": game_id,
            "message": message
        })

    async def test_resign(self, game_id: str):
        """Probar rendición"""
        await self.send_message({
            "type": "game_action",
            "game_id": game_id,
            "action": "resign"
        })

    async def close(self):
        """Cerrar conexión"""
        if self.websocket:
            await self.websocket.close()
            print("🔌 Conexión cerrada")

async def interactive_test():
    """Modo interactivo para pruebas"""
    tester = ChessWebSocketTester()
    
    print("=== TESTER DE WEBSOCKETS AJEDREZ ===")
    print()
    
    # Login
    email = input("Email: ")
    password = input("Password: ")
    
    if not await tester.login_user(email, password):
        return
    
    # Conectar WebSocket
    if not await tester.connect_websocket():
        return
    
    # Crear tarea para escuchar mensajes
    listen_task = asyncio.create_task(tester.listen_messages())
    
    print("\nComandos disponibles:")
    print("1. ping - Probar ping")
    print("2. find - Buscar partida")
    print("3. cancel - Cancelar búsqueda")
    print("4. move <game_id> - Hacer movimiento")
    print("5. chat <game_id> <mensaje> - Enviar chat")
    print("6. resign <game_id> - Rendirse")
    print("7. quit - Salir")
    print()
    
    try:
        while True:
            command = input("Comando: ").strip().split()
            
            if not command:
                continue
            
            cmd = command[0].lower()
            
            if cmd == "quit":
                break
            elif cmd == "ping":
                await tester.test_ping()
            elif cmd == "find":
                await tester.test_find_match()
            elif cmd == "cancel":
                await tester.test_cancel_match()
            elif cmd == "move" and len(command) > 1:
                await tester.test_move(command[1])
            elif cmd == "chat" and len(command) > 2:
                game_id = command[1]
                message = " ".join(command[2:])
                await tester.test_chat(game_id, message)
            elif cmd == "resign" and len(command) > 1:
                await tester.test_resign(command[1])
            else:
                print("Comando no válido")
            
            # Pequeña pausa para ver respuestas
            await asyncio.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\n🛑 Interrumpido por usuario")
    finally:
        listen_task.cancel()
        await tester.close()

async def automated_test():
    """Prueba automatizada básica"""
    tester = ChessWebSocketTester()
    
    print("=== PRUEBA AUTOMATIZADA ===")
    
    # Necesitarías usuarios de prueba en tu BD
    if not await tester.login_user("test@example.com", "test_password"):
        print("❌ Crea un usuario de prueba primero")
        return
    
    if not await tester.connect_websocket():
        return
    
    # Escuchar en background
    listen_task = asyncio.create_task(tester.listen_messages())
    
    try:
        # Secuencia de pruebas
        print("🧪 Probando ping...")
        await tester.test_ping()
        await asyncio.sleep(1)
        
        print("🧪 Probando búsqueda de partida...")
        await tester.test_find_match()
        await asyncio.sleep(2)
        
        print("🧪 Probando cancelar búsqueda...")
        await tester.test_cancel_match()
        await asyncio.sleep(1)
        
        print("✅ Pruebas completadas")
        
    except Exception as e:
        print(f"❌ Error en pruebas: {e}")
    finally:
        listen_task.cancel()
        await tester.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "auto":
        asyncio.run(automated_test())
    else:
        asyncio.run(interactive_test())
