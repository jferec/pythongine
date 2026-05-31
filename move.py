from dataclasses import dataclass
from enum import Enum, auto

from pieces import PieceKind, Square

_PROMOTION_CHARS = {
    PieceKind.QUEEN: "q",
    PieceKind.ROOK: "r",
    PieceKind.BISHOP: "b",
    PieceKind.KNIGHT: "n",
}


class MoveFlag(Enum):
    QUIET = auto()
    CAPTURE = auto()
    PROMOTION = auto()
    CASTLE_KINGSIDE = auto()
    CASTLE_QUEENSIDE = auto()
    EN_PASSANT = auto()


@dataclass(frozen=True, slots=True)
class Move:
    from_square: Square
    to_square: Square
    promotion: PieceKind | None = None
    flags: MoveFlag = MoveFlag.QUIET

    def __repr__(self) -> str:
        notation = (
            f"{_square_name(self.from_square)}{_square_name(self.to_square)}"
        )
        if self.flags in (MoveFlag.CASTLE_KINGSIDE, MoveFlag.CASTLE_QUEENSIDE):
            return notation
        if self.promotion is not None:
            notation += _PROMOTION_CHARS[self.promotion]
        return notation


def _square_name(square: Square) -> str:
    return f"{chr(ord('a') + square.file)}{square.rank + 1}"
