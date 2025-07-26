#!/usr/bin/env python3
"""
Script para simular dos jugadores y probar una partida completa
"""

import asyncio
import websockets
import json
import requests

class Player:
    def __init__(self, email, password, name):
        self.email = email
        self.password = password
        self.name = name
        self.token = None
        self.websocket = None
        self.game_id = None
        self.color = None

    async def login(self):
        """Hacer login y obtener token"""
        response = requests.post("http://localhost:8000/login", json={
            "email": self.email,
            "password": self.password
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            print(f"✅ {self.name} - Login exitoso")
            return True
        else:
            print(f"❌ {self.name} - Error en login: {response.text}")
            return False

    async def connect(self):
        """Conectar al WebSocket"""
        try:
            uri = f"ws://localhost:8000/ws/{self.token}"
            self.websocket = await websockets.connect(uri)
            print(f"✅ {self.name} - WebSocket conectado")
            return True
        except Exception as e:
            print(f"❌ {self.name} - Error conectando: {e}")
            return False

    async def send(self, message):
        """Enviar mensaje"""
        await self.websocket.send(json.dumps(message))
        print(f"📤 {self.name} - Enviado: {message}")

    async def receive(self, timeout=5.0):
        """Recibir mensaje"""
        try:
            response = await asyncio.wait_for(self.websocket.recv(), timeout=timeout)
            data = json.loads(response)
            print(f"📥 {self.name} - Recibido: {data}")
            
            # Guardar información de la partida
            if data.get("type") == "game_start":
                self.game_id = data.get("game_id")
                self.color = data.get("your_color")
                print(f"🎮 {self.name} - Juega como {self.color} en partida {self.game_id}")
            
            return data
        except asyncio.TimeoutError:
            print(f"⏰ {self.name} - Timeout")
            return None

    async def find_match(self):
        """Buscar partida"""
        await self.send({"type": "find_match", "elo": 1200})

    async def make_move(self, move_data):
        """Hacer un movimiento"""
        await self.send({
            "type": "move",
            "game_id": self.game_id,
            "move": move_data
        })

    async def disconnect(self):
        """Desconectar"""
        if self.websocket:
            await self.websocket.close()
            print(f"🔌 {self.name} - Desconectado")

async def test_full_game():
    """Probar una partida completa con dos jugadores"""
    print("🎯 === PRUEBA DE PARTIDA COMPLETA ===\n")
    
    # Crear jugadores
    player1 = Player("test@example.com", "password123", "Jugador1")
    player2 = Player("player2@example.com", "password123", "Jugador2")
    
    try:
        # 1. Login de ambos jugadores
        print("1️⃣ Login de jugadores...")
        if not await player1.login() or not await player2.login():
            return
        
        # 2. Conectar WebSockets
        print("\n2️⃣ Conectando WebSockets...")
        if not await player1.connect() or not await player2.connect():
            return
        
        # 3. Ambos buscan partida
        print("\n3️⃣ Buscando partida...")
        await player1.find_match()
        await asyncio.sleep(0.5)  # Pequeña pausa
        await player2.find_match()
        
        # 4. Esperar que se inicie la partida
        print("\n4️⃣ Esperando inicio de partida...")
        
        # Recibir respuestas de game_start
        game_start_tasks = [
            player1.receive(timeout=10.0),
            player2.receive(timeout=10.0)
        ]
        
        results = await asyncio.gather(*game_start_tasks, return_exceptions=True)
        
        # Verificar que ambos recibieron game_start
        game_started = False
        for i, result in enumerate(results):
            player = [player1, player2][i]
            if isinstance(result, dict) and result.get("type") == "game_start":
                game_started = True
            elif result is None:
                print(f"⚠️ {player.name} - No recibió game_start")
        
        if game_started:
            print("🎮 ¡Partida iniciada exitosamente!")
            
            # 5. Simular un movimiento
            print("\n5️⃣ Simulando movimiento...")
            
            # Encontrar quién juega con blancas
            white_player = player1 if player1.color == "white" else player2
            black_player = player2 if white_player == player1 else player1
            
            print(f"🟨 {white_player.name} juega con blancas")
            print(f"⬛ {black_player.name} juega con negras")
            
            # Movimiento de prueba: e2-e4
            test_move = {
                "from_square": "e2",
                "to_square": "e4",
                "piece": "P",
                "san": "e4",
                "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
            }
            
            await white_player.make_move(test_move)
            
            # Esperar que ambos reciban el movimiento
            move_tasks = [
                white_player.receive(timeout=5.0),
                black_player.receive(timeout=5.0)
            ]
            
            move_results = await asyncio.gather(*move_tasks, return_exceptions=True)
            
            for i, result in enumerate(move_results):
                player = [white_player, black_player][i]
                if isinstance(result, dict) and result.get("type") == "move":
                    print(f"✅ {player.name} - Recibió el movimiento")
                else:
                    print(f"⚠️ {player.name} - No recibió el movimiento: {result}")
            
        else:
            print("❌ No se pudo iniciar la partida")
        
        # 6. Prueba de chat
        print("\n6️⃣ Probando chat...")
        if player1.game_id:
            await player1.send({
                "type": "chat",
                "game_id": player1.game_id,
                "message": "¡Buena partida!"
            })
            
            # Esperar mensaje de chat
            chat_response = await player2.receive(timeout=3.0)
            if chat_response and chat_response.get("type") == "chat":
                print("✅ Chat funciona correctamente")
        
        print("\n🎉 === PRUEBA COMPLETA FINALIZADA ===")
        
    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
    finally:
        # Desconectar ambos jugadores
        await player1.disconnect()
        await player2.disconnect()

if __name__ == "__main__":
    asyncio.run(test_full_game())
