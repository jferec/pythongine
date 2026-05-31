from dataclasses import dataclass, field

from bitboard import KING_ATTACKS, KNIGHT_ATTACKS, iter_squares, square_bb
from move import Move, MoveFlag
from pieces import Color, Piece, PieceKind, Square

# Re-exported for callers that import from board.
__all__ = [
    "Board",
    "CASTLE_ALL",
    "CASTLE_BLACK_KINGSIDE",
    "CASTLE_BLACK_QUEENSIDE",
    "CASTLE_WHITE_KINGSIDE",
    "CASTLE_WHITE_QUEENSIDE",
    "Color",
    "Move",
    "MoveFlag",
    "Piece",
    "PieceKind",
    "Square",
]

# Castling rights: KQkq — white kingside, white queenside, black kingside, black queenside
CASTLE_WHITE_KINGSIDE = 8
CASTLE_WHITE_QUEENSIDE = 4
CASTLE_BLACK_KINGSIDE = 2
CASTLE_BLACK_QUEENSIDE = 1
CASTLE_ALL = (
    CASTLE_WHITE_KINGSIDE
    | CASTLE_WHITE_QUEENSIDE
    | CASTLE_BLACK_KINGSIDE
    | CASTLE_BLACK_QUEENSIDE
)

PROMOTION_PIECES = (
    PieceKind.QUEEN,
    PieceKind.ROOK,
    PieceKind.BISHOP,
    PieceKind.KNIGHT,
)

_FEN_TO_PIECE = {
    "P": (PieceKind.PAWN, Color.WHITE),
    "N": (PieceKind.KNIGHT, Color.WHITE),
    "B": (PieceKind.BISHOP, Color.WHITE),
    "R": (PieceKind.ROOK, Color.WHITE),
    "Q": (PieceKind.QUEEN, Color.WHITE),
    "K": (PieceKind.KING, Color.WHITE),
    "p": (PieceKind.PAWN, Color.BLACK),
    "n": (PieceKind.KNIGHT, Color.BLACK),
    "b": (PieceKind.BISHOP, Color.BLACK),
    "r": (PieceKind.ROOK, Color.BLACK),
    "q": (PieceKind.QUEEN, Color.BLACK),
    "k": (PieceKind.KING, Color.BLACK),
}

_PIECE_TO_FEN = {
    (PieceKind.PAWN, Color.WHITE): "P",
    (PieceKind.KNIGHT, Color.WHITE): "N",
    (PieceKind.BISHOP, Color.WHITE): "B",
    (PieceKind.ROOK, Color.WHITE): "R",
    (PieceKind.QUEEN, Color.WHITE): "Q",
    (PieceKind.KING, Color.WHITE): "K",
    (PieceKind.PAWN, Color.BLACK): "p",
    (PieceKind.KNIGHT, Color.BLACK): "n",
    (PieceKind.BISHOP, Color.BLACK): "b",
    (PieceKind.ROOK, Color.BLACK): "r",
    (PieceKind.QUEEN, Color.BLACK): "q",
    (PieceKind.KING, Color.BLACK): "k",
}

_BISHOP_DELTAS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
_ROOK_DELTAS = ((0, 1), (0, -1), (1, 0), (-1, 0))


