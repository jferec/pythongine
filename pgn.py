import re
from dataclasses import dataclass
from pathlib import Path

from board import Board
from san import match_move

STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

_HEADER_RE = re.compile(r'^\[(\w+)\s+"((?:\\"|[^"])*)"\]\s*$')
_FEN_TAG_RE = re.compile(r'\[%fen\s+"((?:\\"|[^"])*)"\]')
_MOVE_NUMBER_RE = re.compile(r"^\d+\.+\.*$")
_EMBEDDED_MOVE_RE = re.compile(r"^\d+\.+\.*(.+)$")
_NAG_RE = re.compile(r"^\$\d+$")
_RESULT_TOKENS = frozenset({"1-0", "0-1", "1/2-1/2", "*"})
_SKIP_MOVE_TOKENS = frozenset({"--", "Z0", "..."})


@dataclass(frozen=True)
class GameStep:
    san: str
    expected_fen: str


@dataclass(frozen=True)
class Game:
    headers: dict[str, str]
    start_fen: str
    steps: list[GameStep]


def load_game(path: Path | str) -> Game:
    """Load and parse a PGN file from ``path``."""
    return parse_game(Path(path).read_text(encoding="utf-8"))


def parse_game(text: str) -> Game:
    """Parse PGN text with ``[%fen "..."]`` comments after each move."""
    headers: dict[str, str] = {}
    movetext_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        header_match = _HEADER_RE.match(stripped)
        if header_match:
            tag, value = header_match.groups()
            headers[tag] = value.replace('\\"', '"')
            continue
        movetext_lines.append(stripped)

    movetext = " ".join(movetext_lines)
    if not movetext:
        raise ValueError("PGN contains no movetext")

    if "(" in movetext:
        raise ValueError("PGN variations are not supported")

    fen_comments = _extract_fen_comments(movetext)
    tokens = _tokenize_movetext(movetext)

    if len(tokens) != len(fen_comments):
        raise ValueError(
            f"Expected {len(tokens)} [%fen] comments for {len(tokens)} moves, "
            f"found {len(fen_comments)}"
        )

    start_fen = headers.get("FEN", STARTING_FEN)
    Board.from_fen(start_fen)

    steps = [
        GameStep(san=san, expected_fen=fen)
        for san, fen in zip(tokens, fen_comments, strict=True)
    ]
    return Game(headers=headers, start_fen=start_fen, steps=steps)


def _extract_fen_comments(movetext: str) -> list[str]:
    comments = _FEN_TAG_RE.findall(movetext)
    if not comments:
        raise ValueError("PGN movetext contains no [%fen \"...\"] comments")
    return [comment.replace('\\"', '"') for comment in comments]


def _tokenize_movetext(movetext: str) -> list[str]:
    movetext = _strip_comments(movetext)
    raw_tokens = movetext.split()
    tokens: list[str] = []
    for token in raw_tokens:
        san = _coerce_move_token(token)
        if san is not None:
            tokens.append(san)
    if not tokens:
        raise ValueError("PGN movetext contains no moves")
    return tokens


def split_pgn_games(text: str) -> list[str]:
    """Split a multi-game PGN file into individual game texts."""
    games: list[str] = []
    current: list[str] = []
    in_movetext = False

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("["):
            if in_movetext and current:
                games.append("\n".join(current))
                current = []
                in_movetext = False
            current.append(line)
            continue
        in_movetext = True
        current.append(line)

    if current:
        games.append("\n".join(current))
    return games


def parse_standard_game(text: str) -> Game:
    """Parse standard PGN mainline (no ``[%fen]`` comments) and replay moves."""
    headers: dict[str, str] = {}
    movetext_lines: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        header_match = _HEADER_RE.match(stripped)
        if header_match:
            tag, value = header_match.groups()
            headers[tag] = value.replace('\\"', '"')
            continue
        movetext_lines.append(stripped)

    movetext = " ".join(movetext_lines)
    if not movetext:
        raise ValueError("PGN contains no movetext")

    start_fen = headers.get("FEN", STARTING_FEN)
    sans = _tokenize_mainline_movetext(movetext)
    return replay_sans(headers, start_fen, sans)


def replay_sans(headers: dict[str, str], start_fen: str, sans: list[str]) -> Game:
    """Replay SAN mainline moves and attach FEN checkpoints."""
    board = Board.from_fen(start_fen)
    steps: list[GameStep] = []
    for san in sans:
        move = match_move(board, san)
        board.make_move(move)
        steps.append(GameStep(san=san, expected_fen=board.to_fen()))
    return Game(headers=headers, start_fen=start_fen, steps=steps)


def encode_fixture_pgn(game: Game, *, source: str | None = None) -> str:
    """Serialize a replayed game as a pythongine fixture PGN."""
    lines: list[str] = []
    if source:
        lines.append(f"# Source: {source}")

    header_order = (
        "Event",
        "Site",
        "Date",
        "Round",
        "White",
        "Black",
        "Result",
        "ECO",
        "SetUp",
        "FEN",
    )
    seen: set[str] = set()
    for tag in header_order:
        if tag in game.headers:
            lines.append(f'[{tag} "{game.headers[tag]}"]')
            seen.add(tag)
    for tag, value in game.headers.items():
        if tag not in seen:
            lines.append(f'[{tag} "{value}"]')

    if lines and not lines[-1].startswith("#") and lines[-1].startswith("["):
        lines.append("")

    movetext_parts: list[str] = []
    for index, step in enumerate(game.steps):
        movetext_parts.append(_move_number_prefix(index, game.start_fen))
        movetext_parts.append(step.san)
        movetext_parts.append(f'{{ [%fen "{step.expected_fen}"] }}')

    result = game.headers.get("Result", "*")
    movetext_parts.append(result)
    lines.append(" ".join(movetext_parts))
    return "\n".join(lines) + "\n"


def _tokenize_mainline_movetext(movetext: str) -> list[str]:
    movetext = _strip_variations(movetext)
    movetext = _strip_comments(movetext)
    raw_tokens = movetext.split()
    tokens: list[str] = []
    for token in raw_tokens:
        san = _coerce_move_token(token)
        if san is None:
            if token in _SKIP_MOVE_TOKENS:
                break
            continue
        tokens.append(san)
    if not tokens:
        raise ValueError("PGN movetext contains no moves")
    return tokens


def _coerce_move_token(token: str) -> str | None:
    if token in _RESULT_TOKENS or token in _SKIP_MOVE_TOKENS:
        return None
    if _MOVE_NUMBER_RE.match(token) or _NAG_RE.match(token):
        return None
    embedded = _EMBEDDED_MOVE_RE.match(token)
    if embedded:
        return embedded.group(1) or None
    return token


def _move_number_prefix(index: int, start_fen: str) -> str:
    starts_black = start_fen.split()[1] == "b"
    fullmove = (index // 2) + 1
    is_black = index % 2 == 1
    if starts_black:
        is_black = not is_black
        if is_black:
            return f"{fullmove}..."
        return f"{fullmove + 1}."
    if is_black:
        return f"{fullmove}..."
    return f"{fullmove}."


def _strip_comments(movetext: str) -> str:
    return re.sub(r"\{[^}]*\}", " ", movetext)


def _strip_variations(movetext: str) -> str:
    result: list[str] = []
    depth = 0
    for character in movetext:
        if character == "(":
            depth += 1
        elif character == ")":
            if depth > 0:
                depth -= 1
        elif depth == 0:
            result.append(character)
    return "".join(result)
