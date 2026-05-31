import pytest

from board import (
    Board,
    CASTLE_ALL,
    CASTLE_BLACK_KINGSIDE,
    CASTLE_BLACK_QUEENSIDE,
    CASTLE_WHITE_KINGSIDE,
    CASTLE_WHITE_QUEENSIDE,
    Color,
    MoveFlag,
    Piece,
    PieceKind,
    Square,
)
from move import Move


def test_capture_round_trip() -> None:
    board = Board.from_simple_fen("8/8/8/3p4/4P3/8/8/4K3 w")
    move = Move(Square.E4, Square.D5, flags=MoveFlag.CAPTURE)
    fen_before = board.to_simple_fen()

    board.make_move(move)
    assert board[Square.D5] == Piece(PieceKind.PAWN, Color.WHITE)
    assert board[Square.E4] is None
    assert board[Square.D5] is not None

    board.unmake_move()
    assert board.to_simple_fen() == fen_before
    assert board[Square.E4] == Piece(PieceKind.PAWN, Color.WHITE)
    assert board[Square.D5] == Piece(PieceKind.PAWN, Color.BLACK)


def test_promotion_round_trip() -> None:
    board = Board.from_simple_fen("8/4P3/8/8/8/8/4K2k/8 w")
    move = Move(
        Square.E7,
        Square.E8,
        promotion=PieceKind.QUEEN,
        flags=MoveFlag.PROMOTION,
    )
    fen_before = board.to_simple_fen()

    board.make_move(move)
    assert board[Square.E8] == Piece(PieceKind.QUEEN, Color.WHITE)
    assert board[Square.E7] is None

    board.unmake_move()
    assert board.to_simple_fen() == fen_before
    assert board[Square.E7] == Piece(PieceKind.PAWN, Color.WHITE)


def test_castle_kingside_round_trip() -> None:
    board = Board.from_simple_fen("r3k2r/8/8/8/8/8/8/R3K2R w")
    board.castling_rights = CASTLE_ALL
    move = Move(Square.E1, Square.G1, flags=MoveFlag.CASTLE_KINGSIDE)
    rights_before = board.castling_rights

    board.make_move(move)
    assert board[Square.G1] == Piece(PieceKind.KING, Color.WHITE)
    assert board[Square.F1] == Piece(PieceKind.ROOK, Color.WHITE)
    assert board[Square.E1] is None
    assert board[Square.H1] is None
    assert board.castling_rights == rights_before & ~(
        CASTLE_WHITE_KINGSIDE | CASTLE_WHITE_QUEENSIDE
    )

    board.unmake_move()
    assert board[Square.E1] == Piece(PieceKind.KING, Color.WHITE)
    assert board[Square.H1] == Piece(PieceKind.ROOK, Color.WHITE)
    assert board[Square.F1] is None
    assert board[Square.G1] is None
    assert board.castling_rights == rights_before


def test_castling_rights_cleared_when_king_moves() -> None:
    board = Board.from_simple_fen("8/8/8/8/8/8/8/R3K2R w")
    board.castling_rights = CASTLE_ALL
    board.make_move(Move(Square.E1, Square.E2))
    assert board.castling_rights == CASTLE_ALL & ~(
        CASTLE_WHITE_KINGSIDE | CASTLE_WHITE_QUEENSIDE
    )


def test_castling_rights_cleared_when_rook_moves_from_corner() -> None:
    board = Board.from_simple_fen("8/8/8/8/8/8/8/R3K2R w")
    board.castling_rights = CASTLE_ALL
    board.make_move(Move(Square.H1, Square.H2))
    assert board.castling_rights == CASTLE_ALL & ~CASTLE_WHITE_KINGSIDE


def test_castling_rights_cleared_when_corner_rook_captured() -> None:
    board = Board.from_simple_fen("8/8/8/8/8/8/6r1/R3K2R w")
    board.castling_rights = CASTLE_ALL
    board.make_move(Move(Square.H1, Square.H2, flags=MoveFlag.CAPTURE))
    assert board.castling_rights == CASTLE_ALL & ~CASTLE_WHITE_KINGSIDE


def test_double_pawn_push_and_clear_en_passant_target() -> None:
    board = Board.from_simple_fen("8/8/8/8/8/8/8/4K3 w")
    board[Square.E2] = Piece(PieceKind.PAWN, Color.WHITE)
    board.make_move(Move(Square.E2, Square.E4))
    assert board.en_passant_target == Square.E3

    board[Square.E8] = Piece(PieceKind.KING, Color.BLACK)
    board.make_move(Move(Square.E8, Square.E7))
    assert board.en_passant_target is None


def test_move_history_tracks_make_and_unmake() -> None:
    board = Board.from_simple_fen("8/8/8/8/8/8/8/4K3 w")
    board[Square.E2] = Piece(PieceKind.PAWN, Color.WHITE)
    board[Square.E8] = Piece(PieceKind.KING, Color.BLACK)

    board.make_move(Move(Square.E2, Square.E4))
    board.make_move(Move(Square.E8, Square.E7))
    assert len(board.move_history) == 2

    board.unmake_move()
    assert len(board.move_history) == 1
    board.unmake_move()
    assert board.move_history == []


def test_unmake_move_on_empty_stack_raises() -> None:
    board = Board()
    with pytest.raises(ValueError, match="No move to unmake"):
        board.unmake_move()


def test_make_move_on_empty_from_square_raises() -> None:
    board = Board.from_simple_fen("8/8/8/8/8/8/8/4K3 w")
    with pytest.raises(ValueError, match="Illegal move"):
        board.make_move(Move(Square.E4, Square.E5))
