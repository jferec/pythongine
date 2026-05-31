from collections.abc import Iterator

from pieces import Square

KNIGHT_OFFSETS = (17, 15, 10, 6, -6, -10, -15, -17)
KING_OFFSETS = (1, -1, 8, -8, 9, 7, -7, -9)


def square_bb(square: Square) -> int:
    return 1 << square


def iter_squares(bitboard: int) -> Iterator[Square]:
    while bitboard:
        least_significant = bitboard & -bitboard
        yield Square(least_significant.bit_length() - 1)
        bitboard ^= least_significant


def popcount(bitboard: int) -> int:
    return bitboard.bit_count()


def _attacks_from_offsets(square_index: int, offsets: tuple[int, ...]) -> int:
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
    return tuple(_attacks_from_offsets(square_index, offsets) for square_index in range(64))


KNIGHT_ATTACKS = _build_attack_table(KNIGHT_OFFSETS)
KING_ATTACKS = _build_attack_table(KING_OFFSETS)
