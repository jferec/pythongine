from board import Board, MoveFlag
from move import Move
from pieces import PieceKind, Square
from san import match_move


def test_pawn_push() -> None:
    board = Board()
    move = match_move(board, "e4")
    assert move == Move(Square.E2, Square.E4)


def test_pawn_capture() -> None:
    board = Board.from_fen("8/8/8/3p4/4P3/8/8/4K3 w - - 0 1")
    move = match_move(board, "exd5")
    assert move.to_square == Square.D5
    assert move.flags == MoveFlag.CAPTURE


def test_knight_move() -> None:
    board = Board.from_fen("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")
    move = match_move(board, "Nf6")
    assert move.from_square == Square.G8
    assert move.to_square == Square.F6


def test_knight_disambiguation() -> None:
    board = Board.from_fen("4k3/8/8/8/2N1N3/8/8/4K3 w - - 0 1")
    move = match_move(board, "Ncd6")
    assert move.from_square == Square.C4
    assert move.to_square == Square.D6


def test_kingside_castle() -> None:
    board = Board.from_fen(
        "r1bqkbnr/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
    )
    move = match_move(board, "O-O")
    assert move.flags == MoveFlag.CASTLE_KINGSIDE


def test_promotion() -> None:
    board = Board.from_fen("8/4P3/8/8/8/8/4K2k/8 w - - 0 1")
    move = match_move(board, "e8=Q")
    assert move.flags == MoveFlag.PROMOTION
    assert move.promotion == PieceKind.QUEEN


def test_en_passant() -> None:
    board = Board.from_fen("4k3/8/8/4pP2/8/8/8/4K3 w - e6 0 2")
    move = match_move(board, "fxe6")
    assert move.flags == MoveFlag.EN_PASSANT


def test_strips_check_and_mate_suffix() -> None:
    board = Board.from_fen("7k1/6Q1/8/8/8/8/8/7K w - - 0 1")
    move = match_move(board, "Qf7#")
    assert move.to_square == Square.F7
