from enum import IntEnum, Enum

from typing import NamedTuple


class Color(IntEnum):
    WHITE = 0
    BLACK = 1

    def __invert__(self):
        if self == self.WHITE:
            return self.BLACK
        else:
            return self.WHITE


class Piece(Enum):
    def __init__(self, color: Color):
        self.color = color

    PAWN = 1
    KNIGHT = 2
    BISHOP = 3
    ROOK = 4
    QUEEN = 5
    KING = 6


class Square(NamedTuple):
    """
    Represents a square on a chessboard.


    Attributes:
        rank: Row index, 0-7 (0 is white's back rank).
        file: Column index, 0-7 (0 is the a-file).
    """

    rank: int
    file: int

    def __new__(cls, rank: int, file: int):
        if not (0 <= rank < 8):
            raise ValueError(f"rank out of bounds: {rank}")
        if not (0 <= file < 8):
            raise ValueError(f"file out of bounds: {file}")
        return super().__new__(cls, (rank, file))

    @property
    def board_index(self) -> int:
        return 8 * self.rank + self.file
