from dataclasses import dataclass, field

from bitboard import KING_ATTACKS, KNIGHT_ATTACKS, iter_squares, square_bb
from king_safety import KingSafety
from move import Move, MoveFlag
from pieces import Color, Piece, PieceKind, Square, square_from_name, square_to_name

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

_CASTLE_KINGSIDE_DESTINATIONS = square_bb(Square.G1) | square_bb(Square.G8)
_CASTLE_QUEENSIDE_DESTINATIONS = square_bb(Square.C1) | square_bb(Square.C8)

_CASTLING_FROM_FEN = {
    "K": CASTLE_WHITE_KINGSIDE,
    "Q": CASTLE_WHITE_QUEENSIDE,
    "k": CASTLE_BLACK_KINGSIDE,
    "q": CASTLE_BLACK_QUEENSIDE,
}
_CASTLING_TO_FEN = (
    (CASTLE_WHITE_KINGSIDE, "K"),
    (CASTLE_WHITE_QUEENSIDE, "Q"),
    (CASTLE_BLACK_KINGSIDE, "k"),
    (CASTLE_BLACK_QUEENSIDE, "q"),
)


def _parse_castling(field: str) -> int:
    """Return castling-rights bitmask from a FEN castling field."""
    if field == "-":
        return 0
    rights = 0
    for character in field:
        if character not in _CASTLING_FROM_FEN:
            raise ValueError(f"Invalid castling field: {field!r}")
        rights |= _CASTLING_FROM_FEN[character]
    return rights


def _format_castling(rights: int) -> str:
    """Return the FEN castling field for ``rights``."""
    if rights == 0:
        return "-"
    return "".join(label for bit, label in _CASTLING_TO_FEN if rights & bit)


def _parse_en_passant(field: str) -> Square | None:
    """Return the en passant target square from a FEN field."""
    if field == "-":
        return None
    square = square_from_name(field)
    if square.rank not in (2, 5):
        raise ValueError(f"Invalid en passant square: {field!r}")
    return square


def _format_en_passant(square: Square | None) -> str:
    """Return the FEN en passant field for ``square``."""
    if square is None:
        return "-"
    return square_to_name(square)


def _parse_placement(placement: str, board: "Board") -> None:
    """Place pieces on ``board`` from the FEN piece-placement field."""
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
        if file >= 8 or rank < 0:
            raise ValueError(f"Invalid piece placement: {placement!r}")
        kind, color = _FEN_TO_PIECE[character]
        board[Square(rank * 8 + file)] = Piece(kind, color)
        file += 1
    if rank != 0 or file != 8:
        raise ValueError(f"Invalid piece placement: {placement!r}")


def _format_placement(board: "Board") -> str:
    """Return the FEN piece-placement field for ``board``."""
    fen_ranks: list[str] = []
    for rank in range(7, -1, -1):
        empty_run = 0
        rank_chars: list[str] = []
        for file in range(8):
            piece = board[Square(rank * 8 + file)]
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
    return "/".join(fen_ranks)


@dataclass
class _UndoState:
    """Snapshot needed to reverse a single ``make_move`` call."""

    move: Move
    moving_color: Color
    captured_piece: Piece | None
    captured_square: Square | None
    previous_castling_rights: int
    previous_en_passant_target: Square | None
    previous_halfmove_clock: int
    previous_fullmove_number: int
    rook_from: Square | None = None
    rook_to: Square | None = None


