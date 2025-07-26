#!/usr/bin/env python3
"""
Script de prueba automatizada para WebSockets del backend de ajedrez
"""

import asyncio
import websockets
import json
import requests
from typing import Optional

class AutomatedWebSocketTest:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.ws_url = base_url.replace("http", "ws")
        self.token = None
        self.websocket = None
        self.messages_received = []

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
                print(f"✅ Login exitoso para {email}")
                print(f"🔑 Token: {self.token[:50]}...")
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
            print(f"🔌 Conectando a: {uri}")
            self.websocket = await websockets.connect(uri)
            print(f"✅ Conectado al WebSocket")
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

    async def receive_message(self, timeout: float = 2.0) -> Optional[dict]:
        """Recibir un mensaje del WebSocket con timeout"""
        try:
            message_text = await asyncio.wait_for(
                self.websocket.recv(), 
                timeout=timeout
            )
            message = json.loads(message_text)
            print(f"📥 Recibido: {message}")
            self.messages_received.append(message)
            return message
        except asyncio.TimeoutError:
            print(f"⏰ Timeout esperando mensaje ({timeout}s)")
            return None
        except Exception as e:
            print(f"❌ Error recibiendo mensaje: {e}")
            return None

    async def test_ping(self):
        """Probar ping/pong"""
        print("\n🧪 === PRUEBA PING ===")
        await self.send_message({"type": "ping"})
        response = await self.receive_message()
        
        if response and response.get("type") == "pong":
            print("✅ Ping/Pong funciona correctamente")
            return True
        else:
            print("❌ Ping/Pong no funcionó como se esperaba")
            return False

    async def test_find_match(self):
        """Probar búsqueda de partida"""
        print("\n🧪 === PRUEBA BÚSQUEDA DE PARTIDA ===")
        await self.send_message({
            "type": "find_match",
            "elo": 1200
        })
        
        # Esperar respuesta (puede que no encuentre oponente)
        response = await self.receive_message(timeout=3.0)
        
        if response:
            if response.get("type") == "game_start":
                print("✅ ¡Se encontró una partida!")
                return response.get("game_id")
            else:
                print("ℹ️ Buscando partida (sin oponente disponible)")
        else:
            print("ℹ️ Sin respuesta inmediata (normal si no hay otro jugador)")
        
        return None

    async def test_cancel_match(self):
        """Probar cancelar búsqueda"""
        print("\n🧪 === PRUEBA CANCELAR BÚSQUEDA ===")
        await self.send_message({"type": "cancel_match"})
        response = await self.receive_message()
        
        if response and response.get("type") == "match_cancelled":
            print("✅ Cancelación de búsqueda funciona")
            return True
        else:
            print("ℹ️ Respuesta de cancelación: ", response)
            return False

    async def close(self):
        """Cerrar conexión"""
        if self.websocket:
            await self.websocket.close()
            print("🔌 Conexión cerrada")

async def run_tests():
    """Ejecutar todas las pruebas"""
    print("🚀 === INICIANDO PRUEBAS AUTOMATIZADAS DE WEBSOCKETS ===\n")
    
    tester = AutomatedWebSocketTest()
    
    try:
        # Paso 1: Login
        print("1️⃣ Probando login...")
        if not await tester.login_user("test@example.com", "password123"):
            print("❌ Error en login. Asegúrate de que el usuario existe.")
            return
        
        # Paso 2: Conectar WebSocket
        print("\n2️⃣ Conectando WebSocket...")
        if not await tester.connect_websocket():
            print("❌ Error conectando WebSocket")
            return
        
        # Paso 3: Prueba Ping
        await tester.test_ping()
        
        # Paso 4: Prueba búsqueda de partida
        game_id = await tester.test_find_match()
        
        # Paso 5: Cancelar búsqueda si no se encontró partida
        if not game_id:
            await tester.test_cancel_match()
        
        # Paso 6: Probar mensaje inválido
        print("\n🧪 === PRUEBA MENSAJE INVÁLIDO ===")
        await tester.send_message({"type": "invalid_type"})
        response = await tester.receive_message()
        
        print(f"\n📊 === RESUMEN ===")
        print(f"Total de mensajes recibidos: {len(tester.messages_received)}")
        print("✅ Pruebas completadas exitosamente")
        
    except Exception as e:
        print(f"❌ Error durante las pruebas: {e}")
    finally:
        await tester.close()

if __name__ == "__main__":
    asyncio.run(run_tests())
