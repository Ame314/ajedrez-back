# /backend/utils/websocket_manager.py
from fastapi import WebSocket
from typing import Dict, List, Set
import json
import uuid
import random
from datetime import datetime
from models.live_game import LiveGame, GameMessage
from utils.chess_validation import validate_move_format, STARTING_FEN

class ConnectionManager:
    def __init__(self):
        # Conexiones activas por usuario
        self.active_connections: Dict[str, WebSocket] = {}
        # Salas de juego activas {game_id: {players, game_data}}
        self.active_games: Dict[str, Dict] = {}
        # Cola de jugadores buscando partida
        self.matchmaking_queue: List[str] = []
        # Mapping de usuario a game_id
        self.user_to_game: Dict[str, str] = {}

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        
        # Si el usuario ya estaba conectado, cerrar la conexión anterior
        if username in self.active_connections:
            try:
                old_ws = self.active_connections[username]
                await old_ws.close(code=4000, reason="Nueva conexión establecida")
            except:
                pass
        
        self.active_connections[username] = websocket
        print(f"Usuario {username} conectado. Conexiones activas: {len(self.active_connections)}")
        
        # Enviar confirmación de conexión
        await self.send_personal_message({
            "type": "connection_confirmed",
            "username": username,
            "timestamp": datetime.utcnow().isoformat()
        }, username)

    async def disconnect(self, username: str):
        print(f"Desconectando usuario: {username}")
        
        if username in self.active_connections:
            try:
                await self.active_connections[username].close()
            except:
                pass
            del self.active_connections[username]
        
        # Remover de cola de matchmaking si está
        if username in self.matchmaking_queue:
            self.matchmaking_queue.remove(username)
            print(f"Usuario {username} removido de cola de matchmaking")
        
        # Si está en una partida, notificar al oponente
        if username in self.user_to_game:
            game_id = self.user_to_game[username]
            if game_id in self.active_games:
                game = self.active_games[game_id]
                opponent = None
                if game["white_player"] == username:
                    opponent = game["black_player"]
                elif game["black_player"] == username:
                    opponent = game["white_player"]
                
                if opponent and opponent in self.active_connections:
                    await self.send_personal_message({
                        "type": "opponent_disconnected",
                        "message": f"{username} se ha desconectado"
                    }, opponent)
                
                # Pausar la partida
                game["status"] = "paused"
            
            del self.user_to_game[username]
        
        print(f"Usuario {username} desconectado. Conexiones restantes: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, username: str):
        if username in self.active_connections:
            try:
                await self.active_connections[username].send_text(json.dumps(message))
                print(f"Mensaje enviado a {username}: {message.get('type', 'unknown')}")
                return True
            except Exception as e:
                print(f"Error enviando mensaje a {username}: {e}")
                # Conexión cerrada, limpiar
                await self.disconnect(username)
                return False
        else:
            print(f"Usuario {username} no está conectado")
            return False

    async def send_game_message(self, message: dict, game_id: str):
        """Envía un mensaje a todos los jugadores de una partida específica"""
        if game_id in self.active_games:
            game = self.active_games[game_id]
            players = [game["white_player"], game["black_player"]]
            
            sent_count = 0
            for player in players:
                if await self.send_personal_message(message, player):
                    sent_count += 1
            
            return sent_count == len(players)
        return False

    def create_game(self, white_player: str, black_player: str, white_elo: int, black_elo: int) -> str:
        """Crea una nueva partida"""
        game_id = str(uuid.uuid4())
        
        game_data = {
            "game_id": game_id,
            "white_player": white_player,
            "black_player": black_player,
            "white_elo": white_elo,
            "black_elo": black_elo,
            "current_turn": "white",
            "moves": [],
            "status": "active",
            "result": "*",
            "winner": None,
            "time_control": {"white_time": 600, "black_time": 600},
            "current_fen": STARTING_FEN,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        self.active_games[game_id] = game_data
        self.user_to_game[white_player] = game_id
        self.user_to_game[black_player] = game_id
        
        print(f"Partida creada: {game_id} entre {white_player} (blancas) y {black_player} (negras)")
        return game_id

    async def add_to_matchmaking(self, username: str, user_elo: int):
        """Añade un jugador a la cola de matchmaking"""
        print(f"Añadiendo {username} (ELO: {user_elo}) a la cola de matchmaking")
        
        # Verificar que el usuario está conectado
        if username not in self.active_connections:
            print(f"Error: {username} no está conectado")
            return
        
        # Verificar que no está ya en una partida
        if username in self.user_to_game:
            print(f"Error: {username} ya está en una partida")
            await self.send_personal_message({
                "type": "error",
                "message": "Ya estás en una partida activa"
            }, username)
            return
        
        # Añadir a la cola si no está ya
        if username not in self.matchmaking_queue:
            self.matchmaking_queue.append(username)
            print(f"Cola de matchmaking actualizada: {self.matchmaking_queue}")
            
            # Buscar oponente inmediatamente
            await self.process_matchmaking(username, user_elo)
        else:
            print(f"{username} ya está en la cola de matchmaking")

    async def process_matchmaking(self, username: str, user_elo: int):
        """Procesa la cola de matchmaking para encontrar oponentes"""
        opponent = None
        
        # Buscar oponente en la cola
        for potential_opponent in self.matchmaking_queue:
            if (potential_opponent != username and 
                potential_opponent in self.active_connections and
                potential_opponent not in self.user_to_game):
                opponent = potential_opponent
                break
        
        if opponent:
            print(f"Oponente encontrado: {opponent} para {username}")
            await self.create_match(username, opponent, user_elo)
        else:
            print(f"No se encontró oponente para {username}. Esperando...")
            await self.send_personal_message({
                "type": "searching_match",
                "message": "Buscando oponente..."
            }, username)

    async def create_match(self, player1: str, player2: str, player1_elo: int, player2_elo: int = 1200):
        """Crea una partida entre dos jugadores"""
        print(f"Intentando crear partida entre {player1} y {player2}")
        
        # Verificar que ambos jugadores siguen conectados y disponibles
        if not self.verify_players_available([player1, player2]):
            print("Error: No se puede crear la partida - jugadores no disponibles")
            return False
        
        # Remover de la cola
        if player1 in self.matchmaking_queue:
            self.matchmaking_queue.remove(player1)
        if player2 in self.matchmaking_queue:
            self.matchmaking_queue.remove(player2)
        
        # Determinar colores aleatoriamente
        if random.choice([True, False]):
            white_player, black_player = player1, player2
            white_elo, black_elo = player1_elo, player2_elo
        else:
            white_player, black_player = player2, player1
            white_elo, black_elo = player2_elo, player1_elo
        
        game_id = self.create_game(white_player, black_player, white_elo, black_elo)
        
        # Notificar a ambos jugadores
        success = await self.notify_game_start(game_id, white_player, black_player, white_elo, black_elo)
        
        if not success:
            print("Error notificando a los jugadores. Cancelando partida.")
            await self.cancel_game(game_id)
            return False
        
        print(f"Partida {game_id} creada exitosamente")
        return True

    def verify_players_available(self, players: List[str]) -> bool:
        """Verifica que todos los jugadores estén conectados y disponibles"""
        for player in players:
            if (player not in self.active_connections or 
                player in self.user_to_game):
                print(f"Jugador {player} no disponible")
                return False
        return True

    async def notify_game_start(self, game_id: str, white_player: str, black_player: str, 
                               white_elo: int, black_elo: int) -> bool:
        """Notifica a ambos jugadores el inicio de la partida"""
        
        white_message = {
            "type": "game_start",
            "game_id": game_id,
            "white_player": white_player,
            "black_player": black_player,
            "your_color": "white",
            "opponent": black_player,
            "opponent_elo": black_elo
        }
        
        black_message = {
            "type": "game_start",
            "game_id": game_id,
            "white_player": white_player,
            "black_player": black_player,
            "your_color": "black",
            "opponent": white_player,
            "opponent_elo": white_elo
        }
        
        # Enviar mensajes y verificar que lleguen
        white_sent = await self.send_personal_message(white_message, white_player)
        black_sent = await self.send_personal_message(black_message, black_player)
        
        if white_sent and black_sent:
            print(f"Ambos jugadores notificados correctamente para partida {game_id}")
            return True
        else:
            print(f"Error notificando jugadores: white_sent={white_sent}, black_sent={black_sent}")
            return False

    async def cancel_game(self, game_id: str):
        """Cancela una partida y limpia los datos"""
        if game_id in self.active_games:
            game = self.active_games[game_id]
            
            # Limpiar mapeos de usuarios
            for player in [game["white_player"], game["black_player"]]:
                if player in self.user_to_game:
                    del self.user_to_game[player]
                # Volver a agregar a cola de matchmaking si están conectados
                if (player in self.active_connections and 
                    player not in self.matchmaking_queue):
                    self.matchmaking_queue.append(player)
            
            del self.active_games[game_id]
            print(f"Partida {game_id} cancelada")

    async def handle_move(self, game_id: str, move_data: dict, player: str) -> bool:
        """Procesa un movimiento en una partida"""
        if game_id not in self.active_games:
            print(f"Error: Partida {game_id} no encontrada")
            return False
        
        game = self.active_games[game_id]
        
        # Verificar que es el turno del jugador
        current_turn = game["current_turn"]
        if ((current_turn == "white" and player != game["white_player"]) or
            (current_turn == "black" and player != game["black_player"])):
            print(f"Error: No es el turno de {player}")
            return False
        
        # Validar formato del movimiento
        if not validate_move_format(move_data):
            print(f"Error: Formato de movimiento inválido: {move_data}")
            return False
        
        # Actualizar estado del juego
        game["moves"].append(move_data)
        game["current_fen"] = move_data.get("fen", game["current_fen"])
        game["current_turn"] = "black" if current_turn == "white" else "white"
        game["updated_at"] = datetime.utcnow()
        
        # Notificar el movimiento a ambos jugadores
        move_message = {
            "type": "move",
            "game_id": game_id,
            "move": move_data,
            "current_turn": game["current_turn"],
            "move_number": len(game["moves"])
        }
        
        success = await self.send_game_message(move_message, game_id)
        
        if success:
            print(f"Movimiento procesado exitosamente en partida {game_id}")
            return True
        else:
            print(f"Error enviando movimiento en partida {game_id}")
            return False

    async def handle_game_action(self, game_id: str, action: str, player: str):
        """Maneja acciones del juego como resignar, ofrecer tablas, etc."""
        if game_id not in self.active_games:
            return
        
        game = self.active_games[game_id]
        
        if action == "resign":
            # El jugador se rinde
            game["status"] = "finished"
            if player == game["white_player"]:
                game["result"] = "0-1"
                game["winner"] = game["black_player"]
            else:
                game["result"] = "1-0"
                game["winner"] = game["white_player"]
            
            await self.send_game_message({
                "type": "game_end",
                "result": game["result"],
                "winner": game["winner"],
                "reason": "resignation",
                "resigned_by": player
            }, game_id)
            
            # Limpiar mapeos
            del self.user_to_game[game["white_player"]]
            del self.user_to_game[game["black_player"]]
        
        elif action == "draw_offer":
            # Ofrecer tablas
            opponent = game["black_player"] if player == game["white_player"] else game["white_player"]
            await self.send_personal_message({
                "type": "draw_offer",
                "from": player,
                "game_id": game_id
            }, opponent)
            
        elif action == "accept_draw":
            # Aceptar tablas
            game["status"] = "finished"
            game["result"] = "1/2-1/2"
            game["winner"] = "draw"
            
            await self.send_game_message({
                "type": "game_end",
                "result": game["result"],
                "winner": "draw",
                "reason": "mutual_agreement"
            }, game_id)
            
            # Limpiar mapeos
            del self.user_to_game[game["white_player"]]
            del self.user_to_game[game["black_player"]]
            
        elif action == "decline_draw":
            # Rechazar tablas
            opponent = game["black_player"] if player == game["white_player"] else game["white_player"]
            await self.send_personal_message({
                "type": "draw_declined",
                "from": player,
                "game_id": game_id
            }, opponent)

    async def handle_chat_message(self, game_id: str, message: str, player: str):
        """Maneja mensajes de chat en una partida"""
        if game_id not in self.active_games:
            return
        
        game = self.active_games[game_id]
        
        # Verificar que el jugador está en la partida
        if player not in [game["white_player"], game["black_player"]]:
            return
        
        # Enviar mensaje a ambos jugadores
        chat_message = {
            "type": "chat_message",
            "game_id": game_id,
            "player": player,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.send_game_message(chat_message, game_id)

# Instancia global del manager
manager = ConnectionManager()
