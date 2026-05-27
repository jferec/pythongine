from board import Board, Color, Piece, PieceKind, Square


def test_initial_board_position() -> None:
    board = Board()

    back_rank = [
        PieceKind.ROOK,
        PieceKind.KNIGHT,
        PieceKind.BISHOP,
        PieceKind.QUEEN,
        PieceKind.KING,
        PieceKind.BISHOP,
        PieceKind.KNIGHT,
        PieceKind.ROOK,
    ]

    for file_index, piece_kind in enumerate(back_rank):
        assert board[Square(file_index)] == Piece(piece_kind, Color.WHITE)
        assert board[Square(8 + file_index)] == Piece(PieceKind.PAWN, Color.WHITE)
        assert board[Square(48 + file_index)] == Piece(PieceKind.PAWN, Color.BLACK)
        assert board[Square(56 + file_index)] == Piece(piece_kind, Color.BLACK)

    for square_index in range(Square.A3, Square.H6 + 1):
        assert board[Square(square_index)] is None
