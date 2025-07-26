#!/usr/bin/env python3
"""
Prueba completa de partida de ajedrez con dos jugadores
Simula una partida completa con matchmaking, movimientos y chat
"""

import asyncio
import websockets
import json
import requests
from typing import Optional

class GamePlayer:
    def __init__(self, email: str, password: str, name: str, base_url: str = "http://localhost:8000"):
        self.email = email
        self.password = password
        self.name = name
        self.base_url = base_url
        self.ws_url = base_url.replace("http", "ws")
        self.token = None
        self.websocket = None
        self.game_id = None
        self.color = None

    async def login(self) -> bool:
        """Login y obtener token"""
        try:
            response = requests.post(f"{self.base_url}/login", json={
                "email": self.email,
                "password": self.password
            })
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                print(f"✅ {self.name} - Login exitoso")
                return True
            else:
                print(f"❌ {self.name} - Error en login: {response.text}")
                return False
        except Exception as e:
            print(f"❌ {self.name} - Error de conexión: {e}")
            return False

    async def connect_websocket(self) -> bool:
        """Conectar al WebSocket"""
        try:
            uri = f"{self.ws_url}/ws/{self.token}"
            self.websocket = await websockets.connect(uri)
            print(f"✅ {self.name} - WebSocket conectado")
            return True
        except Exception as e:
            print(f"❌ {self.name} - Error conectando WebSocket: {e}")
            return False

    async def send_message(self, message: dict):
        """Enviar mensaje al WebSocket"""
        if self.websocket:
            await self.websocket.send(json.dumps(message))
            print(f"📤 {self.name} - Enviado: {message}")

    async def receive_message(self, timeout: float = 5.0) -> Optional[dict]:
        """Recibir mensaje del WebSocket"""
        try:
            message_text = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
            message = json.loads(message_text)
            print(f"📥 {self.name} - Recibido: {message}")
            
            # Procesar mensajes especiales
            if message.get("type") == "game_start":
                self.game_id = message.get("game_id")
                self.color = message.get("your_color")
                print(f"🎮 {self.name} - Juega como {self.color} en partida {self.game_id}")
            
            return message
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            print(f"❌ {self.name} - Error recibiendo mensaje: {e}")
            return None

    async def find_match(self):
        """Buscar partida"""
        await self.send_message({"type": "find_match", "elo": 1200})

    async def make_move(self, from_square: str, to_square: str, piece: str, san: str, fen: str):
        """Realizar un movimiento"""
        move_data = {
            "type": "move",
            "game_id": self.game_id,
            "move": {
                "from_square": from_square,
                "to_square": to_square,
                "piece": piece,
                "san": san,
                "fen": fen
            }
        }
        await self.send_message(move_data)

    async def send_chat(self, message: str):
        """Enviar mensaje de chat"""
        chat_data = {
            "type": "chat",
            "game_id": self.game_id,
            "message": message
        }
        await self.send_message(chat_data)

    async def close(self):
        """Cerrar conexión"""
        if self.websocket:
            await self.websocket.close()
            print(f"🔌 {self.name} - Desconectado")

async def test_full_game():
    """Prueba completa de partida entre dos jugadores"""
    print("🎯 === PRUEBA DE PARTIDA COMPLETA ===")
    
    # Crear jugadores
    player1 = GamePlayer("test@example.com", "password123", "Jugador1")
    player2 = GamePlayer("player2@example.com", "password123", "Jugador2")
    
    try:
        # 1. Login de ambos jugadores
        print("\n1️⃣ Login de jugadores...")
        if not await player1.login() or not await player2.login():
            return
        
        # 2. Conectar WebSockets
        print("\n2️⃣ Conectando WebSockets...")
        if not await player1.connect_websocket() or not await player2.connect_websocket():
            return
        
        # 3. Buscar partida
        print("\n3️⃣ Buscando partida...")
        await player1.find_match()
        await player2.find_match()
        
        # 4. Esperar inicio de partida
        print("\n4️⃣ Esperando inicio de partida...")
        game_start1 = await player1.receive_message()
        game_start2 = await player2.receive_message()
        
        if not game_start1 or not game_start2:
            print("❌ No se pudo iniciar la partida")
            return
        
        # 5. Simular movimientos
        print("\n5️⃣ Simulando movimientos...")
        
        # Jugador con blancas hace el primer movimiento
        white_player = player1 if player1.color == "white" else player2
        black_player = player2 if player1.color == "white" else player1
        
        print(f"🔵 {white_player.name} juega con blancas")
        
        # Movimiento de apertura: e4
        await white_player.make_move(
            "e2", "e4", "P", "e4",
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        )
        
        # Ambos jugadores reciben el movimiento
        move_response1 = await player1.receive_message(timeout=3.0)
        move_response2 = await player2.receive_message(timeout=3.0)
        
        if move_response1:
            print(f"✅ {player1.name} - Recibió el movimiento")
        if move_response2:
            print(f"✅ {player2.name} - Recibió el movimiento")
        
        # 6. Probar chat
        print("\n6️⃣ Probando chat...")
        await player1.send_chat("¡Buena partida!")
        
        chat_response = await player2.receive_message(timeout=3.0)
        if chat_response and chat_response.get("type") == "chat":
            print("✅ Chat funciona correctamente")
        
        print("\n🎉 === PRUEBA COMPLETA FINALIZADA ===")
        
    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
    finally:
        await player1.close()
        await player2.close()

if __name__ == "__main__":
    asyncio.run(test_full_game())
