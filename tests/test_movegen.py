from board import (
    Board,
    CASTLE_ALL,
    Color,
    MoveFlag,
    Piece,
    PieceKind,
    Square,
)
from king_safety import KingSafety
from move import Move


def test_initial_position_white_move_count() -> None:
    board = Board()
    moves = board.generate_moves()
    assert len(moves) == 20
    assert all(move.flags != MoveFlag.PROMOTION for move in moves)


def test_to_simple_fen_starting_position() -> None:
    board = Board()
    assert (
        board.to_simple_fen()
        == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w"
    )


def test_from_simple_fen_round_trip() -> None:
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w"
    board = Board.from_simple_fen(fen)
    assert board.to_simple_fen() == fen
    assert len(board.generate_moves()) == 20


def test_en_passant_capture_generated() -> None:
    board = Board.from_simple_fen("8/8/8/3p1P3/8/8/8/4K3 w")
    board.en_passant_target = Square.E6
    moves = board.generate_moves()
    ep_moves = [move for move in moves if move.flags == MoveFlag.EN_PASSANT]
    assert len(ep_moves) == 1
    assert ep_moves[0] == Move(Square.F5, Square.E6, flags=MoveFlag.EN_PASSANT)


def test_castling_moves_generated() -> None:
    board = Board.from_simple_fen("r3k2r/8/8/8/8/8/8/R3K2R w")
    board.castling_rights = CASTLE_ALL
    moves = board.generate_moves()
    castle_moves = [
        move
        for move in moves
        if move.flags in (MoveFlag.CASTLE_KINGSIDE, MoveFlag.CASTLE_QUEENSIDE)
    ]
    assert len(castle_moves) == 2
    assert Move(Square.E1, Square.G1, flags=MoveFlag.CASTLE_KINGSIDE) in castle_moves
    assert Move(Square.E1, Square.C1, flags=MoveFlag.CASTLE_QUEENSIDE) in castle_moves


def test_promotion_generates_four_moves() -> None:
    board = Board.from_simple_fen("8/4P3/8/8/8/8/4K2k/8 w")
    moves = board.generate_moves()
    promotions = [move for move in moves if move.flags == MoveFlag.PROMOTION]
    assert len(promotions) == 4
    promotion_kinds = {move.promotion for move in promotions}
    assert promotion_kinds == {
        PieceKind.QUEEN,
        PieceKind.ROOK,
        PieceKind.BISHOP,
        PieceKind.KNIGHT,
    }


def test_pawn_cannot_capture_empty_diagonal() -> None:
    board = Board.from_simple_fen("8/8/8/8/4P3/8/8/4K3 w")
    moves = board.generate_moves()
    assert all(move.to_square != Square.D5 for move in moves)
    assert all(move.to_square != Square.F5 for move in moves)


def test_knight_blocked_by_friendly_piece() -> None:
    board = Board.from_simple_fen("8/8/8/2P4/8/3N4/8/4K3 w")
    moves = board.generate_moves()
    knight_destinations = {
        move.to_square for move in moves if move.from_square == Square.D3
    }
    assert Square.C5 not in knight_destinations


def test_pinned_piece_cannot_move_off_pin_line() -> None:
    board = Board.from_simple_fen("4k3/4q3/8/8/8/8/4B3/4K3 w")
    moves = board.generate_moves()
    assert all(move.from_square != Square.E2 for move in moves)


def test_in_check_only_evasion_moves() -> None:
    board = Board.from_simple_fen("R3k3/8/8/8/8/8/8/8 b")
    moves = board.generate_moves()
    assert moves
    assert all(move.from_square == Square.E8 for move in moves)


def test_castling_illegal_through_check() -> None:
    board = Board.from_simple_fen("r3k2r/8/8/8/8/8/4q3/R3K2R w")
    board.castling_rights = CASTLE_ALL
    moves = board.generate_moves()
    castle_moves = [
        move
        for move in moves
        if move.flags in (MoveFlag.CASTLE_KINGSIDE, MoveFlag.CASTLE_QUEENSIDE)
    ]
    assert castle_moves == []


def test_en_passant_pinned_illegal() -> None:
    board = Board.from_simple_fen("4r3/8/8/8/3p1P2/8/8/4K3 w")
    board.en_passant_target = Square.D6
    moves = board.generate_moves()
    assert all(move.flags != MoveFlag.EN_PASSANT for move in moves)


