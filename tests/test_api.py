"""API integration tests."""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from api.games import _game_to_loaded
from api.main import app
from search import AnalysisUpdate, ScoredMove

SAMPLE_PGN = """[Event "Test Game"]
[Site "Local"]
[Date "2026.05.31"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 1-0
"""


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_static_eval(client: TestClient) -> None:
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    response = client.get("/api/position/eval", params={"fen": fen})
    assert response.status_code == 200
    body = response.json()
    assert "static_eval" in body
    assert isinstance(body["static_eval"], int)


def test_game_to_loaded_shape() -> None:
    loaded = _game_to_loaded("abcd1234", SAMPLE_PGN)
    assert loaded.lichess_id == "abcd1234"
    assert len(loaded.moves) == 4
    assert loaded.headers["White"] == "Alice"
    assert loaded.moves[0].san == "e4"


@patch("api.games.fetch_lichess_pgn", new_callable=AsyncMock)
def test_load_lichess_game(mock_fetch: AsyncMock, client: TestClient) -> None:
    mock_fetch.return_value = SAMPLE_PGN
    response = client.post("/api/games/lichess", json={"url_or_id": "abcd1234"})
    assert response.status_code == 200
    body = response.json()
    assert body["lichess_id"] == "abcd1234"
    assert len(body["moves"]) == 4
    assert body["headers"]["Black"] == "Bob"


@patch("api.analysis.analyze")
def test_analyze_sse(mock_analyze, client: TestClient) -> None:
    def fake_analyze(board, *, deadline, on_update=None):
        update = AnalysisUpdate(
            depth=1,
            static_eval=42,
            top_moves=[
                ScoredMove(san="e4", score_cp=42, depth=1, pv=["e4"]),
            ],
            elapsed_ms=5,
        )
        if on_update is not None:
            on_update(update)
        return [update]

    mock_analyze.side_effect = fake_analyze
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    with client.stream(
        "GET",
        "/api/analyze",
        params={"fen": fen, "session": "test-session-1"},
    ) as response:
        assert response.status_code == 200
        events: list[tuple[str, dict]] = []
        event_name = "message"
        data_lines: list[str] = []
        started = time.monotonic()
        for line in response.iter_lines():
            if time.monotonic() - started > 5:
                break
            if not line:
                if data_lines:
                    events.append((event_name, json.loads("\n".join(data_lines))))
                    data_lines = []
                if events:
                    break
                continue
            if line.startswith("event:"):
                event_name = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].strip())

    assert events
    assert events[0][0] == "update"
    assert events[0][1]["top_moves"][0]["san"] == "e4"


def test_cancel_analysis(client: TestClient) -> None:
    response = client.post("/api/analyze/cancel", json={"session": "missing-session"})
    assert response.status_code == 200
    assert response.json()["cancelled"] is False

    from api.analysis import session_manager

    session_manager.ensure_session("cancel-me")
    cancelled = client.post("/api/analyze/cancel", json={"session": "cancel-me"})
    assert cancelled.json()["cancelled"] is True
