"""Iterative-deepening negamax search with root multi-PV."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

from board import Board
from eval import MATE_SCORE, evaluate, is_checkmate, is_stalemate
from move import Move
from pieces import Color, PieceKind, Square
from san import move_to_san

INF = 1_000_000
MAX_DEPTH = 64
TOP_MOVES = 5


class SearchTimeout(Exception):
    """Raised when the search deadline is reached."""


@dataclass(frozen=True)
class ScoredMove:
    san: str
    score_cp: int
    depth: int
    pv: list[str]


@dataclass(frozen=True)
class AnalysisUpdate:
    depth: int
    static_eval: int
    top_moves: list[ScoredMove]
    elapsed_ms: int


def _has_king(board: Board, color: Color) -> bool:
    for square in Square:
        piece = board[square]
        if piece is not None and piece.kind == PieceKind.KING and piece.color == color:
            return True
    return False


def _negamax(
    board: Board,
    depth: int,
    alpha: int,
    beta: int,
    deadline: float,
    ply: int,
) -> tuple[int, list[str]]:
    if time.monotonic() >= deadline:
        raise SearchTimeout

    if not _has_king(board, board.side_to_move):
        return -MATE_SCORE + ply, []
    if is_checkmate(board):
        return -MATE_SCORE + ply, []
    if is_stalemate(board):
        return 0, []

    if depth == 0:
        return evaluate(board), []

    best_score = -INF
    best_pv: list[str] = []
    for move in board.generate_moves():
        if time.monotonic() >= deadline:
            raise SearchTimeout
        san = move_to_san(board, move)
        board.make_move(move)
        try:
            score, child_pv = _negamax(board, depth - 1, -beta, -alpha, deadline, ply + 1)
        finally:
            board.unmake_move()
        score = -score
        if score > best_score:
            best_score = score
            best_pv = [san, *child_pv]
        alpha = max(alpha, score)
        if alpha >= beta:
            break
    return best_score, best_pv


def analyze(
    board: Board,
    *,
    deadline: float,
    on_update: Callable[[AnalysisUpdate], None] | None = None,
    on_progress: Callable[[str], None] | None = None,
) -> list[AnalysisUpdate]:
    """Run iterative deepening until ``deadline``; return all depth snapshots."""
    start = time.monotonic()
    static_eval = evaluate(board)
    root_moves = board.generate_moves()
    updates: list[AnalysisUpdate] = []
    last_top: list[ScoredMove] = []

    def progress(message: str) -> None:
        logger.info(message)
        if on_progress is not None:
            on_progress(message)

    progress(
        f"Analysis started: {len(root_moves)} root moves, static eval {static_eval} cp"
    )

    for depth in range(1, MAX_DEPTH + 1):
        if time.monotonic() >= deadline:
            progress(f"Deadline reached before depth {depth}")
            break
        progress(f"Searching depth {depth}...")
        scored: list[ScoredMove] = []
        try:
            for index, move in enumerate(root_moves, start=1):
                if time.monotonic() >= deadline:
                    raise SearchTimeout
                san = move_to_san(board, move)
                board.make_move(move)
                try:
                    score, pv = _negamax(board, depth - 1, -INF, INF, deadline, ply=1)
                finally:
                    board.unmake_move()
                scored.append(
                    ScoredMove(
                        san=san,
                        score_cp=-score,
                        depth=depth,
                        pv=[san, *pv],
                    )
                )
                progress(
                    f"Depth {depth}: scored {index}/{len(root_moves)} ({san}, {-score} cp)"
                )
        except SearchTimeout:
            progress(f"Timeout during depth {depth}")
            break

        if not scored:
            break

        scored.sort(key=lambda item: item.score_cp, reverse=True)
        last_top = scored[:TOP_MOVES]
        elapsed_ms = int((time.monotonic() - start) * 1000)
        best = last_top[0]
        progress(
            f"Depth {depth} complete in {elapsed_ms}ms — "
            f"best {best.san} ({best.score_cp} cp)"
        )
        update = AnalysisUpdate(
            depth=depth,
            static_eval=static_eval,
            top_moves=last_top,
            elapsed_ms=elapsed_ms,
        )
        updates.append(update)
        if on_update is not None:
            on_update(update)

    total_ms = int((time.monotonic() - start) * 1000)
    progress(f"Analysis finished after {total_ms}ms ({len(updates)} depths)")
    return updates
