"""
Attack tables for Xadrez_AI_Final.

Objective:
  Precompute and expose bitboard attack tables for non-sliding pieces
  (knight, king, pawn by color) and provide a thin runtime API that
  delegates sliding piece attacks to magic_bitboards when available.

Invariants:
  - Bitboard-first indexing A1=0 ... H8=63.
  - Tables are deterministic and precomputed at import time via init().
  - init() is idempotent and thread-safe.
  - No circular import at module top-level with magic_bitboards:
      magic_bitboards is imported lazily inside init() to avoid cycles.
  - Runtime hot paths use local bindings and no redundant calculations.

Public API:
  init()
  knight_attacks(sq) -> int
  king_attacks(sq) -> int
  pawn_attacks(sq, color) -> int
  rook_attacks(sq, occ) -> int
  bishop_attacks(sq, occ) -> int
  queen_attacks(sq, occ) -> int
  RUNTIME_TABLES / constants exported for tests
"""

from __future__ import annotations
from typing import List, Dict
import threading

from utils.constants import U64, SQUARE_TO_FILE, SQUARE_TO_RANK
from utils.enums import Color

# Public tables (filled by init)
KNIGHT_ATTACKS: List[int] = [0] * 64
KING_ATTACKS: List[int] = [0] * 64
PAWN_ATTACKS: Dict[Color, List[int]] = {Color.WHITE: [0] * 64, Color.BLACK: [0] * 64}

# Optional ray masks for debug/fallback (computed from magic or computed here)
ROOK_RAY_MASKS: List[int] = [0] * 64
BISHOP_RAY_MASKS: List[int] = [0] * 64

# Lazy bindings to magic_bitboards runtime functions (set in init)
_magic_rook_attacks = None  # type: ignore
_magic_bishop_attacks = None  # type: ignore

# Initialization guard
_INITIALIZED = False
_init_lock = threading.Lock()

U64_MASK = U64
BIT_1 = 1


# ----------------------------
# Local helpers (pure, no imports causing cycles)
# ----------------------------
def _in_bounds(f: int, r: int) -> bool:
    return 0 <= f < 8 and 0 <= r < 8


def _sq(f: int, r: int) -> int:
    return r * 8 + f


def _set_bit(bb: int, sq: int) -> int:
    return bb | (BIT_1 << (sq & 63))


# ----------------------------
# Table builders
# ----------------------------
def _build_knight_attacks() -> List[int]:
    table = [0] * 64
    knight_moves = ((1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2))
    for sq in range(64):
        f = SQUARE_TO_FILE[sq]
        r = SQUARE_TO_RANK[sq]
        bb = 0
        for df, dr in knight_moves:
            nf, nr = f + df, r + dr
            if _in_bounds(nf, nr):
                bb = _set_bit(bb, _sq(nf, nr))
        table[sq] = bb & U64_MASK
    return table


def _build_king_attacks() -> List[int]:
    table = [0] * 64
    king_moves = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))
    for sq in range(64):
        f = SQUARE_TO_FILE[sq]
        r = SQUARE_TO_RANK[sq]
        bb = 0
        for df, dr in king_moves:
            nf, nr = f + df, r + dr
            if _in_bounds(nf, nr):
                bb = _set_bit(bb, _sq(nf, nr))
        table[sq] = bb & U64_MASK
    return table


def _build_pawn_attacks() -> Dict[Color, List[int]]:
    white = [0] * 64
    black = [0] * 64
    for sq in range(64):
        f = SQUARE_TO_FILE[sq]
        r = SQUARE_TO_RANK[sq]

        # White pawns attack to r+1, files f-1 and f+1
        bb_w = 0
        if r + 1 < 8:
            if f - 1 >= 0:
                bb_w = _set_bit(bb_w, _sq(f - 1, r + 1))
            if f + 1 < 8:
                bb_w = _set_bit(bb_w, _sq(f + 1, r + 1))
        white[sq] = bb_w & U64_MASK

        # Black pawns attack to r-1, files f-1 and f+1
        bb_b = 0
        if r - 1 >= 0:
            if f - 1 >= 0:
                bb_b = _set_bit(bb_b, _sq(f - 1, r - 1))
            if f + 1 < 8:
                bb_b = _set_bit(bb_b, _sq(f + 1, r - 1))
        black[sq] = bb_b & U64_MASK

    return {Color.WHITE: white, Color.BLACK: black}


