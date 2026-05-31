from board import (
    Board,
    CASTLE_ALL,
    Color,
    MoveFlag,
    Piece,
    PieceKind,
    Square,
)
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
    board = Board.from_simple_fen("8/8/8/3pP3/8/8/8/8 w")
    board.en_passant_target = Square.E6
    moves = board.generate_moves()
    ep_moves = [move for move in moves if move.flags == MoveFlag.EN_PASSANT]
    assert len(ep_moves) == 1
    assert ep_moves[0] == Move(Square.E5, Square.E6, flags=MoveFlag.EN_PASSANT)


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
    board = Board.from_simple_fen("8/4P3/8/8/8/8/8/4k3 w")
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
    board = Board.from_simple_fen("8/8/8/8/4P3/8/8/8 w")
    moves = board.generate_moves()
    assert all(move.to_square != Square.D5 for move in moves)
    assert all(move.to_square != Square.F5 for move in moves)


def test_knight_blocked_by_friendly_piece() -> None:
    board = Board.from_simple_fen("8/8/8/2P4/8/3N4/8/8 w")
    moves = board.generate_moves()
    knight_destinations = {
        move.to_square for move in moves if move.from_square == Square.D3
    }
    assert Square.C5 not in knight_destinations
