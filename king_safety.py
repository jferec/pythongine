from collections.abc import Iterator
from dataclasses import dataclass

from attacks import attackers_to_square, danger_bb
from bitboard import popcount, square_bb
from pieces import Color, Piece, PieceKind, Square
from position import Position

ALL_SQUARES = (1 << 64) - 1

_BISHOP_DELTAS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
_ROOK_DELTAS = ((0, 1), (0, -1), (1, 0), (-1, 0))
_RAY_DELTAS = _BISHOP_DELTAS + _ROOK_DELTAS


def _find_king_square(position: Position, color: Color) -> Square:
    """Return the square of ``color``'s king."""
    for square in Square:
        piece = position[square]
        if piece is not None and piece.kind == PieceKind.KING and piece.color == color:
            return square
    raise ValueError(f"No {color.name.lower()} king on the board")


def _is_diagonal_delta(delta_file: int, delta_rank: int) -> bool:
    return abs(delta_file) == abs(delta_rank)


def _is_orthogonal_delta(delta_file: int, delta_rank: int) -> bool:
    return delta_file == 0 or delta_rank == 0


def _slider_pins_along_ray(piece: Piece, delta_file: int, delta_rank: int) -> bool:
    """Return True if ``piece`` can absolutely pin along this ray direction."""
    if piece.kind == PieceKind.QUEEN:
        return True
    if piece.kind == PieceKind.BISHOP and _is_diagonal_delta(delta_file, delta_rank):
        return True
    if piece.kind == PieceKind.ROOK and _is_orthogonal_delta(delta_file, delta_rank):
        return True
    return False


def _iter_ray_squares(
    from_square: Square, delta_file: int, delta_rank: int
) -> Iterator[Square]:
    """Yield squares along a ray starting one step from ``from_square``."""
    file = from_square.file + delta_file
    rank = from_square.rank + delta_rank
    while 0 <= file < 8 and 0 <= rank < 8:
        yield Square(rank * 8 + file)
        file += delta_file
        rank += delta_rank


def _occupied_pieces_on_ray(
    position: Position,
    from_square: Square,
    delta_file: int,
    delta_rank: int,
    *,
    max_pieces: int = 2,
) -> list[tuple[Square, Piece]]:
    """Return up to ``max_pieces`` occupied squares in ray order from ``from_square``."""
    pieces: list[tuple[Square, Piece]] = []
    for square in _iter_ray_squares(from_square, delta_file, delta_rank):
        piece = position[square]
        if piece is None:
            continue
        pieces.append((square, piece))
        if len(pieces) >= max_pieces:
            break
    return pieces


def _pin_line_mask(
    from_square: Square, delta_file: int, delta_rank: int, through_square: Square
) -> int:
    """Return a bitboard of ray squares from ``from_square`` through ``through_square``."""
    mask = 0
    for square in _iter_ray_squares(from_square, delta_file, delta_rank):
        mask |= square_bb(square)
        if square == through_square:
            break
    return mask


def _absolute_pin_on_ray(
    position: Position,
    king_square: Square,
    color: Color,
    delta_file: int,
    delta_rank: int,
) -> tuple[Square, int] | None:
    """Return ``(pinned_square, pin_line)`` when an absolute pin exists on this ray."""
    pieces = _occupied_pieces_on_ray(position, king_square, delta_file, delta_rank)
    if len(pieces) != 2:
        return None

    (friendly_square, friendly), (enemy_square, enemy) = pieces
    if friendly.color != color or enemy.color == color:
        return None
    if not _slider_pins_along_ray(enemy, delta_file, delta_rank):
        return None

    return friendly_square, _pin_line_mask(
        king_square, delta_file, delta_rank, enemy_square
    )


def _scan_pins_from_king(
    position: Position, king_square: Square, color: Color
) -> tuple[int, tuple[int, ...]]:
    """Detect absolute pins and return ``(pinned, pin_rays)``."""
    pin_rays = [ALL_SQUARES] * 64
    pinned = 0

    for delta_file, delta_rank in _RAY_DELTAS:
        pin = _absolute_pin_on_ray(position, king_square, color, delta_file, delta_rank)
        if pin is None:
            continue
        friendly_square, pin_line = pin
        pinned |= square_bb(friendly_square)
        pin_rays[friendly_square] = pin_line

    return pinned, tuple(pin_rays)


def _between_squares(from_square: Square, to_square: Square) -> int:
    """Return empty squares strictly between ``from_square`` and ``to_square``."""
    delta_file = to_square.file - from_square.file
    delta_rank = to_square.rank - from_square.rank
    if delta_file == 0 and delta_rank == 0:
        return 0

    step_file = 0 if delta_file == 0 else (1 if delta_file > 0 else -1)
    step_rank = 0 if delta_rank == 0 else (1 if delta_rank > 0 else -1)
    if abs(delta_file) != abs(delta_rank) and delta_file != 0 and delta_rank != 0:
        return 0

    between = 0
    file = from_square.file + step_file
    rank = from_square.rank + step_rank
    while file != to_square.file or rank != to_square.rank:
        between |= square_bb(Square(rank * 8 + file))
        file += step_file
        rank += step_rank
    return between


def _build_evasion_mask(
    position: Position, king_square: Square, checkers: int
) -> int:
    """Return destination mask for non-king moves while resolving check."""
    if checkers == 0:
        return ALL_SQUARES
    if popcount(checkers) >= 2:
        return 0

    checker_square = Square((checkers & -checkers).bit_length() - 1)
    checker = position[checker_square]
    assert checker is not None

    if checker.kind in (PieceKind.KNIGHT, PieceKind.PAWN):
        return square_bb(checker_square)

    return _between_squares(king_square, checker_square) | square_bb(checker_square)


@dataclass(frozen=True)
class KingSafety:
    """King safety analysis for one side: pins, check state, and move masks."""

    color: Color
    king_square: Square
    checkers: int
    danger: int
    pinned: int
    pin_rays: tuple[int, ...]
    evasion_mask: int

    @property
    def in_check(self) -> bool:
        """Return True if the king is currently in check."""
        return self.checkers != 0

    @property
    def is_double_check(self) -> bool:
        """Return True if exactly two or more enemy pieces give check."""
        return popcount(self.checkers) >= 2

    @classmethod
    def for_color(cls, position: Position, color: Color) -> KingSafety:
        """Compute king safety for ``color`` from the current position."""
        king_square = _find_king_square(position, color)
        occupied = position.all_occupied_bb()
        danger = danger_bb(position, color, occupied)
        checkers = attackers_to_square(position, king_square, ~color, occupied)
        pinned, pin_rays = _scan_pins_from_king(position, king_square, color)
        evasion_mask = _build_evasion_mask(position, king_square, checkers)

        return cls(
            color=color,
            king_square=king_square,
            checkers=checkers,
            danger=danger,
            pinned=pinned,
            pin_rays=pin_rays,
            evasion_mask=evasion_mask,
        )