def _compute_ray_masks_from_magic(mb_module) -> None:
    """
    If magic_bitboards exposes masks (ROOK_MASKS/BISHOP_MASKS) we copy them for debug/use.
    This is a no-op if not available.
    """
    global ROOK_RAY_MASKS, BISHOP_RAY_MASKS
    try:
        # prefer direct arrays if present
        rook_masks = getattr(mb_module, "ROOK_MASKS", None)
        bishop_masks = getattr(mb_module, "BISHOP_MASKS", None)
        if rook_masks is not None and len(rook_masks) == 64:
            ROOK_RAY_MASKS = list(rook_masks)
        if bishop_masks is not None and len(bishop_masks) == 64:
            BISHOP_RAY_MASKS = list(bishop_masks)
    except Exception:
        # keep defaults (zeros) on any problem
        pass


# ----------------------------
# Public init (idempotent, thread-safe)
# ----------------------------
def init() -> None:
    """
    Initialize attack tables and connect sliding attack runtime to magic_bitboards.

    Idempotent and thread-safe.
    """
    global _INITIALIZED, KNIGHT_ATTACKS, KING_ATTACKS, PAWN_ATTACKS
    global _magic_rook_attacks, _magic_bishop_attacks

    with _init_lock:
        if _INITIALIZED:
            return

        # Precompute static tables (deterministic)
        _knight = _build_knight_attacks()
        _king = _build_king_attacks()
        _pawn = _build_pawn_attacks()

        for i in range(64):
            KNIGHT_ATTACKS[i] = _knight[i]
            KING_ATTACKS[i] = _king[i]

        for color in PAWN_ATTACKS:
            for sq in range(64):
                PAWN_ATTACKS[color][sq] = _pawn[color][sq]

        # Lazy import of magic_bitboards to avoid circular imports at module load
        try:
            from core.moves import magic_bitboards as mb  # local import, may raise
        except Exception:
            mb = None  # fallbacks will be used at runtime

        if mb is not None:
            # ensure magics are initialized in magic_bitboards (no-op if already)
            try:
                mb.init()
            except Exception:
                # if mb.init fails, we will still keep non-sliding tables functional
                pass

            # Bind sliding attack functions for fast runtime usage
            _magic_rook_attacks = getattr(mb, "rook_attacks", None)
            _magic_bishop_attacks = getattr(mb, "bishop_attacks", None)

            # copy ray masks if available (useful for debug/tests)
            _compute_ray_masks_from_magic(mb)

        _INITIALIZED = True


# ----------------------------
# Runtime API (hot paths)
# ----------------------------
def knight_attacks(sq: int) -> int:
    """Return knight attacks bitboard for square `sq` (0..63)."""
    if not _INITIALIZED:
        init()
    return KNIGHT_ATTACKS[sq]


def king_attacks(sq: int) -> int:
    """Return king attacks bitboard for square `sq` (0..63)."""
    if not _INITIALIZED:
        init()
    return KING_ATTACKS[sq]


def pawn_attacks(sq: int, color: Color) -> int:
    """Return pawn attack bitboard for a pawn of `color` on `sq`."""
    if not _INITIALIZED:
        init()
    return PAWN_ATTACKS[color][sq]


# Sliding delegators: use magic if available, otherwise raise (tests will provide fallbacks)
def rook_attacks(sq: int, occ: int) -> int:
    """
    Return rook attacks for square `sq` given occupancy `occ`.
    Delegates to magic_bitboards.rook_attacks when available.
    """
    if not _INITIALIZED:
        init()
    if _magic_rook_attacks is None:
        raise RuntimeError("Magic bitboards rook_attacks not available (init missing).")
    # local binding for hot path
    func = _magic_rook_attacks
    return func(sq, occ)


def bishop_attacks(sq: int, occ: int) -> int:
    if not _INITIALIZED:
        init()
    if _magic_bishop_attacks is None:
        raise RuntimeError("Magic bitboards bishop_attacks not available (init missing).")
    func = _magic_bishop_attacks
    return func(sq, occ)


def queen_attacks(sq: int, occ: int) -> int:
    """Queen is rook | bishop."""
    return rook_attacks(sq, occ) | bishop_attacks(sq, occ)


# Export list
__all__ = [
    "init",
    "knight_attacks",
    "king_attacks",
    "pawn_attacks",
    "rook_attacks",
    "bishop_attacks",
    "queen_attacks",
    "KNIGHT_ATTACKS",
    "KING_ATTACKS",
    "PAWN_ATTACKS",
    "ROOK_RAY_MASKS",
    "BISHOP_RAY_MASKS",
    "_INITIALIZED",
]
