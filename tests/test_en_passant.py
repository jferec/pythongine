from board import Board, Color, MoveFlag, Piece, PieceKind, Square
from king_safety import KingSafety
from move import Move


def test_en_passant_discovered_check_rejected() -> None:
    """EP that removes a blocker and exposes the king to a slider must be rejected."""
    board = Board.from_simple_fen("4k3/8/4r3/4Pp2/8/8/8/4K3 w")
    board.en_passant_target = Square.F6
    move = Move(Square.E5, Square.F6, flags=MoveFlag.EN_PASSANT)

    assert not KingSafety.for_color(board, Color.WHITE).in_check
    assert move in [
        m for m in board._generate_pseudo_legal_moves() if m.flags == MoveFlag.EN_PASSANT
    ]

    board.make_move(move)
    assert KingSafety.for_color(board, Color.WHITE).in_check
    board.unmake_move()

    assert move not in board.generate_moves()


def test_en_passant_in_check_blocks_slider_accepted() -> None:
    """EP that interposes on a diagonal may be the only legal evasion while in check."""
    board = Board.from_simple_fen("4k3/8/1b6/Pp6/8/8/8/6K1 w")
    board.en_passant_target = Square.B6
    move = Move(Square.A5, Square.B6, flags=MoveFlag.EN_PASSANT)

    assert KingSafety.for_color(board, Color.WHITE).in_check
    assert move in board.generate_moves()

    board.make_move(move)
    assert not KingSafety.for_color(board, Color.WHITE).in_check
    board.unmake_move()


def test_generate_moves_leaves_undo_stack_empty_after_ep_probing() -> None:
    board = Board.from_simple_fen("4k3/8/4r3/4Pp2/8/8/8/4K3 w")
    board.en_passant_target = Square.F6
    fen_before = board.to_simple_fen()
    history_before = len(board.move_history)

    board.generate_moves()

    assert not board._undo_stack
    assert board.to_simple_fen() == fen_before
    assert len(board.move_history) == history_before


def test_black_en_passant_capture_generated() -> None:
    board = Board.from_simple_fen("8/8/8/8/3Pp3/8/8/4k3 b")
    board.en_passant_target = Square.D3
    moves = board.generate_moves()
    ep_moves = [move for move in moves if move.flags == MoveFlag.EN_PASSANT]
    assert len(ep_moves) == 1
    assert ep_moves[0] == Move(Square.E4, Square.D3, flags=MoveFlag.EN_PASSANT)


def test_pawn_push_to_en_passant_square_is_not_en_passant() -> None:
    board = Board.from_simple_fen("8/8/8/8/4P3/8/8/4K3 w")
    board.en_passant_target = Square.E5
    moves = board.generate_moves()
    push = Move(Square.E4, Square.E5, flags=MoveFlag.QUIET)
    assert push in moves
    assert all(move.flags != MoveFlag.EN_PASSANT for move in moves)


def test_double_pawn_push_sets_en_passant_target() -> None:
    board = Board.from_simple_fen("8/8/8/8/8/8/8/4K3 w")
    board[Square.E2] = Piece(PieceKind.PAWN, Color.WHITE)
    board.make_move(Move(Square.E2, Square.E4))
    assert board.en_passant_target == Square.E3
