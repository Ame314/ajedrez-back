# /backend/routes/websockets.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from utils.websocket_manager import manager
from utils.auth import decode_token
import json

router = APIRouter()
security = HTTPBearer()

async def get_current_user_ws(token: str):
    """Función para autenticar usuario en WebSocket"""
    payload = decode_token(token)
    if payload is None:
        return None
    return payload.get("username")

@router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """Endpoint principal de WebSocket para conexiones de usuarios"""
    username = await get_current_user_ws(token)
    
    if not username:
        await websocket.close(code=4001, reason="Token inválido")
        return
    
    await manager.connect(websocket, username)
    
    try:
        while True:
            # Recibir mensaje del cliente
            data = await websocket.receive_text()
            message = json.loads(data)
            
            message_type = message.get("type")
            
            if message_type == "find_match":
                # Buscar partida
                user_elo = message.get("elo", 1200)
                await manager.add_to_matchmaking(username, user_elo)
                
            elif message_type == "cancel_match":
                # Cancelar búsqueda de partida
                if username in manager.matchmaking_queue:
                    manager.matchmaking_queue.remove(username)
                await manager.send_personal_message({
                    "type": "match_cancelled"
                }, username)
                
            elif message_type == "move":
                # Realizar movimiento
                game_id = message.get("game_id")
                move_data = message.get("move")
                
                if game_id and move_data:
                    await manager.handle_move(game_id, move_data, username)
                
            elif message_type == "game_action":
                # Acciones del juego (resignar, ofrecer tablas, etc.)
                game_id = message.get("game_id")
                action = message.get("action")
                
                if game_id and action:
                    await manager.handle_game_action(game_id, action, username)
                
            elif message_type == "chat":
                # Mensaje de chat en la partida
                game_id = message.get("game_id")
                chat_message = message.get("message")
                
                if game_id and chat_message:
                    await manager.send_game_message({
                        "type": "chat",
                        "player": username,
                        "message": chat_message
                    }, game_id)
                
            elif message_type == "ping":
                # Ping para mantener conexión
                await manager.send_personal_message({
                    "type": "pong"
                }, username)
                
    except WebSocketDisconnect:
        manager.disconnect(username)
    except Exception as e:
        print(f"Error en WebSocket para {username}: {e}")
        manager.disconnect(username)

@router.get("/active-games")
async def get_active_games(request: Request):
    """Obtener lista de partidas activas"""
    games = []
    for game_id, game_data in manager.active_games.items():
        games.append({
            "game_id": game_id,
            "white_player": game_data["white_player"],
            "black_player": game_data["black_player"],
            "status": game_data["status"],
            "moves_count": len(game_data["moves"])
        })
    return {"active_games": games}

@router.get("/game/{game_id}")
async def get_game_details(game_id: str, request: Request):
    """Obtener detalles de una partida específica"""
    if game_id not in manager.active_games:
        raise HTTPException(status_code=404, detail="Partida no encontrada")
    
    return manager.active_games[game_id]

@router.post("/create-private-game")
async def create_private_game(
    request: Request,
    opponent_username: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Crear una partida privada con un oponente específico"""
    db = request.app.state.db
    
    # Verificar token
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    username = payload["username"]
    
    # Verificar que el oponente existe y está conectado
    if opponent_username not in manager.active_connections:
        raise HTTPException(status_code=400, detail="Oponente no está conectado")
    
    # Obtener ELOs de la base de datos
    user = await db.users.find_one({"username": username})
    opponent = await db.users.find_one({"username": opponent_username})
    
    if not user or not opponent:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Crear la partida
    import random
    if random.choice([True, False]):
        white_player, black_player = username, opponent_username
        white_elo, black_elo = user["elo"], opponent["elo"]
    else:
        white_player, black_player = opponent_username, username
        white_elo, black_elo = opponent["elo"], user["elo"]
    
    game_id = manager.create_game(white_player, black_player, white_elo, black_elo)
    
    # Notificar a ambos jugadores
    game_start_message = {
        "type": "game_start",
        "game_id": game_id,
        "white_player": white_player,
        "black_player": black_player,
        "is_private": True
    }
    
    await manager.send_personal_message({
        **game_start_message, 
        "your_color": "white" if white_player == username else "black"
    }, username)
    
    await manager.send_personal_message({
        **game_start_message,
        "your_color": "white" if white_player == opponent_username else "black"
    }, opponent_username)
    
    return {"message": "Partida privada creada", "game_id": game_id}
