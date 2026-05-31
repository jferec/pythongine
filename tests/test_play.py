import time

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.play import ApplyMoveRequest, EngineMoveRequest, apply_move, legal_moves
from pgn import STARTING_FEN
from san import AmbiguousMoveError, IllegalMoveError, match_drag

START = STARTING_FEN


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_match_drag_legal_pawn_push() -> None:
    from board import Board

    board = Board()
    move = match_drag(board, "e2", "e4")
    from pieces import Square

    assert move.to_square == Square.E4


def test_match_drag_illegal() -> None:
    from board import Board

    board = Board()
    with pytest.raises(IllegalMoveError):
        match_drag(board, "e2", "e5")


def test_match_drag_promotion_requires_piece() -> None:
    from board import Board

    board = Board.from_fen("8/4P3/8/8/8/8/4K2k/8 w - - 0 1")
    with pytest.raises(AmbiguousMoveError):
        match_drag(board, "e7", "e8")


def test_legal_moves_starting_position() -> None:
    result = legal_moves(START)
    assert len(result["moves"]) == 20


def test_apply_move_e4() -> None:
    result = apply_move(
        ApplyMoveRequest(
            fen=START,
            **{"from": "e2", "to": "e4"},
            player_color="white",
        )
    )
    assert result["san"] == "e4"
    assert result["status"] == "ongoing"
    assert result["player_result"] is None


def test_apply_move_rejects_illegal() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/play/apply-move",
        json={
            "fen": START,
            "from": "e2",
            "to": "e5",
            "player_color": "white",
        },
    )
    assert response.status_code == 400


def test_engine_move_mate_in_one(client: TestClient) -> None:
    fen = "7k1/6Q1/8/8/8/8/8/7K w - - 0 1"
    response = client.post(
        "/api/play/engine-move",
        json={"fen": fen, "think_ms": 5000, "player_color": "black"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "checkmate"
    assert body["player_result"] == "loss"
    assert body["san"].startswith("Q")


def test_engine_move_returns_within_timeout(client: TestClient) -> None:
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    response = client.post(
        "/api/play/engine-move",
        json={"fen": fen, "think_ms": 1000, "player_color": "white"},
    )
    assert response.status_code == 200
    assert "san" in response.json()
