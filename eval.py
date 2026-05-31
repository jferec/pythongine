"""Static position evaluation (material + piece-square tables).

Baseline: Tomasz Michniewski's "Simplified Evaluation Function", published for
the progszach unified-evaluation test tournament and documented on the
Chessprogramming wiki. That scheme is intentionally minimal (material + PSQT
only) so it can stand alone before search, mobility, or pawn-structure terms.

References:
  https://www.chessprogramming.org/Simplified_Evaluation_Function
  https://www.chessprogramming.org/Evaluation  (side-to-move scoring for negamax)
"""

from board import Board
from king_safety import KingSafety
from pieces import Color, PieceKind, Square

MATE_SCORE = 30_000
MATE_THRESHOLD = MATE_SCORE - 1_000  # leaves room for mate-in-N scoring in search

# Centipawn scale (×100) so positional tweaks stay smaller than piece values.
# Michniewski relations: B > N > 3P, B+N ≈ R+1.5P, Q+P ≈ 2R. King is 0 here;
# mate/stalemate are handled in search, not static eval.
PIECE_VALUES: dict[PieceKind, int] = {
    PieceKind.PAWN: 100,
    PieceKind.KNIGHT: 320,
    PieceKind.BISHOP: 330,
    PieceKind.ROOK: 500,
    PieceKind.QUEEN: 900,
    PieceKind.KING: 0,
}

# Michniewski PSQT values (white-oriented, rank 8 = index 0). Middlegame king
# table only; tapered mg/eg interpolation is deferred until search exists.
_PAWN_PSQT = (
    (0, 0, 0, 0, 0, 0, 0, 0),
    (50, 50, 50, 50, 50, 50, 50, 50),
    (10, 10, 20, 30, 30, 20, 10, 10),
    (5, 5, 10, 25, 25, 10, 5, 5),
    (0, 0, 0, 20, 20, 0, 0, 0),
    (5, -5, -10, 0, 0, -10, -5, 5),
    (5, 10, 10, -20, -20, 10, 10, 5),
    (0, 0, 0, 0, 0, 0, 0, 0),
)

_KNIGHT_PSQT = (
    (-50, -40, -30, -30, -30, -30, -40, -50),
    (-40, -20, 0, 0, 0, 0, -20, -40),
    (-30, 0, 10, 15, 15, 10, 0, -30),
    (-30, 5, 15, 20, 20, 15, 5, -30),
    (-30, 0, 15, 20, 20, 15, 0, -30),
    (-30, 5, 10, 15, 15, 10, 5, -30),
    (-40, -20, 0, 5, 5, 0, -20, -40),
    (-50, -40, -30, -30, -30, -30, -40, -50),
)

_BISHOP_PSQT = (
    (-20, -10, -10, -10, -10, -10, -10, -20),
    (-10, 0, 0, 0, 0, 0, 0, -10),
    (-10, 0, 5, 10, 10, 5, 0, -10),
    (-10, 5, 5, 10, 10, 5, 5, -10),
    (-10, 0, 10, 10, 10, 10, 0, -10),
    (-10, 10, 10, 10, 10, 10, 10, -10),
    (-10, 5, 0, 0, 0, 0, 5, -10),
    (-20, -10, -10, -10, -10, -10, -10, -20),
)

_ROOK_PSQT = (
    (0, 0, 0, 0, 0, 0, 0, 0),
    (5, 10, 10, 10, 10, 10, 10, 5),
    (-5, 0, 0, 0, 0, 0, 0, -5),
    (-5, 0, 0, 0, 0, 0, 0, -5),
    (-5, 0, 0, 0, 0, 0, 0, -5),
    (-5, 0, 0, 0, 0, 0, 0, -5),
    (-5, 0, 0, 0, 0, 0, 0, -5),
    (0, 0, 0, 5, 5, 0, 0, 0),
)

_QUEEN_PSQT = (
    (-20, -10, -10, -5, -5, -10, -10, -20),
    (-10, 0, 0, 0, 0, 0, 0, -10),
    (-10, 0, 5, 5, 5, 5, 0, -10),
    (-5, 0, 5, 5, 5, 5, 0, -5),
    (0, 0, 5, 5, 5, 5, 0, -5),
    (-10, 5, 5, 5, 5, 5, 0, -10),
    (-10, 0, 5, 0, 0, 0, 0, -10),
    (-20, -10, -10, -5, -5, -10, -10, -20),
)

_KING_PSQT = (
    (-30, -40, -40, -50, -50, -40, -40, -30),
    (-30, -40, -40, -50, -50, -40, -40, -30),
    (-30, -40, -40, -50, -50, -40, -40, -30),
    (-30, -40, -40, -50, -50, -40, -40, -30),
    (-20, -30, -30, -40, -40, -30, -30, -20),
    (-10, -20, -20, -20, -20, -20, -20, -10),
    (20, 20, 0, 0, 0, 0, 20, 20),
    (20, 30, 10, 0, 0, 10, 30, 20),
)

_PSQT: dict[PieceKind, tuple[tuple[int, ...], ...]] = {
    PieceKind.PAWN: _PAWN_PSQT,
    PieceKind.KNIGHT: _KNIGHT_PSQT,
    PieceKind.BISHOP: _BISHOP_PSQT,
    PieceKind.ROOK: _ROOK_PSQT,
    PieceKind.QUEEN: _QUEEN_PSQT,
    PieceKind.KING: _KING_PSQT,
}


def psqt_bonus(kind: PieceKind, square: Square, color: Color) -> int:
    """Return the piece-square bonus for ``kind`` on ``square`` for ``color``.

    Tables are authored for White; Black mirrors by rank per Michniewski.
    ``square.rank`` runs 0=a1..7=a8, so White indexes with ``7 - rank``.
    """
    table = _PSQT[kind]
    if color == Color.WHITE:
        rank = 7 - square.rank
    else:
        rank = square.rank
    return table[rank][square.file]


def _color_score(board: Board, color: Color) -> int:
    score = 0
    for square in Square:
        piece = board[square]
        if piece is None or piece.color != color:
            continue
        score += PIECE_VALUES[piece.kind]
        score += psqt_bonus(piece.kind, square, color)
    return score


def evaluate(board: Board) -> int:
    """Return a centipawn score from the side-to-move's perspective.

    White advantage is positive before the sign flip. Negamax expects this
    convention so leaf scores are always good for the player about to move.
    Counts from scratch each call; incremental eval can wait until search profiling.
    """
    white_score = _color_score(board, Color.WHITE) - _color_score(board, Color.BLACK)
    if board.side_to_move == Color.WHITE:
        return white_score
    return -white_score


def is_checkmate(board: Board) -> bool:
    """Return True if the side to move has no legal moves and is in check."""
    if board.generate_moves():
        return False
    return KingSafety.for_color(board, board.side_to_move).in_check


def is_stalemate(board: Board) -> bool:
    """Return True if the side to move has no legal moves and is not in check."""
    if board.generate_moves():
        return False
    return not KingSafety.for_color(board, board.side_to_move).in_check
