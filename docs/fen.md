# FEN in pythongine

FEN is the text format pythongine uses to load and save a chess position. A
string encodes piece placement, side to move, castling rights, en passant,
and the halfmove/fullmove clocks.

```python
from board import Board

board = Board.from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
fen = board.to_fen()
```

For tests and quick setups, a two-field shortcut is also available:
`Board.from_simple_fen(...)` / `board.to_simple_fen()`.

---

## Format overview

A full FEN string has **six space-separated fields**:

```
<piece placement> <active color> <castling> <en passant> <halfmove> <fullmove>
```

Starting position:

```
rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1
```

`Board.from_fen` accepts **1–6 fields**. Missing trailing fields use these
defaults:

| Omitted field | Default |
|---------------|---------|
| Castling | `-` (no rights) |
| En passant | `-` |
| Halfmove clock | `0` |
| Fullmove number | `1` |

`Board.to_fen` always writes all six fields.

---

## Board mapping

| FEN field | `Board` attribute | Updated by `make_move` |
|-----------|-------------------|------------------------|
| Piece placement | `_squares` | yes |
| Active color | `side_to_move` | yes (flipped) |
| Castling | `castling_rights` | yes |
| En passant | `en_passant_target` | yes |
| Halfmove clock | `halfmove_clock` | yes |
| Fullmove number | `fullmove_number` | yes |

All six values (except piece placement, which is rebuilt from squares) are
restored by `unmake_move` via `_UndoState`.

Castling rights use the bitmask constants exported from `board.py`:

- `CASTLE_WHITE_KINGSIDE` (`K`)
- `CASTLE_WHITE_QUEENSIDE` (`Q`)
- `CASTLE_BLACK_KINGSIDE` (`k`)
- `CASTLE_BLACK_QUEENSIDE` (`q`)
- `CASTLE_ALL` — all four combined

---

## Field 1: Piece placement

Parsed by `_parse_placement`, serialized by `_format_placement`.

Ranks are listed from rank 8 to rank 1 (Black's back rank first). Each rank is
separated by `/`. The first character group is `a8…h8`; the last is `a1…h1`.

### Piece letters

| Letter | Piece | Color |
|--------|-------|-------|
| `P` `N` `B` `R` `Q` `K` | Pawn … King | White |
| `p` `n` `b` `r` `q` `k` | Pawn … King | Black |

### Empty squares

Runs of empty squares are digits `1`–`8`. Example: `4P3` = four empty, White
pawn, three empty (eight files total).

Each rank must sum to exactly eight files. Invalid placement raises
`ValueError`.

`from_fen` validates syntax only — it does not check for legal positions
(missing kings, pawns on back ranks, etc.).

---

## Field 2: Active color

| Value | `Board.side_to_move` |
|-------|----------------------|
| `w` | `Color.WHITE` |
| `b` | `Color.BLACK` |

If the FEN contains only the placement field, `from_fen` defaults to White.

---

## Field 3: Castling availability

Parsed by `_parse_castling`, serialized by `_format_castling`.

| Character | Bit | Meaning |
|-----------|-----|---------|
| `K` | `CASTLE_WHITE_KINGSIDE` | White O-O available |
| `Q` | `CASTLE_WHITE_QUEENSIDE` | White O-O-O available |
| `k` | `CASTLE_BLACK_KINGSIDE` | Black O-O available |
| `q` | `CASTLE_BLACK_QUEENSIDE` | Black O-O-O available |
| `-` | `0` | No rights |

Characters are concatenated in order **K, Q, k, q**. Unknown characters raise
`ValueError`.

This field records whether the king and corner rooks have moved or been
captured. Whether castling is actually legal (path clear, not in check, transit
squares safe) is decided later in `generate_moves`.

`make_move` clears rights via `_update_castling_rights` when:

- The king moves
- A corner rook moves from `a1`, `h1`, `a8`, or `h8`
- A piece is captured on one of those corner squares

`from_simple_fen` does **not** read this field; castling defaults to
`CASTLE_ALL`.

---

## Field 4: En passant target square

Parsed by `_parse_en_passant`, serialized by `_format_en_passant`.

| Value | `Board.en_passant_target` |
|-------|---------------------------|
| `-` | `None` |
| e.g. `e3`, `d6` | `Square` via `square_from_name` |

The square is the one **behind** a pawn that just double-pushed — the square
an opposing pawn would land on when capturing en passant.

pythongine only accepts squares on **rank 3 or rank 6** (internal rank index 2
or 5). Other squares raise `ValueError`.

`make_move` sets the target in `_update_en_passant_target` after a double pawn
push and clears it on every move.

En passant legality (pins, discovered check) is checked separately in
`_is_legal_en_passant` during `generate_moves`.

Square name helpers live in `pieces.py`:

```python
from pieces import square_from_name, square_to_name

square_from_name("e4")     # → Square.E4
square_to_name(Square.E4)  # → "e4"
```

`from_simple_fen` does **not** read this field; `en_passant_target` defaults
to `None`.

---

## Field 5: Halfmove clock

Non-negative integer stored in `Board.halfmove_clock`.

`make_move` updates it as follows:

| Move type | Effect |
|-----------|--------|
| Pawn move | reset to `0` |
| Capture (including en passant) | reset to `0` |
| Any other quiet move | increment by `1` |

Negative values in the FEN string raise `ValueError` on load.

---

## Field 6: Fullmove number

Positive integer stored in `Board.fullmove_number`. Starts at `1`.

`make_move` increments it by `1` when the moving side is Black. Values below
`1` in the FEN string raise `ValueError` on load.

---

## API summary

| Method | Fields | Notes |
|--------|--------|-------|
| `Board.from_fen(fen)` | 1–6 | Canonical loader |
| `Board.to_fen()` | all 6 | Always complete output |
| `Board.from_simple_fen(fen)` | 2 | Placement + side only; castling `CASTLE_ALL`, EP `None` |
| `Board.to_simple_fen()` | 2 | Placement + side only |
| `Board()` | — | Standard start; `to_fen()` matches the usual start FEN |

---

## Worked example

```
4k3/8/4r3/4Pp2/8/8/8/4K3 w - f6 0 1
```

| Field | Board state |
|-------|-------------|
| Placement | Black `Ke8`, `Re6`; White `Pe5`, `Pf5`; White `Ke1`; rest empty |
| `w` | White to move |
| `-` | `castling_rights == 0` |
| `f6` | `en_passant_target == Square.F6` |
| `0` | `halfmove_clock == 0` |
| `1` | `fullmove_number == 1` |

Loading this FEN is enough for `generate_moves` to offer `f5xe6` en passant —
no manual assignment of `en_passant_target` is needed.

---

## Common pitfalls

1. **Eight files per rank.** `3p1P3` is nine files and fails parsing; use
   `3p1P2`.

2. **Castling field ≠ legal castling.** `KQkq` in FEN does not guarantee
   `generate_moves` will offer castle moves.

3. **EP expires after one ply.** `make_move` clears `en_passant_target` on
   every move; it is only re-set by a double pawn push.

4. **`from_simple_fen` vs `from_fen`.** Simple FEN ignores castling, EP, and
   clocks. Prefer full FEN when those matter, e.g.
   `8/8/8/3p1P2/8/8/8/4K3 w - e6 0 1` instead of setting `en_passant_target`
   manually after load.

5. **Halfmove vs fullmove.** Halfmove resets on pawn/capture moves; fullmove
   increments only after Black's half-move in `make_move`.
