import time

from board import Board
from eval import MATE_SCORE
from search import INF, AnalysisUpdate, analyze
from san import match_move, move_to_san


def test_mate_in_one_picks_correct_top_move() -> None:
    board = Board.from_fen("7k1/6Q1/8/8/8/8/8/7K w - - 0 1")
    deadline = time.monotonic() + 5.0
    updates = analyze(board, deadline=deadline)
    assert updates
    top = updates[-1].top_moves[0]
    assert top.score_cp >= MATE_SCORE - 100
    assert top.san.endswith("#")


def test_stalemate_scores_zero() -> None:
    board = Board.from_fen("7k/5Q2/8/8/8/8/8/K7 b - - 0 1")
    from eval import is_stalemate
    from search import _negamax

    assert is_stalemate(board)
    score, _ = _negamax(board, 1, -INF, INF, time.monotonic() + 5.0, ply=1)
    assert score == 0


def test_timeout_stops_cleanly() -> None:
    board = Board()
    deadline = time.monotonic() + 0.01
    updates = analyze(board, deadline=deadline)
    assert isinstance(updates, list)


def test_on_update_callback() -> None:
    board = Board.from_fen("7k1/6Q1/8/8/8/8/8/7K w - - 0 1")
    seen: list[AnalysisUpdate] = []
    analyze(board, deadline=time.monotonic() + 5.0, on_update=seen.append)
    assert seen
    assert seen[-1].depth >= 1
