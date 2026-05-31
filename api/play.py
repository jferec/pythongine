"""Play-vs-engine API: legal moves, human apply, engine best move."""

from __future__ import annotations

import asyncio
import time
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, Field

from board import Board
from eval import is_checkmate, is_stalemate
from move import MoveFlag
from pieces import Color, PieceKind, Square, square_to_name
from pgn import STARTING_FEN
from san import AmbiguousMoveError, IllegalMoveError, match_drag, match_move, move_to_san
from search import best_move

PlayerColor = Literal["white", "black"]
GameStatus = Literal["ongoing", "checkmate", "stalemate"]
PlayerResult = Literal["win", "loss", "draw"]

_PROMOTION_FROM_CHAR = {
    "Q": PieceKind.QUEEN,
    "R": PieceKind.ROOK,
    "B": PieceKind.BISHOP,
    "N": PieceKind.KNIGHT,
}
_PROMOTION_TO_CHAR = {kind: char for char, kind in _PROMOTION_FROM_CHAR.items()}


class ApplyMoveRequest(BaseModel):
    fen: str
    from_square: str = Field(alias="from")
    to_square: str = Field(alias="to")
    promotion: str | None = None
    player_color: PlayerColor

    model_config = {"populate_by_name": True}


class EngineMoveRequest(BaseModel):
    fen: str
    think_ms: int = Field(ge=1000, le=180_000)
    player_color: PlayerColor


def _parse_player_color(color: PlayerColor) -> Color:
    return Color.WHITE if color == "white" else Color.BLACK


def _promotion_kind(value: str | None) -> PieceKind | None:
    if value is None:
        return None
    kind = _PROMOTION_FROM_CHAR.get(value.upper())
    if kind is None:
        raise HTTPException(status_code=400, detail=f"Invalid promotion: {value!r}")
    return kind


def _has_king(board: Board, color: Color) -> bool:
    for square in Square:
        piece = board[square]
        if piece is not None and piece.kind == PieceKind.KING and piece.color == color:
            return True
    return False


def _game_status(board: Board) -> GameStatus:
    if not _has_king(board, Color.WHITE) or not _has_king(board, Color.BLACK):
        return "checkmate"
    if is_checkmate(board):
        return "checkmate"
    if is_stalemate(board):
        return "stalemate"
    return "ongoing"


def _player_result(board: Board, player_color: Color) -> PlayerResult | None:
    status = _game_status(board)
    if status == "stalemate":
        return "draw"
    if status == "checkmate":
        if board.side_to_move == player_color:
            return "loss"
        return "win"
    return None


def _move_record(move, board: Board) -> dict:
    promotion = None
    if move.flags == MoveFlag.PROMOTION and move.promotion is not None:
        promotion = _PROMOTION_TO_CHAR[move.promotion]
    return {
        "from": square_to_name(move.from_square),
        "to": square_to_name(move.to_square),
        "san": move_to_san(board, move).rstrip("#+"),
        "promotion": promotion,
    }


def legal_moves(fen: str) -> dict:
    try:
        board = Board.from_fen(fen)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    moves = [_move_record(move, board) for move in board.generate_moves()]
    return {"fen": fen, "moves": moves}


def apply_move(body: ApplyMoveRequest) -> dict:
    try:
        board = Board.from_fen(body.fen)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    player = _parse_player_color(body.player_color)
    if board.side_to_move != player:
        raise HTTPException(status_code=400, detail="Not the player's turn")

    try:
        move = match_drag(
            board,
            body.from_square,
            body.to_square,
            promotion=_promotion_kind(body.promotion),
        )
    except IllegalMoveError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except AmbiguousMoveError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    san = move_to_san(board, move).rstrip("#+")
    board.make_move(move)
    fen = board.to_fen()
    status = _game_status(board)
    result = _player_result(board, player)
    return {
        "san": san,
        "fen": fen,
        "status": status,
        "player_result": result,
    }


def engine_move(body: EngineMoveRequest) -> dict:
    try:
        board = Board.from_fen(body.fen)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    player = _parse_player_color(body.player_color)
    engine = ~player
    if board.side_to_move != engine:
        raise HTTPException(status_code=400, detail="Not the engine's turn")

    deadline = time.monotonic() + body.think_ms / 1000.0
    scored = best_move(board, deadline=deadline)
    if scored is None:
        raise HTTPException(status_code=500, detail="Engine found no move")

    move = match_move(board, scored.san.rstrip("#+"))
    san = move_to_san(board, move).rstrip("#+")
    board.make_move(move)
    fen = board.to_fen()
    status = _game_status(board)
    result = _player_result(board, player)
    return {
        "san": san,
        "fen": fen,
        "status": status,
        "player_result": result,
        "score_cp": scored.score_cp,
        "depth": scored.depth,
    }


async def engine_move_async(body: EngineMoveRequest) -> dict:
    return await asyncio.to_thread(engine_move, body)


def new_game_fen() -> str:
    return STARTING_FEN
