from typing import Protocol

from pieces import Piece, Square


class Position(Protocol):
    """Read-only piece placement used by attacks and king-safety analysis."""

    def __getitem__(self, square: Square) -> Piece | None:
        """Return the piece on ``square``, or ``None`` if empty."""
        ...

    def all_occupied_bb(self) -> int:
        """Return a bitboard of every occupied square."""
        ...
