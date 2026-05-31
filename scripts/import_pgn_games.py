#!/usr/bin/env python3
"""Convert standard PGN files into pythongine replay fixtures."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pgn import encode_fixture_pgn, parse_standard_game, split_pgn_games


def _read_source(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    raise FileNotFoundError(path)


def _fetch_url(url: str) -> str:
    try:
        with urlopen(url, timeout=30) as response:
            return response.read().decode("utf-8")
    except URLError as error:
        raise SystemExit(f"Failed to fetch {url}: {error}") from error


def _source_comment(path: Path | None, url: str | None) -> str:
    if url:
        return url
    if path is not None:
        try:
            return str(path.relative_to(ROOT))
        except ValueError:
            return str(path)
    return "unknown"


def import_game(
    text: str,
    *,
    output: Path,
    source: str,
    game_index: int = 0,
) -> None:
    games = split_pgn_games(text)
    if not games:
        raise SystemExit("No games found in input")
    if game_index >= len(games):
        raise SystemExit(
            f"Game index {game_index} out of range ({len(games)} games in file)"
        )

    fixture = parse_standard_game(games[game_index])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        encode_fixture_pgn(fixture, source=source),
        encoding="utf-8",
    )
    print(f"Wrote {output} ({len(fixture.steps)} moves)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        type=Path,
        nargs="?",
        help="Standard PGN file (default: read stdin)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Fixture PGN output path",
    )
    parser.add_argument(
        "--url",
        help="Download PGN from this URL instead of reading a local file",
    )
    parser.add_argument(
        "--game-index",
        type=int,
        default=0,
        help="Which game to import from a multi-game PGN (default: 0)",
    )
    parser.add_argument(
        "--source",
        help="Source attribution stored in the fixture header comment",
    )
    args = parser.parse_args()

    if args.url:
        text = _fetch_url(args.url)
        source = args.source or args.url
    elif args.input:
        text = _read_source(args.input)
        source = args.source or _source_comment(args.input, None)
    else:
        text = sys.stdin.read()
        source = args.source or "stdin"

    import_game(
        text,
        output=args.output,
        source=source,
        game_index=args.game_index,
    )


if __name__ == "__main__":
    main()
