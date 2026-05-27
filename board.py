from dataclasses import dataclass, field
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


class PieceKind(Enum):
    PAWN = 1
    KNIGHT = 2
    BISHOP = 3
    ROOK = 4
    QUEEN = 5
    KING = 6


class Piece(NamedTuple):
    kind: PieceKind
    color: Color


class Square(IntEnum):
    """
    Represents a square on a chessboard.

    Attributes:
        value: Board index, 0-63.
    """

    A1 = 0
    B1 = 1
    C1 = 2
    D1 = 3
    E1 = 4
    F1 = 5
    G1 = 6
    H1 = 7
    A2 = 8
    B2 = 9
    C2 = 10
    D2 = 11
    E2 = 12
    F2 = 13
    G2 = 14
    H2 = 15
    A3 = 16
    B3 = 17
    C3 = 18
    D3 = 19
    E3 = 20
    F3 = 21
    G3 = 22
    H3 = 23
    A4 = 24
    B4 = 25
    C4 = 26
    D4 = 27
    E4 = 28
    F4 = 29
    G4 = 30
    H4 = 31
    A5 = 32
    B5 = 33
    C5 = 34
    D5 = 35
    E5 = 36
    F5 = 37
    G5 = 38
    H5 = 39
    A6 = 40
    B6 = 41
    C6 = 42
    D6 = 43
    E6 = 44
    F6 = 45
    G6 = 46
    H6 = 47
    A7 = 48
    B7 = 49
    C7 = 50
    D7 = 51
    E7 = 52
    F7 = 53
    G7 = 54
    H7 = 55
    A8 = 56
    B8 = 57
    C8 = 58
    D8 = 59
    E8 = 60
    F8 = 61
    G8 = 62
    H8 = 63

    @property
    def board_index(self) -> int:
        return self.value

    @property
    def rank(self) -> int:
        return self.value // 8

    @property
    def file(self) -> int:
        return self.value % 8


@dataclass
class Board:
    width: int = 8
    height: int = 8
    _squares: list[Piece | None] = field(init=False, repr=False)

    def __post_init__(self):
        self._squares = [None] * (self.width * self.height)
        self.__initialize_board()

    def __getitem__(self, square: Square) -> Piece | None:
        return self._squares[square.board_index]

    def __setitem__(self, square: Square, value: Piece | None) -> None:
        self._squares[square.board_index] = value

    def __initialize_board(self) -> None:
        back_rank = [
            PieceKind.ROOK,
            PieceKind.KNIGHT,
            PieceKind.BISHOP,
            PieceKind.QUEEN,
            PieceKind.KING,
            PieceKind.BISHOP,
            PieceKind.KNIGHT,
            PieceKind.ROOK,
        ]

        self._squares[Square.A1 : Square.A2] = [
            Piece(kind, Color.WHITE) for kind in back_rank
        ]
        self._squares[Square.A2 : Square.A3] = [
            Piece(PieceKind.PAWN, Color.WHITE) for _ in range(8)
        ]
        self._squares[Square.A7 : Square.A8] = [
            Piece(PieceKind.PAWN, Color.BLACK) for _ in range(8)
        ]
        self._squares[Square.A8 :] = [Piece(kind, Color.BLACK) for kind in back_rank]
