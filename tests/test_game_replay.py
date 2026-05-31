from pathlib import Path

import pytest

from game_replay import replay_game
from pgn import load_game, parse_game

GAME_DIR = Path(__file__).parent / "assets" / "games"


@pytest.mark.parametrize("path", sorted(GAME_DIR.glob("*.pgn")), ids=lambda p: p.name)
def test_replay_game_forward(path: Path) -> None:
    replay_game(load_game(path), verify_unmake=False)


@pytest.mark.parametrize("path", sorted(GAME_DIR.glob("*.pgn")), ids=lambda p: p.name)
def test_replay_game_with_unmake(path: Path) -> None:
    replay_game(load_game(path), verify_unmake=True)


def test_parse_game_rejects_variations() -> None:
    pgn = '1. e4 { [%fen "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"] } (1... c5) 1... e5 *'
    with pytest.raises(ValueError, match="variations"):
        parse_game(pgn)


def test_parse_game_requires_fen_comments() -> None:
    with pytest.raises(ValueError, match="no \\[%fen"):
        parse_game("1. e4 e5 *")


def test_parse_standard_game_replays_mainline() -> None:
    from pgn import parse_standard_game

    game = parse_standard_game(
        '[Event "Test"]\n1. e4 e5 2. Nf3 Nc6 1-0'
    )
    assert len(game.steps) == 4
    assert game.steps[0].san == "e4"
    assert game.steps[-1].expected_fen.endswith("- 2 3")


def test_parse_standard_game_strips_comments_and_variations() -> None:
    from pgn import parse_standard_game

    game = parse_standard_game(
        '[Event "Test"]\n1. e4 { [%clk 0:05:00] } e5 (1... c5) 2. Nf3 *'
    )
    assert [step.san for step in game.steps] == ["e4", "e5", "Nf3"]


def test_parse_standard_game_stops_at_null_move() -> None:
    from pgn import parse_standard_game

    game = parse_standard_game('[Event "Test"]\n1. e4 e5 2. Nf3 Z0 2... Nc6 *')
    assert [step.san for step in game.steps] == ["e4", "e5", "Nf3"]