@dataclass
class Board:
    """Chess position with legal move generation."""

    width: int = 8
    height: int = 8

    setup_standard_position: bool = True
    """When True, ``__post_init__`` fills the board with the usual start array."""

    side_to_move: Color = Color.WHITE
    """Color allowed to play next; used by ``generate_moves`` and simple FEN."""

    castling_rights: int = CASTLE_ALL
    """Bitmask of remaining castling rights (``CASTLE_*`` constants, KQkq)."""

    en_passant_target: Square | None = None
    """Square behind a pawn that just moved two ranks; ``None`` if unavailable."""

    halfmove_clock: int = 0
    """Half-moves since the last pawn advance or capture (50-move rule)."""

    fullmove_number: int = 1
    """Full-move count; incremented after each black half-move."""

    move_history: list[Move] = field(default_factory=list)
    """Played moves in order; populated by ``make_move`` (not ``generate_moves``)."""

    _squares: list[Piece | None] = field(init=False, repr=False)
    """Internal piece list indexed by ``Square.board_index``."""

    _undo_stack: list[_UndoState] = field(default_factory=list, repr=False)
    """Undo records for ``unmake_move``; not cleared by ``generate_moves``."""

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
    def from_fen(cls, fen: str) -> "Board":
        """Build a board from standard FEN (1–6 fields).

        Example: ``rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1``.
        Omitted trailing fields default to ``-`` for castling/en passant and
        ``0``/``1`` for the halfmove and fullmove clocks.
        """
        fields = fen.strip().split()
        if not 1 <= len(fields) <= 6:
            raise ValueError(f"FEN must contain 1–6 fields, got {len(fields)}")

        board = cls(setup_standard_position=False)
        _parse_placement(fields[0], board)

        if len(fields) == 1:
            board.side_to_move = Color.WHITE
            return board

        active_color = fields[1]
        if active_color not in ("w", "b"):
            raise ValueError(f"Invalid active color: {active_color!r}")
        board.side_to_move = Color.WHITE if active_color == "w" else Color.BLACK

        if len(fields) > 2:
            board.castling_rights = _parse_castling(fields[2])
        if len(fields) > 3:
            board.en_passant_target = _parse_en_passant(fields[3])
        if len(fields) > 4:
            halfmove = int(fields[4])
            if halfmove < 0:
                raise ValueError(f"Invalid halfmove clock: {halfmove}")
            board.halfmove_clock = halfmove
        if len(fields) > 5:
            fullmove = int(fields[5])
            if fullmove < 1:
                raise ValueError(f"Invalid fullmove number: {fullmove}")
            board.fullmove_number = fullmove

        return board

    @classmethod
    def from_simple_fen(cls, fen: str) -> "Board":
        """Build a board from simplified FEN (piece placement and side to move only).

        Example: ``rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w``.
        Castling rights and en passant are not read from the string; defaults apply.
        """
        placement, active_color = fen.strip().split()
        board = cls(setup_standard_position=False)
        board.side_to_move = Color.WHITE if active_color == "w" else Color.BLACK
        _parse_placement(placement, board)
        return board

    def to_fen(self) -> str:
        """Encode the position as standard 6-field FEN."""
        active = "w" if self.side_to_move == Color.WHITE else "b"
        return (
            f"{_format_placement(self)} {active} "
            f"{_format_castling(self.castling_rights)} "
            f"{_format_en_passant(self.en_passant_target)} "
            f"{self.halfmove_clock} {self.fullmove_number}"
        )

    def to_simple_fen(self) -> str:
        """Encode piece placement and ``side_to_move`` as simplified FEN."""
        active = "w" if self.side_to_move == Color.WHITE else "b"
        return f"{_format_placement(self)} {active}"

    def generate_moves(self) -> list[Move]:
        """Return all legal moves for ``side_to_move``.

        Filters pseudo-legal moves with ``KingSafety`` masks; en passant is
        additionally validated by applying the move and checking for check.
        """
        safety = KingSafety.for_color(self, self.side_to_move)
        moves: list[Move] = []
        for square in Square:
            piece = self[square]
            if piece is None or piece.color != self.side_to_move:
                continue
            destinations = self._legal_moves_bb(square, piece, safety)
            for destination in iter_squares(destinations):
                for move in self._moves_for_destination(square, destination, piece):
                    if move.flags == MoveFlag.EN_PASSANT:
                        if self._is_legal_en_passant(move, safety):
                            moves.append(move)
                    else:
                        moves.append(move)
        return moves

    def _generate_pseudo_legal_moves(self) -> list[Move]:
        """Return pseudo-legal moves without king-safety filtering."""
        moves: list[Move] = []
        for square in Square:
            piece = self[square]
            if piece is None or piece.color != self.side_to_move:
                continue
            destinations = self._piece_moves_bb(square, piece)
            for destination in iter_squares(destinations):
                moves.extend(self._moves_for_destination(square, destination, piece))
        return moves

    def make_move(self, move: Move) -> None:
        """Apply ``move`` for ``side_to_move`` and push an undo record."""
        color = self.side_to_move
        piece = self[move.from_square]
        if piece is None or piece.color != color:
            raise ValueError(f"Illegal move: no {color.name.lower()} piece on {move.from_square}")

        captured_piece: Piece | None = None
        captured_square: Square | None = None
        rook_from: Square | None = None
        rook_to: Square | None = None
        previous_castling_rights = self.castling_rights
        previous_en_passant_target = self.en_passant_target
        previous_halfmove_clock = self.halfmove_clock
        previous_fullmove_number = self.fullmove_number

        if move.flags == MoveFlag.EN_PASSANT:
            captured_square = self._en_passant_captured_square(move)
            captured_piece = self[captured_square]
            self[captured_square] = None
            self[move.to_square] = piece
            self[move.from_square] = None
        elif move.flags in (MoveFlag.CASTLE_KINGSIDE, MoveFlag.CASTLE_QUEENSIDE):
            rook_from, rook_to = self._castle_rook_squares(move, color)
            rook_piece = self[rook_from]
            self[move.to_square] = piece
            self[move.from_square] = None
            self[rook_to] = rook_piece
            self[rook_from] = None
        else:
            captured_piece = self[move.to_square]
            if captured_piece is not None:
                captured_square = move.to_square
            if move.flags == MoveFlag.PROMOTION:
                assert move.promotion is not None
                self[move.to_square] = Piece(move.promotion, color)
            else:
                self[move.to_square] = piece
            self[move.from_square] = None

        self._update_castling_rights(move, piece)
        self._update_en_passant_target(move, piece, color)

        is_pawn_or_capture = (
            piece.kind == PieceKind.PAWN
            or captured_piece is not None
            or move.flags == MoveFlag.EN_PASSANT
        )
        self.halfmove_clock = 0 if is_pawn_or_capture else self.halfmove_clock + 1
        if color == Color.BLACK:
            self.fullmove_number += 1

        self._undo_stack.append(
            _UndoState(
                move=move,
                moving_color=color,
                captured_piece=captured_piece,
                captured_square=captured_square,
                previous_castling_rights=previous_castling_rights,
                previous_en_passant_target=previous_en_passant_target,
                previous_halfmove_clock=previous_halfmove_clock,
                previous_fullmove_number=previous_fullmove_number,
                rook_from=rook_from,
                rook_to=rook_to,
            )
        )
        self.side_to_move = ~color
        self.move_history.append(move)

    def unmake_move(self) -> Move:
        """Revert the most recent ``make_move`` and return the undone move."""
        if not self._undo_stack:
            raise ValueError("No move to unmake")

        undo = self._undo_stack.pop()
        self.move_history.pop()
        self.side_to_move = undo.moving_color
        self.castling_rights = undo.previous_castling_rights
        self.en_passant_target = undo.previous_en_passant_target
        self.halfmove_clock = undo.previous_halfmove_clock
        self.fullmove_number = undo.previous_fullmove_number

        move = undo.move
        piece = self[move.to_square]
        if move.flags == MoveFlag.PROMOTION:
            piece = Piece(PieceKind.PAWN, undo.moving_color)
        self[move.from_square] = piece
        self[move.to_square] = None

        if undo.rook_from is not None and undo.rook_to is not None:
            self[undo.rook_from] = self[undo.rook_to]
            self[undo.rook_to] = None

        if undo.captured_square is not None:
            self[undo.captured_square] = undo.captured_piece

        return move

    def _en_passant_captured_square(self, move: Move) -> Square:
        """Return the square of the pawn removed by an en passant capture."""
        file_delta = move.to_square.file - move.from_square.file
        return Square(move.from_square + file_delta)

    def _castle_rook_squares(
        self, move: Move, color: Color
    ) -> tuple[Square, Square]:
        """Return ``(rook_from, rook_to)`` for a castling ``move``."""
        if color == Color.WHITE:
            if move.flags == MoveFlag.CASTLE_KINGSIDE:
                return Square.H1, Square.F1
            return Square.A1, Square.D1
        if move.flags == MoveFlag.CASTLE_KINGSIDE:
            return Square.H8, Square.F8
        return Square.A8, Square.D8

    def _update_castling_rights(self, move: Move, piece: Piece) -> None:
        """Clear castling rights affected by ``move``."""
        color = self.side_to_move
        if piece.kind == PieceKind.KING:
            if color == Color.WHITE:
                self.castling_rights &= ~(
                    CASTLE_WHITE_KINGSIDE | CASTLE_WHITE_QUEENSIDE
                )
            else:
                self.castling_rights &= ~(
                    CASTLE_BLACK_KINGSIDE | CASTLE_BLACK_QUEENSIDE
                )

        if piece.kind == PieceKind.ROOK:
            if move.from_square == Square.A1:
                self.castling_rights &= ~CASTLE_WHITE_QUEENSIDE
            elif move.from_square == Square.H1:
                self.castling_rights &= ~CASTLE_WHITE_KINGSIDE
            elif move.from_square == Square.A8:
                self.castling_rights &= ~CASTLE_BLACK_QUEENSIDE
            elif move.from_square == Square.H8:
                self.castling_rights &= ~CASTLE_BLACK_KINGSIDE

        if move.to_square == Square.A1:
            self.castling_rights &= ~CASTLE_WHITE_QUEENSIDE
        elif move.to_square == Square.H1:
            self.castling_rights &= ~CASTLE_WHITE_KINGSIDE
        elif move.to_square == Square.A8:
            self.castling_rights &= ~CASTLE_BLACK_QUEENSIDE
        elif move.to_square == Square.H8:
            self.castling_rights &= ~CASTLE_BLACK_KINGSIDE

    def _update_en_passant_target(
        self, move: Move, piece: Piece, color: Color
    ) -> None:
        """Set or clear the en passant target after ``move``."""
        self.en_passant_target = None
        if piece.kind != PieceKind.PAWN:
            return
        forward = 8 if color == Color.WHITE else -8
        if move.to_square - move.from_square == 2 * forward:
            self.en_passant_target = Square(move.from_square + forward)

    def _legal_moves_bb(
        self, from_square: Square, piece: Piece, safety: KingSafety
    ) -> int:
        """Legal destination bitboard for ``piece`` on ``from_square``."""
        pseudo = self._piece_moves_bb(from_square, piece)

        if piece.kind == PieceKind.KING:
            castle = self._legal_castle_destinations(from_square, piece.color, safety)
            non_castle = pseudo & ~(_CASTLE_KINGSIDE_DESTINATIONS | _CASTLE_QUEENSIDE_DESTINATIONS)
            return (non_castle & ~safety.danger) | castle

        if safety.pinned & square_bb(from_square):
            pseudo &= safety.pin_rays[from_square]
        if safety.in_check:
            pseudo &= safety.evasion_mask
        return pseudo

    def _legal_castle_destinations(
        self, king_square: Square, color: Color, safety: KingSafety
    ) -> int:
        """Return king destination bits for legal castling from ``king_square``."""
        destinations = 0
        if king_square == Square.E1 and color == Color.WHITE:
            if self._white_kingside_castle_bb():
                transit = square_bb(Square.E1) | square_bb(Square.F1) | square_bb(Square.G1)
                if not safety.danger & transit:
                    destinations |= square_bb(Square.G1)
            if self._white_queenside_castle_bb():
                transit = square_bb(Square.E1) | square_bb(Square.D1) | square_bb(Square.C1)
                if not safety.danger & transit:
                    destinations |= square_bb(Square.C1)
        elif king_square == Square.E8 and color == Color.BLACK:
            if self._black_kingside_castle_bb():
                transit = square_bb(Square.E8) | square_bb(Square.F8) | square_bb(Square.G8)
                if not safety.danger & transit:
                    destinations |= square_bb(Square.G8)
            if self._black_queenside_castle_bb():
                transit = square_bb(Square.E8) | square_bb(Square.D8) | square_bb(Square.C8)
                if not safety.danger & transit:
                    destinations |= square_bb(Square.C8)
        return destinations

    def _is_legal_en_passant(self, move: Move, safety: KingSafety) -> bool:
        """Return True if en passant ``move`` leaves the king out of check."""
        if safety.pinned & square_bb(move.from_square):
            if not safety.pin_rays[move.from_square] & square_bb(move.to_square):
                return False
        if safety.in_check:
            if not safety.evasion_mask & square_bb(move.to_square):
                return False

        moving_color = self.side_to_move
        self.make_move(move)
        in_check = KingSafety.for_color(self, moving_color).in_check
        self.unmake_move()
        return not in_check

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
            and to_square.file != from_square.file
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
            and to_square.file != from_square.file
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

    def all_occupied_bb(self) -> int:
        """Bitboard of all squares that contain any piece."""
        occupied = 0
        for square in Square:
            if self[square] is not None:
                occupied |= square_bb(square)
        return occupied

    def _all_occupied_bb(self) -> int:
        """Alias for ``all_occupied_bb`` (used internally by move generation)."""
        return self.all_occupied_bb()

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
