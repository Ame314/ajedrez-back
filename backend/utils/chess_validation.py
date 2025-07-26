# /backend/utils/chess_validation.py
"""
Utilidades básicas para validación de movimientos de ajedrez.
Para una implementación completa, considera usar python-chess library.
"""

def is_valid_square(square: str) -> bool:
    """Verifica si una casilla es válida (a1-h8)"""
    if len(square) != 2:
        return False
    
    file = square[0].lower()
    rank = square[1]
    
    return file in 'abcdefgh' and rank in '12345678'

def is_valid_piece(piece: str) -> bool:
    """Verifica si una pieza es válida"""
    return piece.upper() in ['K', 'Q', 'R', 'B', 'N', 'P']

def validate_move_format(move_data: dict) -> bool:
    """Validación básica de formato de movimiento"""
    required_fields = ['from_square', 'to_square', 'piece', 'san', 'fen']
    
    for field in required_fields:
        if field not in move_data:
            return False
    
    if not is_valid_square(move_data['from_square']):
        return False
    
    if not is_valid_square(move_data['to_square']):
        return False
    
    if not is_valid_piece(move_data['piece']):
        return False
    
    return True

def validate_fen(fen: str) -> bool:
    """Validación básica de FEN"""
    # Una validación FEN completa es compleja, aquí una versión básica
    try:
        parts = fen.split(' ')
        if len(parts) != 6:
            return False
        
        # Verificar que la posición de las piezas tenga 8 filas
        rows = parts[0].split('/')
        if len(rows) != 8:
            return False
        
        return True
    except:
        return False

# FEN inicial estándar
STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
