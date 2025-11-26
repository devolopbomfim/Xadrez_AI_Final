# board.py — Xadrez_AI_Final
# Bitboard-first + mailbox, A1=0, sem regras, sem movegen, sem GUI.
# Objetivo: implementação eficiente do objeto de tabuleiro com caminhos quentes
# invariantes preservadas (A1=0, enums, serialização externa, APIs públicas).
# Hot paths: set_piece_at, remove_piece_at, move_piece, validate, copy.
from __future__ import annotations
from typing import Optional, Tuple, List

from utils.enums import Color, PieceType
from utils.constants import PIECE_COUNT, COLOR_COUNT

# ------------------------------------------------------------
# Precomputed bit masks
# ------------------------------------------------------------
# PERF: Precompute single-square bit masks to avoid repeated shifts in hot paths.
SQUARE_BB: tuple[int, ...] = tuple(1 << sq for sq in range(64))

def _sq_bit(square: int) -> int:
    """Return the bitboard mask for `square`. Uses precomputed table for speed."""
    return SQUARE_BB[square]

# mailbox cell: None | (Color, PieceType)
MailboxCell = Optional[Tuple[Color, PieceType]]

# ------------------------------------------------------------
# Board
# ------------------------------------------------------------
class Board:
    """Board container combining bitboards and a mailbox.

    Invariants:
        - Indexing A1=0..H8=63
        - bitboards[color][piece] holds piece bitboard (uint64)
        - occupancy[color] holds occupancy bitboard
        - all_occupancy == occupancy[0] | occupancy[1]
        - mailbox contains None or (Color, PieceType) consistent with bitboards

    Public API kept identical:
        - __init__(setup: bool = True)
        - clear()
        - copy() -> Board
        - get_piece_at(square: int) -> MailboxCell
        - set_piece_at(square: int, color: Color, piece: PieceType) -> None
        - remove_piece_at(square: int) -> None
        - move_piece(from_sq: int, to_sq: int) -> None
        - validate() -> None
    """

    __slots__ = (
        "bitboards",
        "occupancy",
        "all_occupancy",
        "mailbox",
    )

    def __init__(self, setup: bool = True) -> None:
        # bitboards[color][piece] -> uint64
        # PERF: use list-of-lists for mutability; inner lists are small and fixed-length.
        self.bitboards: List[List[int]] = [[0 for _ in range(PIECE_COUNT)] for _ in range(COLOR_COUNT)]
        # occupancy[color] -> uint64
        self.occupancy: List[int] = [0, 0]
        # all occupancy
        self.all_occupancy: int = 0
        # mailbox[64] -> None | (Color, PieceType)
        self.mailbox: List[MailboxCell] = [None] * 64

        if setup:
            self._set_starting_position()
        self.validate()

    # ------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------
    def clear(self) -> None:
        """Clear the board to an empty state.

        Complexity: O(PIECE_COUNT * COLOR_COUNT) ~ constant.
        """
        # PERF: assign lists directly to avoid many Python-level assignments where valid.
        for c in range(COLOR_COUNT):
            self.occupancy[c] = 0
            bb_row = self.bitboards[c]
            for p in range(PIECE_COUNT):
                bb_row[p] = 0
        self.all_occupancy = 0
        # PERF: recreate mailbox list (fast) instead of mutating each entry.
        self.mailbox = [None] * 64

    def copy(self) -> "Board":
        """Return a shallow copy of the board (bitboards/mailbox copied).

        Complexity: O(PIECE_COUNT * COLOR_COUNT + 64) -> effectively constant.
        """
        b = Board(setup=False)
        # PERF: local var lookups reduce attribute access overhead
        src_bb = self.bitboards
        dst_bb = b.bitboards
        for c in range(COLOR_COUNT):
            dst_bb[c][:] = src_bb[c][:]  # copy inner list contents in-place
            b.occupancy[c] = self.occupancy[c]
        b.all_occupancy = self.all_occupancy
        # mailbox is a small fixed-size list; .copy() is efficient
        b.mailbox = self.mailbox.copy()
        return b

    def get_piece_at(self, square: int) -> MailboxCell:
        """Return mailbox cell at `square`."""
        return self.mailbox[square]

    def set_piece_at(self, square: int, color: Color, piece: PieceType) -> None:
        """Place a piece on `square`. Raises assertion if square already occupied.

        Complexity: O(1)
        """
        bit = SQUARE_BB[square]  # PERF: local lookup
        assert (self.all_occupancy & bit) == 0, "Square already occupied"

        ci = int(color)
        pi = int(piece)

        # PERF: local references to reduce attribute lookups
        self.bitboards[ci][pi] |= bit
        self.occupancy[ci] |= bit
        self.all_occupancy |= bit
        self.mailbox[square] = (color, piece)

        # Validation limited to invariants touched — cheap but important in debug.
        self._validate_local(color)

    def remove_piece_at(self, square: int) -> None:
        """Remove any piece at `square`. No-op if square empty.

        Complexity: O(1) average.
        """
        cell = self.mailbox[square]
        if cell is None:
            return

        color, piece = cell
        bit = SQUARE_BB[square]

        ci = int(color)
        pi = int(piece)

        self.bitboards[ci][pi] &= ~bit
        self.occupancy[ci] &= ~bit
        self.all_occupancy &= ~bit
        self.mailbox[square] = None

        self._validate_local(color)

    def move_piece(self, from_sq: int, to_sq: int) -> None:
        """Move piece from `from_sq` to `to_sq`. Handles capturing automatically.

        Complexity: O(1)
        """
        if from_sq == to_sq:
            return

        src = self.mailbox[from_sq]
        assert src is not None, "No piece at from_sq"

        color, piece = src
        src_bit = SQUARE_BB[from_sq]
        dst_bit = SQUARE_BB[to_sq]
        ci = int(color)
        pi = int(piece)

        # capture if necessary
        if self.mailbox[to_sq] is not None:
            # PERF: reuse remove_piece_at (very fast) to keep correctness centralized
            self.remove_piece_at(to_sq)

        # move bitboards — XOR both bits (remove source, set destination).
        # PERF: XOR is slightly faster than separate clear/set in-place.
        self.bitboards[ci][pi] ^= (src_bit | dst_bit)
        # move occupancy
        self.occupancy[ci] ^= (src_bit | dst_bit)
        # move mailbox
        self.mailbox[from_sq] = None
        self.mailbox[to_sq] = (color, piece)
        # update global occupancy
        self.all_occupancy = self.occupancy[0] | self.occupancy[1]

        self._validate_local(color)

    # ------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------
    def _validate_local(self, color: Color) -> None:
        """Validate local invariants related to `color`.

        Complexity: O(#pieces + 64) worst-case; optimized with local variables.
        """
        ci = int(color)

        # color overlap
        assert (self.occupancy[0] & self.occupancy[1]) == 0

        # global occupancy
        assert self.all_occupancy == (self.occupancy[0] | self.occupancy[1])

        # mailbox consistency (only check recently affected squares)
        occ = self.occupancy[ci]
        bb_rows = self.bitboards
        mailbox = self.mailbox
        all_occ = self.all_occupancy

        # PERF: iterate only over set bits in all_occupancy to validate occupied squares.
        occ_mask = all_occ
        while occ_mask:
            lsb = occ_mask & -occ_mask
            sq = lsb.bit_length() - 1
            cell = mailbox[sq]
            assert cell is not None, "Mailbox missing piece on occupied square"
            c, p = cell
            assert bb_rows[int(c)][int(p)] & SQUARE_BB[sq], "Bitboard/mailbox inconsistency"
            occ_mask &= occ_mask - 1

        # Validate that mailbox entries for empty squares are None.
        # PERF: use bitwise complement check instead of per-square loop.
        # Build mask of mailbox-claimed squares
        mailbox_mask = 0
        for i, cell in enumerate(mailbox):
            if cell is not None:
                mailbox_mask |= SQUARE_BB[i]
        # mailbox_mask must equal all_occupancy
        assert mailbox_mask == all_occ, "Mailbox claims do not match occupancy"

    def validate(self) -> None:
        """Full validation: recompute occupancies and check mailbox consistency.

        Complexity: O(PIECE_COUNT * COLOR_COUNT + 64)
        """
        # recompute occupancy
        recomputed_occ = [0, 0]
        for c in range(COLOR_COUNT):
            row = self.bitboards[c]
            acc = 0
            # PERF: iterate inner list directly
            for p in range(PIECE_COUNT):
                acc |= row[p]
            recomputed_occ[c] = acc

        assert recomputed_occ[0] == self.occupancy[0]
        assert recomputed_occ[1] == self.occupancy[1]
        assert (self.occupancy[0] & self.occupancy[1]) == 0
        assert self.all_occupancy == (self.occupancy[0] | self.occupancy[1])

        # mailbox full check
        mailbox = self.mailbox
        all_occ = self.all_occupancy

        # PERF: validate occupied squares by iterating set bits (pieces count usually << 64)
        occ_mask = all_occ
        seen_mask = 0
        bb_rows = self.bitboards
        while occ_mask:
            lsb = occ_mask & -occ_mask
            sq = lsb.bit_length() - 1
            cell = mailbox[sq]
            assert cell is not None
            c, p = cell
            assert bb_rows[int(c)][int(p)] & SQUARE_BB[sq]
            seen_mask |= lsb
            occ_mask &= occ_mask - 1

        # All other squares must have mailbox None
        if seen_mask != ((1 << 64) - 1):
            # Empty squares mask
            empty_mask = (~seen_mask) & ((1 << 64) - 1)
            # PERF: iterate empties by checking mailbox entries for nones
            # (rarely faster to check all 64 entries due to branch predictability)
            for sq in range(64):
                if empty_mask & SQUARE_BB[sq]:
                    assert mailbox[sq] is None

        # king invariants
        king_index = int(PieceType.KING)
        for c in Color:
            king_bb = self.bitboards[int(c)][king_index]
            if king_bb != 0:  # only validate if king exists
                assert king_bb.bit_count() == 1, f"Invalid king count for {c}"

    # ------------------------------------------------------------
    # Starting Position
    # ------------------------------------------------------------
    def _set_starting_position(self) -> None:
        """Set standard chess starting position.

        Complexity: O(1) (constant number of placements)
        """
        self.clear()

        def place(color: Color, piece: PieceType, squares: List[int]) -> None:
            for sq in squares:
                self.set_piece_at(sq, color, piece)

        W = Color.WHITE
        B = Color.BLACK

        # White
        place(W, PieceType.ROOK,   [0, 7])
        place(W, PieceType.KNIGHT, [1, 6])
        place(W, PieceType.BISHOP, [2, 5])
        place(W, PieceType.QUEEN,  [3])
        place(W, PieceType.KING,   [4])
        place(W, PieceType.PAWN,   list(range(8, 16)))

        # Black
        place(B, PieceType.ROOK,   [56, 63])
        place(B, PieceType.KNIGHT, [57, 62])
        place(B, PieceType.BISHOP, [58, 61])
        place(B, PieceType.QUEEN,  [59])
        place(B, PieceType.KING,   [60])
        place(B, PieceType.PAWN,   list(range(48, 56)))

        self.all_occupancy = self.occupancy[0] | self.occupancy[1]
        self.validate()
