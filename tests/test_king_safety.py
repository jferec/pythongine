import pytest

from bitboard import KNIGHT_ATTACKS, popcount, square_bb
from board import Board, Color, Piece, PieceKind, Square
from king_safety import ALL_SQUARES, KingSafety


def test_starting_position_white_king_safety() -> None:
    board = Board()
    safety = KingSafety.for_color(board, Color.WHITE)

    assert safety.king_square == Square.E1
    assert not safety.in_check
    assert not safety.is_double_check
    assert safety.checkers == 0
    assert safety.pinned == 0
    assert safety.evasion_mask == ALL_SQUARES
    assert safety.danger & square_bb(Square.E1) == 0


def test_back_rank_mate_no_evasion() -> None:
    board = Board.from_simple_fen("6k1/5Q2/8/8/8/8/8/6K1 w")
    safety = KingSafety.for_color(board, Color.BLACK)

    assert safety.king_square == Square.G8
    assert safety.in_check
    assert not safety.is_double_check
    assert popcount(safety.checkers) == 1
    assert safety.checkers & square_bb(Square.F7)
    assert safety.evasion_mask == square_bb(Square.F7)
    assert safety.danger & square_bb(Square.G8)


def test_single_rook_check_evasion_mask() -> None:
    board = Board.from_simple_fen("R3k3/8/8/8/8/8/8/8 w")
    safety = KingSafety.for_color(board, Color.BLACK)

    assert safety.in_check
    assert safety.king_square == Square.E8
    assert safety.checkers & square_bb(Square.A8)
    assert safety.evasion_mask == (
        square_bb(Square.B8)
        | square_bb(Square.C8)
        | square_bb(Square.D8)
        | square_bb(Square.A8)
    )


def test_knight_check_evasion_mask() -> None:
    board = Board.from_simple_fen("4k3/2N5/8/8/8/8/8/8 b")
    safety = KingSafety.for_color(board, Color.BLACK)

    assert safety.in_check
    assert safety.checkers & square_bb(Square.C7)
    assert safety.evasion_mask == square_bb(Square.C7)


def test_double_check_zero_evasion_mask() -> None:
    board = Board.from_simple_fen("4k3/6N1/8/8/8/8/8/4R3 w")
    safety = KingSafety.for_color(board, Color.BLACK)

    assert safety.in_check
    assert safety.is_double_check
    assert popcount(safety.checkers) == 2
    assert safety.evasion_mask == 0


def test_absolute_pin_on_bishop() -> None:
    board = Board.from_simple_fen("4k3/4q3/8/8/8/8/4B3/4K3 w")
    safety = KingSafety.for_color(board, Color.WHITE)

    assert safety.pinned & square_bb(Square.E2)
    expected_ray = (
        square_bb(Square.E2)
        | square_bb(Square.E3)
        | square_bb(Square.E4)
        | square_bb(Square.E5)
        | square_bb(Square.E6)
        | square_bb(Square.E7)
    )
    assert safety.pin_rays[Square.E2] == expected_ray


def test_pinned_knight_has_no_moves_along_pin_ray() -> None:
    board = Board.from_simple_fen("4k3/8/8/8/8/2b5/3N4/4K3 w")
    safety = KingSafety.for_color(board, Color.WHITE)

    assert safety.pinned & square_bb(Square.D2)
    assert safety.pin_rays[Square.D2] & KNIGHT_ATTACKS[Square.D2] == 0


def test_danger_includes_attacked_king_square() -> None:
    board = Board.from_simple_fen("4R1k1/8/8/8/8/8/8/4K3 b")
    safety = KingSafety.for_color(board, Color.BLACK)

    assert safety.in_check
    assert safety.danger & square_bb(Square.G8)


def test_bishop_check_evasion_mask_includes_interposing_squares() -> None:
    board = Board.from_simple_fen("4k3/8/8/8/1b6/8/8/4K3 w")
    safety = KingSafety.for_color(board, Color.WHITE)

    assert safety.in_check
    assert safety.checkers & square_bb(Square.B4)
    assert safety.evasion_mask & square_bb(Square.C3)
    assert safety.evasion_mask & square_bb(Square.D2)
    assert safety.evasion_mask & square_bb(Square.B4)


def test_queen_diagonal_check_evasion_mask() -> None:
    board = Board.from_simple_fen("4k3/8/6Q1/8/8/8/8/4K3 w")
    safety = KingSafety.for_color(board, Color.BLACK)

    assert safety.in_check
    assert safety.checkers & square_bb(Square.G6)
    assert safety.evasion_mask & square_bb(Square.F7)
    assert safety.evasion_mask & square_bb(Square.G6)


def test_pawn_check_evasion_mask_is_checker_square_only() -> None:
    board = Board.from_simple_fen("8/8/8/8/8/8/7p/6K1 w")
    safety = KingSafety.for_color(board, Color.WHITE)

    assert safety.in_check
    assert safety.checkers & square_bb(Square.H2)
    assert safety.evasion_mask == square_bb(Square.H2)


def test_danger_includes_enemy_king_attacks() -> None:
    board = Board.from_simple_fen("8/8/8/8/4k3/8/8/4K3 w")
    safety = KingSafety.for_color(board, Color.WHITE)

    assert safety.danger & square_bb(Square.D3)
    assert not (safety.danger & square_bb(Square.E1))


def test_danger_includes_enemy_pawn_attacks() -> None:
    board = Board.from_simple_fen("8/8/8/8/3p4/8/8/4K3 w")
    safety = KingSafety.for_color(board, Color.WHITE)

    assert safety.danger & square_bb(Square.C3)
    assert safety.danger & square_bb(Square.E3)


def test_for_color_raises_when_king_missing() -> None:
    board = Board.from_simple_fen("8/8/8/8/8/8/8/4K3 w")
    with pytest.raises(ValueError, match="No black king"):
        KingSafety.for_color(board, Color.BLACK)


def test_pin_ray_includes_pinner_square() -> None:
    board = Board.from_simple_fen("4k3/4q3/8/8/8/8/4B3/4K3 w")
    safety = KingSafety.for_color(board, Color.WHITE)

    assert safety.pin_rays[Square.E2] & square_bb(Square.E7)
