from board import Board
from pgn import Game
from san import match_move


class ReplayError(AssertionError):
    """Raised when replayed position does not match the expected FEN."""


def replay_game(game: Game, *, verify_unmake: bool = False) -> None:
    """Apply ``game`` moves and assert FEN checkpoints; optionally verify undo."""
    board = Board.from_fen(game.start_fen)
    if board.to_fen() != game.start_fen:
        raise ReplayError(
            f"Start FEN mismatch: expected {game.start_fen}, got {board.to_fen()}"
        )

    for step in game.steps:
        fen_before = board.to_fen()
        move = match_move(board, step.san)
        board.make_move(move)
        fen_after = board.to_fen()
        if fen_after != step.expected_fen:
            raise ReplayError(
                f"After {step.san!r}: expected {step.expected_fen}, got {fen_after}"
            )

        if verify_unmake:
            board.unmake_move()
            if board.to_fen() != fen_before:
                raise ReplayError(
                    f"After unmake of {step.san!r}: expected {fen_before}, "
                    f"got {board.to_fen()}"
                )
            board.make_move(move)
            if board.to_fen() != step.expected_fen:
                raise ReplayError(
                    f"After re-make of {step.san!r}: expected {step.expected_fen}, "
                    f"got {board.to_fen()}"
                )
