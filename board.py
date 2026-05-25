from enum import IntEnum, Enum

from typing import NamedTuple
from dataclasses import dataclass


class Color(IntEnum):
    WHITE = 0
    BLACK = 1

    def __invert__(self):
        if self == self.WHITE:
            return self.BLACK
        else:
            return self.WHITE


class PieceKind(Enum):
    PAWN = 1
    KNIGHT = 2
    BISHOP = 3
    ROOK = 4
    QUEEN = 5
    KING = 6


from typing import NamedTuple


class Piece(NamedTuple):
    kind: PieceKind
    color: Color


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


@dataclass
class Board:
    width: int
    height: int
    __squares: list[Piece]

    def __post_init__(self):
        __squares = []

    def __getitem__(self, square: Square) -> Piece:
        return self.__squares[square.board_index]

    def __setitem__(self, key: Square, value: Piece) -> None:
        self.__squares[key.board_index] = value

    def __initialize_board(self):
        self.__squares[0:8] = [Piece(PieceKind.PAWN, Color.WHITE)] * 8
