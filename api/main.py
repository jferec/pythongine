"""FastAPI application for chess analysis UI."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from api.analysis import session_manager, static_eval
from api.games import (
    fen_at_ply,
    get_game,
    load_lichess_game,
    loaded_game_to_dict,
    parse_lichess_game_id,
)
from api.play import (
    ApplyMoveRequest,
    EngineMoveRequest,
    apply_move,
    engine_move_async,
    legal_moves,
)

WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="pythongine analysis API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class LichessLoadRequest(BaseModel):
    url_or_id: str


class CancelRequest(BaseModel):
    session: str


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/games/lichess")
async def post_lichess_game(body: LichessLoadRequest) -> dict:
    loaded = await load_lichess_game(body.url_or_id)
    return loaded_game_to_dict(loaded)


@app.get("/api/games/lichess/{lichess_id}")
async def get_lichess_game(lichess_id: str) -> dict:
    if parse_lichess_game_id(lichess_id) is None:
        raise HTTPException(status_code=400, detail="Invalid Lichess game id")
    loaded = await load_lichess_game(lichess_id)
    return loaded_game_to_dict(loaded)


@app.get("/api/games/{game_id}")
async def get_loaded_game(game_id: str) -> dict:
    return loaded_game_to_dict(get_game(game_id))


@app.get("/api/games/{game_id}/fen")
async def get_game_fen(game_id: str, ply: Annotated[int, Query(ge=0)] = 0) -> dict:
    loaded = get_game(game_id)
    return {"game_id": game_id, "ply": ply, "fen": fen_at_ply(loaded, ply)}


@app.get("/api/position/eval")
async def get_position_eval(fen: str) -> dict:
    try:
        return static_eval(fen)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/analyze")
async def analyze_position(
    fen: str,
    session: Annotated[str, Query(min_length=1)],
) -> StreamingResponse:
    session_manager.ensure_session(session)
    stream = session_manager.stream_analysis(fen, session)
    return StreamingResponse(stream, media_type="text/event-stream")


@app.post("/api/analyze/cancel")
async def cancel_analysis(body: CancelRequest) -> dict:
    cancelled = session_manager.cancel(body.session)
    return {"session": body.session, "cancelled": cancelled}


@app.get("/api/play/legal-moves")
async def get_legal_moves(fen: str) -> dict:
    return legal_moves(fen)


@app.post("/api/play/apply-move")
async def post_apply_move(body: ApplyMoveRequest) -> dict:
    return apply_move(body)


@app.post("/api/play/engine-move")
async def post_engine_move(body: EngineMoveRequest) -> dict:
    return await engine_move_async(body)


def _mount_frontend() -> None:
    index = WEB_DIST / "index.html"
    if not index.exists():
        return

    assets_dir = WEB_DIST / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    async def serve_index() -> FileResponse:
        return FileResponse(index)

    @app.get("/favicon.svg", include_in_schema=False)
    async def serve_favicon() -> FileResponse:
        favicon = WEB_DIST / "favicon.svg"
        if favicon.exists():
            return FileResponse(favicon)
        raise HTTPException(status_code=404)


_mount_frontend()
