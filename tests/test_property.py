import pytest

from board import Board, Color
from helpers import CURATED_FEN_SUITE, assert_all_legal_moves_leave_king_safe


@pytest.mark.parametrize("fen", CURATED_FEN_SUITE)
def test_all_legal_moves_leave_king_safe(fen: str) -> None:
    board = Board.from_simple_fen(fen)
    assert_all_legal_moves_leave_king_safe(board)


def test_generate_moves_is_non_mutating() -> None:
    from board import Square

    board = Board.from_simple_fen("4k3/8/4r3/4Pp2/8/8/8/4K3 w")
    board.en_passant_target = Square.F6
    fen_before = board.to_simple_fen()
    history_before = len(board.move_history)

    board.generate_moves()

    assert board.to_simple_fen() == fen_before
    assert not board._undo_stack
    assert len(board.move_history) == history_before
