"""Lichess game loading and in-memory game store."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

import httpx
from fastapi import HTTPException

from board import Board
from pgn import parse_standard_game

LICHESS_EXPORT_URL = "https://lichess.org/game/export/{game_id}"
LICHESS_GAME_ID_RE = re.compile(r"^[a-zA-Z0-9]{8}$")


@dataclass
class MoveRecord:
    ply: int
    san: str
    fen: str


@dataclass
class LoadedGame:
    id: str
    lichess_id: str
    headers: dict[str, str]
    start_fen: str
    moves: list[MoveRecord]


_games: dict[str, LoadedGame] = {}


def parse_lichess_game_id(url_or_id: str) -> str | None:
    """Extract an 8-character Lichess game id from ``url_or_id``."""
    text = url_or_id.strip()
    if LICHESS_GAME_ID_RE.match(text):
        return text
    match = re.search(r"lichess\.org/(?:embed/)?(?:game/)?([a-zA-Z0-9]{8})", text)
    if match:
        return match.group(1)
    return None


async def fetch_lichess_pgn(game_id: str) -> str:
    """Download PGN text for ``game_id`` from Lichess."""
    url = LICHESS_EXPORT_URL.format(game_id=game_id)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
    if response.status_code == 404:
        raise HTTPException(status_code=404, detail=f"Lichess game not found: {game_id}")
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Lichess returned status {response.status_code}",
        )
    return response.text


def _game_to_loaded(lichess_id: str, pgn_text: str) -> LoadedGame:
    try:
        game = parse_standard_game(pgn_text)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    Board.from_fen(game.start_fen)
    moves = [
        MoveRecord(ply=index + 1, san=step.san, fen=step.expected_fen)
        for index, step in enumerate(game.steps)
    ]
    loaded = LoadedGame(
        id=str(uuid.uuid4()),
        lichess_id=lichess_id,
        headers=dict(game.headers),
        start_fen=game.start_fen,
        moves=moves,
    )
    _games[loaded.id] = loaded
    return loaded


async def load_lichess_game(url_or_id: str) -> LoadedGame:
    game_id = parse_lichess_game_id(url_or_id)
    if game_id is None:
        raise HTTPException(status_code=400, detail="Invalid Lichess game id or URL")
    pgn_text = await fetch_lichess_pgn(game_id)
    return _game_to_loaded(game_id, pgn_text)


def get_game(game_id: str) -> LoadedGame:
    loaded = _games.get(game_id)
    if loaded is None:
        raise HTTPException(status_code=404, detail=f"Game not found: {game_id}")
    return loaded


def fen_at_ply(loaded: LoadedGame, ply: int) -> str:
    if ply < 0 or ply > len(loaded.moves):
        raise HTTPException(status_code=400, detail=f"Invalid ply: {ply}")
    if ply == 0:
        return loaded.start_fen
    return loaded.moves[ply - 1].fen


def loaded_game_to_dict(loaded: LoadedGame) -> dict:
    return {
        "id": loaded.id,
        "lichess_id": loaded.lichess_id,
        "headers": loaded.headers,
        "start_fen": loaded.start_fen,
        "moves": [
            {"ply": move.ply, "san": move.san, "fen": move.fen}
            for move in loaded.moves
        ],
    }
