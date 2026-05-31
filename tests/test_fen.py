import pytest

from board import (
    Board,
    CASTLE_ALL,
    CASTLE_BLACK_KINGSIDE,
    CASTLE_WHITE_KINGSIDE,
    CASTLE_WHITE_QUEENSIDE,
    Color,
    MoveFlag,
    Piece,
    PieceKind,
    Square,
)
from move import Move

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def test_starting_position_to_fen() -> None:
    board = Board()
    assert board.to_fen() == STARTING_FEN


def test_from_fen_round_trip() -> None:
    board = Board.from_fen(STARTING_FEN)
    assert board.to_fen() == STARTING_FEN
    assert board.side_to_move == Color.WHITE
    assert board.castling_rights == CASTLE_ALL
    assert board.en_passant_target is None
    assert board.halfmove_clock == 0
    assert board.fullmove_number == 1


def test_castling_field_parsing() -> None:
    board = Board.from_fen(f"{STARTING_FEN.split(' ', 1)[0]} w KQkq - 0 1")
    assert board.castling_rights == CASTLE_ALL

    board = Board.from_fen(f"{STARTING_FEN.split(' ', 1)[0]} w Kk - 0 1")
    assert board.castling_rights == CASTLE_WHITE_KINGSIDE | CASTLE_BLACK_KINGSIDE

    board = Board.from_fen(f"{STARTING_FEN.split(' ', 1)[0]} w - - 0 1")
    assert board.castling_rights == 0


def test_en_passant_field_parsing() -> None:
    fen = "8/8/8/3p1P2/8/8/8/4K3 w - e6 0 1"
    board = Board.from_fen(fen)
    assert board.en_passant_target == Square.E6
    assert board.to_fen() == fen

    board = Board.from_fen("8/8/8/8/8/8/8/4K3 w - - 0 1")
    assert board.en_passant_target is None


def test_en_passant_rejects_invalid_rank() -> None:
    with pytest.raises(ValueError, match="Invalid en passant square"):
        Board.from_fen("8/8/8/8/8/8/8/4K3 w - e4 0 1")


def test_partial_fen_defaults_clocks() -> None:
    placement = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR"
    board = Board.from_fen(f"{placement} w KQkq -")
    assert board.halfmove_clock == 0
    assert board.fullmove_number == 1


def test_clock_fields_preserved_on_load() -> None:
    fen = "8/8/8/8/8/8/8/4K3 w - - 42 17"
    board = Board.from_fen(fen)
    assert board.halfmove_clock == 42
    assert board.fullmove_number == 17


def test_halfmove_resets_on_pawn_push() -> None:
    board = Board.from_fen("8/8/8/8/8/8/8/4K3 w - - 10 1")
    board[Square.E2] = Piece(PieceKind.PAWN, Color.WHITE)
    board[Square.E8] = Piece(PieceKind.KING, Color.BLACK)
    board.make_move(Move(Square.E2, Square.E4))
    assert board.halfmove_clock == 0


def test_halfmove_increments_on_quiet_move() -> None:
    board = Board.from_fen("8/8/8/8/8/8/8/4K3 w - - 3 1")
    board[Square.E8] = Piece(PieceKind.KING, Color.BLACK)
    board.make_move(Move(Square.E1, Square.E2))
    assert board.halfmove_clock == 4


def test_fullmove_increments_after_black_move() -> None:
    board = Board.from_fen("8/8/8/8/8/8/8/4K3 w - - 0 5")
    board[Square.E8] = Piece(PieceKind.KING, Color.BLACK)
    board.make_move(Move(Square.E1, Square.E2))
    board.make_move(Move(Square.E8, Square.E7))
    assert board.fullmove_number == 6


def test_unmake_move_restores_clocks() -> None:
    board = Board.from_fen("8/8/8/8/8/8/8/4K3 w - - 7 3")
    board[Square.E8] = Piece(PieceKind.KING, Color.BLACK)
    board.make_move(Move(Square.E1, Square.E2))
    board.unmake_move()
    assert board.halfmove_clock == 7
    assert board.fullmove_number == 3


def test_from_simple_fen_unchanged() -> None:
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w"
    board = Board.from_simple_fen(fen)
    assert board.to_simple_fen() == fen
    assert board.castling_rights == CASTLE_ALL
    assert board.en_passant_target is None


def test_en_passant_from_full_fen_generates_capture() -> None:
    board = Board.from_fen("8/8/8/3p1P2/8/8/8/4K3 w - e6 0 1")
    ep_moves = [move for move in board.generate_moves() if move.flags == MoveFlag.EN_PASSANT]
    assert len(ep_moves) == 1
    assert ep_moves[0] == Move(Square.F5, Square.E6, flags=MoveFlag.EN_PASSANT)