@dataclass
class Board:
    """Chess position with pseudo-legal move generation.

    Piece placement is stored per square; move generation does not yet filter
    for check, pins, or king safety.
    """

    width: int = 8
    """Board width in squares (always 8 for standard chess)."""

    height: int = 8
    """Board height in squares (always 8 for standard chess)."""

    setup_standard_position: bool = True
    """When True, ``__post_init__`` fills the board with the usual start array."""

    side_to_move: Color = Color.WHITE
    """Color allowed to play next; used by ``generate_moves`` and simple FEN."""

    castling_rights: int = CASTLE_ALL
    """Bitmask of remaining castling rights (``CASTLE_*`` constants, KQkq)."""

    en_passant_target: Square | None = None
    """Square behind a pawn that just moved two ranks; ``None`` if unavailable."""

    move_history: list[Move] = field(default_factory=list)
    """Played moves in order; populated by ``make_move`` (not ``generate_moves``)."""

    _squares: list[Piece | None] = field(init=False, repr=False)
    """Internal piece list indexed by ``Square.board_index``."""

    def __post_init__(self) -> None:
        """Allocate squares and optionally set up the standard start position."""
        self._squares = [None] * (self.width * self.height)
        if self.setup_standard_position:
            self.__initialize_board()

    def __getitem__(self, square: Square) -> Piece | None:
        """Return the piece on ``square``, or ``None`` if the square is empty."""
        return self._squares[square.board_index]

    def __setitem__(self, square: Square, value: Piece | None) -> None:
        """Place ``value`` on ``square`` (``None`` clears the square)."""
        self._squares[square.board_index] = value

    def __initialize_board(self) -> None:
        """Place white and black pieces in the standard starting formation."""
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

    @classmethod
    def from_simple_fen(cls, fen: str) -> "Board":
        """Build a board from simplified FEN (piece placement and side to move only).

        Example: ``rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w``.
        Castling rights and en passant are not read from the string; defaults apply.
        """
        placement, active_color = fen.strip().split()
        board = cls(setup_standard_position=False)
        board.side_to_move = Color.WHITE if active_color == "w" else Color.BLACK

        rank = 7
        file = 0
        for character in placement:
            if character == "/":
                rank -= 1
                file = 0
                continue
            if character.isdigit():
                file += int(character)
                continue
            kind, color = _FEN_TO_PIECE[character]
            board[Square(rank * 8 + file)] = Piece(kind, color)
            file += 1

        return board

    def to_simple_fen(self) -> str:
        """Encode piece placement and ``side_to_move`` as simplified FEN."""
        fen_ranks: list[str] = []
        for rank in range(7, -1, -1):
            empty_run = 0
            rank_chars: list[str] = []
            for file in range(8):
                piece = self[Square(rank * 8 + file)]
                if piece is None:
                    empty_run += 1
                    continue
                if empty_run:
                    rank_chars.append(str(empty_run))
                    empty_run = 0
                rank_chars.append(_PIECE_TO_FEN[(piece.kind, piece.color)])
            if empty_run:
                rank_chars.append(str(empty_run))
            fen_ranks.append("".join(rank_chars))

        active = "w" if self.side_to_move == Color.WHITE else "b"
        return f"{'/'.join(fen_ranks)} {active}"

    def generate_moves(self) -> list[Move]:
        """Return all pseudo-legal moves for ``side_to_move``.

        Includes promotions, castling, and en passant when state allows.
        Does not filter moves that leave the king in check.
        """
        moves: list[Move] = []
        for square in Square:
            piece = self[square]
            if piece is None or piece.color != self.side_to_move:
                continue
            destinations = self._piece_moves_bb(square, piece)
            for destination in iter_squares(destinations):
                moves.extend(self._moves_for_destination(square, destination, piece))
        return moves

    def _moves_for_destination(
        self, from_square: Square, to_square: Square, piece: Piece
    ) -> list[Move]:
        """Turn one destination bit into one or more ``Move`` values (e.g. four promotions)."""
        if piece.kind == PieceKind.KING and abs(to_square.file - from_square.file) == 2:
            flag = (
                MoveFlag.CASTLE_KINGSIDE
                if to_square.file > from_square.file
                else MoveFlag.CASTLE_QUEENSIDE
            )
            return [Move(from_square, to_square, flags=flag)]

        if piece.kind == PieceKind.PAWN and self._is_promotion_square(
            to_square, piece.color
        ):
            return [
                Move(
                    from_square,
                    to_square,
                    promotion=promotion,
                    flags=MoveFlag.PROMOTION,
                )
                for promotion in PROMOTION_PIECES
            ]

        if (
            piece.kind == PieceKind.PAWN
            and self.en_passant_target is not None
            and to_square == self.en_passant_target
        ):
            return [Move(from_square, to_square, flags=MoveFlag.EN_PASSANT)]

        if self._is_capture(from_square, to_square, piece):
            return [Move(from_square, to_square, flags=MoveFlag.CAPTURE)]

        return [Move(from_square, to_square, flags=MoveFlag.QUIET)]

    def _is_promotion_square(self, square: Square, color: Color) -> bool:
        """Return True if ``square`` is the back rank for ``color``."""
        if color == Color.WHITE:
            return square.rank == 7
        return square.rank == 0

    def _is_capture(
        self, from_square: Square, to_square: Square, piece: Piece
    ) -> bool:
        """Return True if the move to ``to_square`` takes an enemy piece (including EP)."""
        target = self[to_square]
        if target is not None and target.color != piece.color:
            return True
        return (
            piece.kind == PieceKind.PAWN
            and self.en_passant_target is not None
            and to_square == self.en_passant_target
        )

    def _piece_moves_bb(self, square: Square, piece: Piece) -> int:
        """Pseudo-legal destination bitboard for ``piece`` on ``square``."""
        match piece.kind:
            case PieceKind.PAWN:
                return self._pawn_moves_bb(square, piece.color)
            case PieceKind.KNIGHT:
                return self._knight_moves_bb(square, piece.color)
            case PieceKind.BISHOP:
                return self._bishop_moves_bb(square, piece.color)
            case PieceKind.ROOK:
                return self._rook_moves_bb(square, piece.color)
            case PieceKind.QUEEN:
                return self._queen_moves_bb(square, piece.color)
            case PieceKind.KING:
                return self._king_moves_bb(square, piece.color)

    def _all_occupied_bb(self) -> int:
        """Bitboard of all squares that contain any piece."""
        occupied = 0
        for square in Square:
            if self[square] is not None:
                occupied |= square_bb(square)
        return occupied

    def _occupied_bb(self, color: Color) -> int:
        """Bitboard of squares occupied by pieces of ``color``."""
        occupied = 0
        for square in Square:
            piece = self[square]
            if piece is not None and piece.color == color:
                occupied |= square_bb(square)
        return occupied

    def _enemy_bb(self, color: Color) -> int:
        """Bitboard of squares occupied by the opponent of ``color``."""
        return self._occupied_bb(~color)

    def _mask_friendly(self, attacks: int, color: Color) -> int:
        """Remove attack targets occupied by friendly pieces."""
        return attacks & ~self._occupied_bb(color)

    def _pawn_moves_bb(self, square: Square, color: Color) -> int:
        """Pseudo-legal pawn pushes, captures, and en passant from ``square``."""
        moves = 0
        forward = 8 if color == Color.WHITE else -8
        one_step = square + forward
        if 0 <= one_step <= 63 and self[Square(one_step)] is None:
            moves |= square_bb(Square(one_step))
            starting_rank = 1 if color == Color.WHITE else 6
            if square.rank == starting_rank:
                two_step = square + 2 * forward
                if self[Square(two_step)] is None:
                    moves |= square_bb(Square(two_step))

        for capture_offset in (-1, 1):
            if square.file + capture_offset < 0 or square.file + capture_offset > 7:
                continue
            capture_square = Square(square + forward + capture_offset)
            target = self[capture_square]
            if target is not None and target.color != color:
                moves |= square_bb(capture_square)

        if self.en_passant_target is not None:
            ep_rank = 4 if color == Color.WHITE else 3
            if (
                square.rank == ep_rank
                and abs(self.en_passant_target.file - square.file) == 1
            ):
                moves |= square_bb(self.en_passant_target)

        return moves

    def _knight_moves_bb(self, square: Square, color: Color) -> int:
        """Pseudo-legal knight leaps from ``square``."""
        return self._mask_friendly(KNIGHT_ATTACKS[square], color)

    def _bishop_moves_bb(self, square: Square, color: Color) -> int:
        """Pseudo-legal bishop rays from ``square``."""
        return self._sliding_moves_bb(square, color, _BISHOP_DELTAS)

    def _rook_moves_bb(self, square: Square, color: Color) -> int:
        """Pseudo-legal rook rays from ``square``."""
        return self._sliding_moves_bb(square, color, _ROOK_DELTAS)

    def _queen_moves_bb(self, square: Square, color: Color) -> int:
        """Pseudo-legal queen moves (bishop and rook rays combined)."""
        return self._bishop_moves_bb(square, color) | self._rook_moves_bb(
            square, color
        )

    def _sliding_moves_bb(
        self, square: Square, color: Color, deltas: tuple[tuple[int, int], ...]
    ) -> int:
        """Ray-cast along ``deltas`` until blocked by any piece or board edge."""
        moves = 0
        for delta_file, delta_rank in deltas:
            file = square.file + delta_file
            rank = square.rank + delta_rank
            while 0 <= file < 8 and 0 <= rank < 8:
                destination = Square(rank * 8 + file)
                target = self[destination]
                if target is None:
                    moves |= square_bb(destination)
                else:
                    if target.color != color:
                        moves |= square_bb(destination)
                    break
                file += delta_file
                rank += delta_rank
        return moves

    def _king_moves_bb(self, square: Square, color: Color) -> int:
        """Pseudo-legal king steps and castling king destinations from ``square``."""
        moves = self._mask_friendly(KING_ATTACKS[square], color)
        if square == Square.E1 and color == Color.WHITE:
            moves |= self._white_kingside_castle_bb()
            moves |= self._white_queenside_castle_bb()
        elif square == Square.E8 and color == Color.BLACK:
            moves |= self._black_kingside_castle_bb()
            moves |= self._black_queenside_castle_bb()
        return moves

    def _white_kingside_castle_bb(self) -> int:
        """King destination bit (G1) if white O-O is pseudo-legal."""
        if not (self.castling_rights & CASTLE_WHITE_KINGSIDE):
            return 0
        if (
            self[Square.E1] == Piece(PieceKind.KING, Color.WHITE)
            and self[Square.H1] == Piece(PieceKind.ROOK, Color.WHITE)
            and self[Square.F1] is None
            and self[Square.G1] is None
        ):
            return square_bb(Square.G1)
        return 0

    def _white_queenside_castle_bb(self) -> int:
        """King destination bit (C1) if white O-O-O is pseudo-legal."""
        if not (self.castling_rights & CASTLE_WHITE_QUEENSIDE):
            return 0
        if (
            self[Square.E1] == Piece(PieceKind.KING, Color.WHITE)
            and self[Square.A1] == Piece(PieceKind.ROOK, Color.WHITE)
            and self[Square.B1] is None
            and self[Square.C1] is None
            and self[Square.D1] is None
        ):
            return square_bb(Square.C1)
        return 0

    def _black_kingside_castle_bb(self) -> int:
        """King destination bit (G8) if black O-O is pseudo-legal."""
        if not (self.castling_rights & CASTLE_BLACK_KINGSIDE):
            return 0
        if (
            self[Square.E8] == Piece(PieceKind.KING, Color.BLACK)
            and self[Square.H8] == Piece(PieceKind.ROOK, Color.BLACK)
            and self[Square.F8] is None
            and self[Square.G8] is None
        ):
            return square_bb(Square.G8)
        return 0

    def _black_queenside_castle_bb(self) -> int:
        """King destination bit (C8) if black O-O-O is pseudo-legal."""
        if not (self.castling_rights & CASTLE_BLACK_QUEENSIDE):
            return 0
        if (
            self[Square.E8] == Piece(PieceKind.KING, Color.BLACK)
            and self[Square.A8] == Piece(PieceKind.ROOK, Color.BLACK)
            and self[Square.B8] is None
            and self[Square.C8] is None
            and self[Square.D8] is None
        ):
            return square_bb(Square.C8)
        return 0