def test_en_passant_post_validation_rejects_leaving_king_in_check() -> None:
    board = Board.from_simple_fen("4r3/8/8/2P6/8/8/8/4K3 w")
    board.en_passant_target = Square.D6
    move = Move(Square.C5, Square.D6, flags=MoveFlag.EN_PASSANT)
    board.make_move(move)
    assert KingSafety.for_color(board, Color.WHITE).in_check
    board.unmake_move()
    assert move not in board.generate_moves()


def test_block_slider_check_with_pawn_push() -> None:
    board = Board.from_simple_fen("4k3/8/8/8/1b6/8/2P5/4K3 w")
    move = Move(Square.C2, Square.C3)
    assert move in board.generate_moves()


def test_capture_knight_checker() -> None:
    board = Board.from_simple_fen("4k3/2N5/8/8/8/8/8/8 b")
    moves = board.generate_moves()
    assert Move(Square.E8, Square.C7) not in moves
    assert all(
        move.from_square == Square.E8 or move.to_square == Square.C7
        for move in moves
    )


def test_double_check_generates_king_moves_only() -> None:
    board = Board.from_simple_fen("4k3/6N1/8/8/8/8/8/4R3 b")
    moves = board.generate_moves()
    assert moves
    assert all(move.from_square == Square.E8 for move in moves)


def test_pinned_rook_moves_along_pin_file() -> None:
    board = Board.from_simple_fen("4k3/4r3/8/8/8/8/4R3/4K3 w")
    moves = [move for move in board.generate_moves() if move.from_square == Square.E2]
    destinations = {move.to_square for move in moves}
    assert Square.E3 in destinations
    assert Square.E7 in destinations
    assert Square.D2 not in destinations


def test_pinned_rook_can_capture_pinner() -> None:
    board = Board.from_simple_fen("4k3/4r3/8/8/8/8/4R3/4K3 w")
    move = Move(Square.E2, Square.E7, flags=MoveFlag.CAPTURE)
    assert move in board.generate_moves()


def test_split_castling_kingside_illegal_queenside_legal() -> None:
    board = Board.from_simple_fen("r3k2r/8/8/8/8/7q/8/R3K2R w")
    board.castling_rights = CASTLE_ALL
    moves = board.generate_moves()
    castle_moves = [
        move
        for move in moves
        if move.flags in (MoveFlag.CASTLE_KINGSIDE, MoveFlag.CASTLE_QUEENSIDE)
    ]
    assert Move(Square.E1, Square.G1, flags=MoveFlag.CASTLE_KINGSIDE) not in castle_moves
    assert Move(Square.E1, Square.C1, flags=MoveFlag.CASTLE_QUEENSIDE) in castle_moves


def test_black_castling_moves_generated() -> None:
    board = Board.from_simple_fen("r3k2r/8/8/8/8/8/8/R3K2R b")
    board.castling_rights = CASTLE_ALL
    moves = board.generate_moves()
    castle_moves = [
        move
        for move in moves
        if move.flags in (MoveFlag.CASTLE_KINGSIDE, MoveFlag.CASTLE_QUEENSIDE)
    ]
    assert Move(Square.E8, Square.G8, flags=MoveFlag.CASTLE_KINGSIDE) in castle_moves
    assert Move(Square.E8, Square.C8, flags=MoveFlag.CASTLE_QUEENSIDE) in castle_moves


def test_make_move_unmake_en_passant_round_trip() -> None:
    board = Board.from_simple_fen("8/8/8/3p1P3/8/8/8/4K3 w")
    board.en_passant_target = Square.E6
    move = Move(Square.F5, Square.E6, flags=MoveFlag.EN_PASSANT)
    fen_before = board.to_simple_fen()
    ep_rights_before = board.en_passant_target

    board.make_move(move)
    assert board[Square.E6] == Piece(PieceKind.PAWN, Color.WHITE)
    assert board[Square.F5] is None
    assert board[Square.E5] is None

    undone = board.unmake_move()
    assert undone == move
    assert board.to_simple_fen() == fen_before
    assert board.en_passant_target == ep_rights_before
    assert board[Square.F5] == Piece(PieceKind.PAWN, Color.WHITE)
    assert board[Square.D5] == Piece(PieceKind.PAWN, Color.BLACK)
