import re

from board import Board
from eval import is_checkmate
from king_safety import KingSafety
from move import Move, MoveFlag
from pieces import PieceKind, Square, square_from_name, square_to_name

_PIECE_CHARS = {
    "N": PieceKind.KNIGHT,
    "B": PieceKind.BISHOP,
    "R": PieceKind.ROOK,
    "Q": PieceKind.QUEEN,
    "K": PieceKind.KING,
}

_PROMOTION_CHARS = {
    "Q": PieceKind.QUEEN,
    "R": PieceKind.ROOK,
    "B": PieceKind.BISHOP,
    "N": PieceKind.KNIGHT,
}


class IllegalMoveError(ValueError):
    """Raised when SAN does not match any legal move."""


class AmbiguousMoveError(ValueError):
    """Raised when SAN matches more than one legal move."""


def _normalize_san(san: str) -> str:
    san = san.strip()
    san = san.rstrip("+").rstrip("#")
    san = san.replace("0-0-0", "O-O-O").replace("0-0", "O-O")
    san = re.sub(r"\s*e\.?p\.?", "", san, flags=re.IGNORECASE)
    return san


def _move_is_capture(move: Move, board: Board) -> bool:
    if move.flags in (MoveFlag.CAPTURE, MoveFlag.EN_PASSANT):
        return True
    if move.flags == MoveFlag.PROMOTION:
        return board[move.to_square] is not None
    return False


def match_move(board: Board, san: str) -> Move:
    """Return the unique legal ``Move`` matching Standard Algebraic ``san``."""
    san = _normalize_san(san)

    if san == "O-O":
        return _match_castle(board, MoveFlag.CASTLE_KINGSIDE, san)
    if san == "O-O-O":
        return _match_castle(board, MoveFlag.CASTLE_QUEENSIDE, san)

    promotion: PieceKind | None = None
    if "=" in san:
        san, promo_part = san.split("=", 1)
        promo_char = promo_part[0].upper()
        if promo_char not in _PROMOTION_CHARS:
            raise IllegalMoveError(f"Unknown promotion piece in {san!r}")
        promotion = _PROMOTION_CHARS[promo_char]

    is_capture = "x" in san
    if len(san) < 2:
        raise IllegalMoveError(f"Invalid SAN: {san!r}")

    to_square = square_from_name(san[-2:])
    prefix = san[:-2]

    piece_kind = PieceKind.PAWN
    if prefix and prefix[0] in _PIECE_CHARS:
        piece_kind = _PIECE_CHARS[prefix[0]]
        prefix = prefix[1:]

    if is_capture:
        prefix = prefix.replace("x", "", 1)

    disambig_file: int | None = None
    disambig_rank: int | None = None
    for character in prefix:
        if character in "abcdefgh":
            disambig_file = ord(character) - ord("a")
        elif character.isdigit():
            disambig_rank = int(character) - 1

    candidates: list[Move] = []
    for move in board.generate_moves():
        piece = board[move.from_square]
        if move.to_square != to_square:
            continue
        if piece.kind != piece_kind:
            continue
        if disambig_file is not None and move.from_square.file != disambig_file:
            continue
        if disambig_rank is not None and move.from_square.rank != disambig_rank:
            continue

        move_capture = _move_is_capture(move, board)
        if is_capture and not move_capture:
            continue
        if not is_capture and move_capture:
            continue

        if promotion is not None:
            if move.flags != MoveFlag.PROMOTION or move.promotion != promotion:
                continue
        elif move.flags == MoveFlag.PROMOTION:
            continue

        candidates.append(move)

    if not candidates:
        raise IllegalMoveError(f"No legal move matches SAN {san!r}")
    if len(candidates) > 1:
        raise AmbiguousMoveError(f"SAN {san!r} is ambiguous: {candidates!r}")
    return candidates[0]


_PIECE_TO_CHAR = {
    PieceKind.KNIGHT: "N",
    PieceKind.BISHOP: "B",
    PieceKind.ROOK: "R",
    PieceKind.QUEEN: "Q",
    PieceKind.KING: "K",
}

_PROMOTION_TO_CHAR = {
    PieceKind.QUEEN: "Q",
    PieceKind.ROOK: "R",
    PieceKind.BISHOP: "B",
    PieceKind.KNIGHT: "N",
}


def move_to_san(board: Board, move: Move) -> str:
    """Return Standard Algebraic Notation for ``move`` on ``board``."""
    if move.flags == MoveFlag.CASTLE_KINGSIDE:
        return _with_check_suffix(board, move, "O-O")
    if move.flags == MoveFlag.CASTLE_QUEENSIDE:
        return _with_check_suffix(board, move, "O-O-O")

    piece = board[move.from_square]
    if piece is None:
        raise IllegalMoveError(f"No piece on {move.from_square}")

    to_name = square_to_name(move.to_square)
    is_capture = _move_is_capture(move, board)

    if piece.kind == PieceKind.PAWN:
        if is_capture:
            san = f"{square_to_name(move.from_square)[0]}x{to_name}"
        else:
            san = to_name
        if move.flags == MoveFlag.PROMOTION and move.promotion is not None:
            san += f"={_PROMOTION_TO_CHAR[move.promotion]}"
        return _with_check_suffix(board, move, san)

    letter = _PIECE_TO_CHAR[piece.kind]
    san = f"{letter}{_disambiguation(board, move, piece.kind)}"
    if is_capture:
        san += "x"
    san += to_name
    return _with_check_suffix(board, move, san)


def _disambiguation(board: Board, move: Move, kind: PieceKind) -> str:
    """Return file/rank prefix when another piece of ``kind`` can reach ``move.to_square``."""
    from_square = move.from_square
    ambiguators: list[Square] = []
    for candidate in board.generate_moves():
        if candidate.to_square != move.to_square:
            continue
        if candidate.from_square == from_square:
            continue
        piece = board[candidate.from_square]
        if piece is not None and piece.kind == kind:
            ambiguators.append(candidate.from_square)
    if not ambiguators:
        return ""

    if not any(square.file == from_square.file for square in ambiguators):
        return chr(ord("a") + from_square.file)
    if not any(square.rank == from_square.rank for square in ambiguators):
        return str(from_square.rank + 1)
    return square_to_name(from_square)


def _with_check_suffix(board: Board, move: Move, san: str) -> str:
    board.make_move(move)
    try:
        opponent = board.side_to_move
        if not _has_king(board, opponent):
            return f"{san}#"
        if is_checkmate(board):
            return f"{san}#"
        if KingSafety.for_color(board, opponent).in_check:
            return f"{san}+"
        return san
    finally:
        board.unmake_move()


def _has_king(board: Board, color) -> bool:
    from pieces import PieceKind

    for square in Square:
        piece = board[square]
        if piece is not None and piece.kind == PieceKind.KING and piece.color == color:
            return True
    return False


def _match_castle(board: Board, flag: MoveFlag, san: str) -> Move:
    candidates = [
        move for move in board.generate_moves() if move.flags == flag
    ]
    if not candidates:
        raise IllegalMoveError(f"No legal move matches SAN {san!r}")
    if len(candidates) > 1:
        raise AmbiguousMoveError(f"SAN {san!r} is ambiguous: {candidates!r}")
    return candidates[0]
