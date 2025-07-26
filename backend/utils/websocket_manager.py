# /backend/utils/websocket_manager.py
from fastapi import WebSocket
from typing import Dict, List, Set
import json
import uuid
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
        self.active_connections[username] = websocket
        print(f"Usuario {username} conectado")

    def disconnect(self, username: str):
        if username in self.active_connections:
            del self.active_connections[username]
        
        # Remover de cola de matchmaking si está
        if username in self.matchmaking_queue:
            self.matchmaking_queue.remove(username)
        
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
                    self.send_personal_message({
                        "type": "opponent_disconnected",
                        "message": f"{username} se ha desconectado"
                    }, opponent)
                
                # Pausar o terminar la partida
                game["status"] = "paused"
            
            del self.user_to_game[username]
        
        print(f"Usuario {username} desconectado")

    async def send_personal_message(self, message: dict, username: str):
        if username in self.active_connections:
            try:
                await self.active_connections[username].send_text(json.dumps(message))
            except:
                # Conexión cerrada, limpiar
                self.disconnect(username)

    async def send_game_message(self, message: dict, game_id: str):
        """Envía un mensaje a todos los jugadores de una partida específica"""
        if game_id in self.active_games:
            game = self.active_games[game_id]
            players = [game["white_player"], game["black_player"]]
            
            for player in players:
                await self.send_personal_message(message, player)

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
        
        return game_id

    async def add_to_matchmaking(self, username: str, user_elo: int):
        """Añade un jugador a la cola de matchmaking"""
        if username not in self.matchmaking_queue:
            self.matchmaking_queue.append(username)
            
            # Buscar oponente
            opponent = self.find_opponent(username, user_elo)
            if opponent:
                await self.create_match(username, opponent, user_elo)

    def find_opponent(self, username: str, user_elo: int):
        """Encuentra un oponente adecuado basado en ELO"""
        elo_range = 200  # Rango de ELO aceptable
        
        for potential_opponent in self.matchmaking_queue:
            if potential_opponent != username:
                # Aquí deberías obtener el ELO del oponente desde la base de datos
                # Por simplicidad, asumimos que está disponible
                return potential_opponent
        
        return None

    async def create_match(self, player1: str, player2: str, player1_elo: int, player2_elo: int = 1200):
        """Crea una partida entre dos jugadores"""
        # Remover de la cola
        if player1 in self.matchmaking_queue:
            self.matchmaking_queue.remove(player1)
        if player2 in self.matchmaking_queue:
            self.matchmaking_queue.remove(player2)
        
        # Determinar colores aleatoriamente
        import random
        if random.choice([True, False]):
            white_player, black_player = player1, player2
            white_elo, black_elo = player1_elo, player2_elo
        else:
            white_player, black_player = player2, player1
            white_elo, black_elo = player2_elo, player1_elo
        
        game_id = self.create_game(white_player, black_player, white_elo, black_elo)
        
        # Notificar a ambos jugadores
        game_start_message = {
            "type": "game_start",
            "game_id": game_id,
            "white_player": white_player,
            "black_player": black_player,
            "your_color": "white" if white_player == player1 else "black"
        }
        
        await self.send_personal_message({**game_start_message, "your_color": "white"}, white_player)
        await self.send_personal_message({**game_start_message, "your_color": "black"}, black_player)

    async def handle_move(self, game_id: str, move_data: dict, player: str):
        """Procesa un movimiento en una partida"""
        if game_id not in self.active_games:
            return False
        
        game = self.active_games[game_id]
        
        # Verificar que es el turno del jugador
        current_color = game["current_turn"]
        if (current_color == "white" and player != game["white_player"]) or \
           (current_color == "black" and player != game["black_player"]):
            await self.send_personal_message({
                "type": "error",
                "message": "No es tu turno"
            }, player)
            return False
        
        # Validar formato del movimiento
        if not validate_move_format(move_data):
            await self.send_personal_message({
                "type": "error",
                "message": "Formato de movimiento inválido"
            }, player)
            return False
        
        # Agregar el movimiento
        game["moves"].append(move_data)
        game["current_turn"] = "black" if current_color == "white" else "white"
        game["current_fen"] = move_data.get("fen", game["current_fen"])
        game["updated_at"] = datetime.utcnow()
        
        # Verificar si la partida terminó
        if "checkmate" in move_data.get("san", "").lower() or "mate" in move_data.get("san", "").lower():
            game["status"] = "finished"
            if current_color == "white":
                game["result"] = "1-0"
                game["winner"] = game["white_player"]
            else:
                game["result"] = "0-1"
                game["winner"] = game["black_player"]
        
        # Enviar movimiento a ambos jugadores
        move_message = {
            "type": "move",
            "move": move_data,
            "player": player,
            "current_turn": game["current_turn"],
            "game_status": game["status"]
        }
        
        if game["status"] == "finished":
            move_message["result"] = game["result"]
            move_message["winner"] = game["winner"]
        
        await self.send_game_message(move_message, game_id)
        return True

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
                "reason": "resignation"
            }, game_id)
        
        elif action == "offer_draw":
            # Ofrecer tablas
            opponent = game["black_player"] if player == game["white_player"] else game["white_player"]
            await self.send_personal_message({
                "type": "draw_offer",
                "from": player
            }, opponent)

# Instancia global del manager
manager = ConnectionManager()
