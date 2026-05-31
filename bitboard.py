"""Bitboard helpers for 64-square chess boards.

A bitboard is an integer whose bit *i* is set when square ``Square(i)`` is
included in the set (attacks, occupancy, move targets, etc.).
"""

from collections.abc import Iterator

from pieces import Square

KNIGHT_OFFSETS = (17, 15, 10, 6, -6, -10, -15, -17)
KING_OFFSETS = (1, -1, 8, -8, 9, 7, -7, -9)

# ``KNIGHT_ATTACKS[square]`` / ``KING_ATTACKS[square]``: pseudo-legal step targets
# from that square (board edges applied; no occupancy masking).
KNIGHT_ATTACKS: tuple[int, ...]
KING_ATTACKS: tuple[int, ...]


def square_bb(square: Square) -> int:
    """Return a bitboard with only ``square`` set."""
    return 1 << square


def iter_squares(bitboard: int) -> Iterator[Square]:
    """Yield each square set in ``bitboard``, from least to most significant bit."""
    while bitboard:
        least_significant = bitboard & -bitboard
        yield Square(least_significant.bit_length() - 1)
        bitboard ^= least_significant


def popcount(bitboard: int) -> int:
    """Return the number of set bits in ``bitboard``."""
    return bitboard.bit_count()


def _attacks_from_offsets(square_index: int, offsets: tuple[int, ...]) -> int:
    """Build attack bitboard for one square from rank/file offset steps."""
    attacks = 0
    origin_rank = square_index // 8
    origin_file = square_index % 8
    for offset in offsets:
        destination = square_index + offset
        if destination < 0 or destination > 63:
            continue
        destination_rank = destination // 8
        destination_file = destination % 8
        if abs(destination_rank - origin_rank) > 2 or abs(destination_file - origin_file) > 2:
            continue
        attacks |= 1 << destination
    return attacks


def _build_attack_table(offsets: tuple[int, ...]) -> tuple[int, ...]:
    """Precompute attack bitboards for all 64 squares."""
    return tuple(_attacks_from_offsets(square_index, offsets) for square_index in range(64))


KNIGHT_ATTACKS = _build_attack_table(KNIGHT_OFFSETS)
KING_ATTACKS = _build_attack_table(KING_OFFSETS)
