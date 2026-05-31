from bitboard import KING_ATTACKS, KNIGHT_ATTACKS, square_bb
from pieces import Color, Piece, PieceKind, Square
from position import Position

_BISHOP_DELTAS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
_ROOK_DELTAS = ((0, 1), (0, -1), (1, 0), (-1, 0))
_RAY_DELTAS = _BISHOP_DELTAS + _ROOK_DELTAS


def pawn_attacks_bb(square: Square, color: Color) -> int:
    """Return capture squares attacked by a pawn on ``square``."""
    attacks = 0
    forward = 8 if color == Color.WHITE else -8
    for capture_offset in (-1, 1):
        capture_file = square.file + capture_offset
        if capture_file < 0 or capture_file > 7:
            continue
        capture_square = Square(square + forward + capture_offset)
        attacks |= square_bb(capture_square)
    return attacks


def sliding_attacks_bb(
    square: Square, occupied: int, deltas: tuple[tuple[int, int], ...]
) -> int:
    """Ray attacks from ``square`` blocked by the first piece on each ray."""
    attacks = 0
    for delta_file, delta_rank in deltas:
        file = square.file + delta_file
        rank = square.rank + delta_rank
        while 0 <= file < 8 and 0 <= rank < 8:
            destination = Square(rank * 8 + file)
            attacks |= square_bb(destination)
            if occupied & square_bb(destination):
                break
            file += delta_file
            rank += delta_rank
    return attacks


def piece_attacks_bb(square: Square, piece: Piece, occupied: int) -> int:
    """Return squares attacked by ``piece`` on ``square``."""
    match piece.kind:
        case PieceKind.PAWN:
            return pawn_attacks_bb(square, piece.color)
        case PieceKind.KNIGHT:
            return KNIGHT_ATTACKS[square]
        case PieceKind.BISHOP:
            return sliding_attacks_bb(square, occupied, _BISHOP_DELTAS)
        case PieceKind.ROOK:
            return sliding_attacks_bb(square, occupied, _ROOK_DELTAS)
        case PieceKind.QUEEN:
            return sliding_attacks_bb(square, occupied, _RAY_DELTAS)
        case PieceKind.KING:
            return KING_ATTACKS[square]


def attackers_to_square(
    position: Position, square: Square, attacker_color: Color, occupied: int
) -> int:
    """Return a bitboard of ``attacker_color`` pieces that attack ``square``."""
    attackers = 0
    for origin in Square:
        piece = position[origin]
        if piece is None or piece.color != attacker_color:
            continue
        if piece_attacks_bb(origin, piece, occupied) & square_bb(square):
            attackers |= square_bb(origin)
    return attackers


def danger_bb(position: Position, color: Color, occupied: int) -> int:
    """Return all squares attacked by the enemy of ``color``."""
    danger = 0
    for square in Square:
        piece = position[square]
        if piece is None or piece.color == color:
            continue
        danger |= piece_attacks_bb(square, piece, occupied)
    return danger
