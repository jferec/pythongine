from board import Board, Color
from king_safety import KingSafety

CURATED_FEN_SUITE = [
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w",
    "4k3/2N5/8/8/8/8/8/4K3 b",
    "4k3/2N5/8/8/8/8/8/8 b",
    "4k3/6N1/8/8/8/8/8/4R3 b",
    "4k3/4q3/8/8/8/8/4B3/4K3 w",
    "4k3/4r3/8/8/8/8/4R3/4K3 w",
    "8/8/8/3p1P3/8/8/8/4K3 w",
    "4r3/8/8/8/3p1P2/8/8/4K3 w",
    "r3k2r/8/8/8/8/8/8/R3K2R w",
    "8/4P3/8/8/8/8/4K2k/8 w",
]


def assert_all_legal_moves_leave_king_safe(board: Board) -> None:
    """Apply each legal move and verify the moving side's king is not left in check."""
    color = board.side_to_move
    for move in board.generate_moves():
        board.make_move(move)
        assert not KingSafety.for_color(board, color).in_check
        board.unmake_move()
    assert not board._undo_stack
