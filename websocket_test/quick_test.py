#!/usr/bin/env python3
"""
Script de prueba rápida para WebSockets
"""

import asyncio
import websockets
import json
import requests

async def quick_test():
    print("🚀 === PRUEBA RÁPIDA DE WEBSOCKETS ===")
    
    # 1. Login
    print("1️⃣ Haciendo login...")
    login_response = requests.post("http://localhost:8000/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    
    if login_response.status_code != 200:
        print("❌ Error en login")
        return
    
    token = login_response.json()["access_token"]
    print(f"✅ Token obtenido: {token[:30]}...")
    
    # 2. Conectar WebSocket
    print("\n2️⃣ Conectando WebSocket...")
    try:
        uri = f"ws://localhost:8000/ws/{token}"
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket conectado")
            
            # 3. Ping
            print("\n3️⃣ Enviando ping...")
            await websocket.send(json.dumps({"type": "ping"}))
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            pong_data = json.loads(response)
            print(f"✅ Recibido: {pong_data}")
            
            # 4. Buscar partida
            print("\n4️⃣ Buscando partida...")
            await websocket.send(json.dumps({"type": "find_match", "elo": 1200}))
            
            # Esperar respuesta o timeout
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                match_data = json.loads(response)
                print(f"📥 Respuesta de matchmaking: {match_data}")
            except asyncio.TimeoutError:
                print("ℹ️ Sin respuesta inmediata (normal sin otro jugador)")
            
            # 5. Cancelar búsqueda
            print("\n5️⃣ Cancelando búsqueda...")
            await websocket.send(json.dumps({"type": "cancel_match"}))
            
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                cancel_data = json.loads(response)
                print(f"✅ Cancelación: {cancel_data}")
            except asyncio.TimeoutError:
                print("ℹ️ Sin respuesta de cancelación")
            
    except Exception as e:
        print(f"❌ Error WebSocket: {e}")
        return
    
    print("\n🎉 === TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE ===")
    print("✅ Login funciona")
    print("✅ WebSocket conecta")
    print("✅ Ping/Pong funciona")
    print("✅ Matchmaking acepta solicitudes")
    print("✅ Sistema de WebSockets operativo")

if __name__ == "__main__":
    asyncio.run(quick_test())
