from board import Board, Color, PieceKind, Square
from eval import evaluate, is_checkmate, is_stalemate, psqt_bonus

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def test_starting_position_is_neutral() -> None:
    board = Board.from_fen(STARTING_FEN)
    assert evaluate(board) == 0


def test_material_advantage_white_to_move() -> None:
    board = Board.from_fen("8/8/8/8/8/8/4Q3/4K3 w - - 0 1")
    assert evaluate(board) == 900


def test_material_advantage_black_to_move() -> None:
    board = Board.from_fen("8/8/8/8/8/8/4Q3/4K3 b - - 0 1")
    assert evaluate(board) == -900


def test_symmetric_material_is_neutral() -> None:
    board = Board.from_fen("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
    assert evaluate(board) == 0


def test_knight_on_center_scores_higher_than_corner() -> None:
    center = Board.from_fen("8/8/8/8/4N3/8/8/4K2k w - - 0 1")
    corner = Board.from_fen("N7/8/8/8/8/8/8/4K2k w - - 0 1")
    assert evaluate(center) > evaluate(corner)


def test_castled_king_scores_higher_than_central_king() -> None:
    castled = Board.from_fen("6k1/8/8/8/8/8/8/5RK1 w - - 0 1")
    central = Board.from_fen("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
    assert evaluate(castled) > evaluate(central)


def test_psqt_bonus_mirrors_black_pieces() -> None:
    white_e4 = psqt_bonus(PieceKind.KNIGHT, Square.E4, Color.WHITE)
    black_e5 = psqt_bonus(PieceKind.KNIGHT, Square.E5, Color.BLACK)
    assert white_e4 == black_e5


def test_promoted_piece_counts_as_queen_material() -> None:
    board = Board.from_fen("4Q3/8/8/8/8/8/4K2k/8 w - - 0 1")
    assert evaluate(board) >= 900


def test_is_checkmate() -> None:
    board = Board.from_fen("7k1/6Q1/6K1/8/8/8/8/8 b - - 0 1")
    assert is_checkmate(board)
    assert not is_stalemate(board)


def test_is_stalemate() -> None:
    board = Board.from_fen("7k/5Q2/5K2/8/8/8/8/8 b - - 0 1")
    assert is_stalemate(board)
    assert not is_checkmate(board)


def test_non_terminal_position() -> None:
    board = Board.from_fen(STARTING_FEN)
    assert not is_checkmate(board)
    assert not is_stalemate(board)
