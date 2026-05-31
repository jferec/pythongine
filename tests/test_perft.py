from board import Board


def perft(board: Board, depth: int) -> int:
    if depth == 0:
        return 1
    nodes = 0
    for move in board.generate_moves():
        board.make_move(move)
        nodes += perft(board, depth - 1)
        board.unmake_move()
    return nodes


def test_perft_starting_position() -> None:
    board = Board()
    assert perft(board, 1) == 20
    assert perft(board, 2) == 400
    assert perft(board, 3) == 8902
