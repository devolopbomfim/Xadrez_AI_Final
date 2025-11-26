# core/hash/zobrist.py
"""
Zobrist hashing utilities for Xadrez_AI_Final.

Design goals:
 - Deterministic initialization from a seed.
 - Singleton/global usage appropriate for a chess engine.
 - Idempotent, thread-safe init() with optional forced reinit.
 - Exposes incremental XOR helpers used by the board implementation.
 - Diagnostic helpers for tests (entropy, signature).
 - All values are masked to 64 bits (U64).
"""

from __future__ import annotations

import threading
import random
from typing import ClassVar, List

from utils.constants import U64
from utils.enums import PieceIndex  # type: ignore

# Number of distinct piece indices expected in this project (usually 12)
_PIECE_INDEX_COUNT = 12
# Castling states encoded in 4 bits -> 16 possibilities
_CASTLING_STATES = 16
# Enpassant square possibilities: 64 (or none / -1 handled by API)
_ENPASSANT_SLOTS = 64

_init_lock = threading.Lock()
_initialized = False


class Zobrist:
    """
    Global Zobrist table holder.

    Usage pattern (engine):
        Zobrist.init(seed=12345)
        h = 0
        h = Zobrist.xor_piece(h, piece_index, square)
        h = Zobrist.xor_side(h)
        h = Zobrist.xor_castling(h, castling_rights)
        h = Zobrist.xor_enpassant(h, enpassant_sq)

    Public class attributes (populated by init):
        piece_square : List[List[int]]  # shape: [_PIECE_INDEX_COUNT][64]
        castling     : List[int]        # length: _CASTLING_STATES
        enpassant    : List[int]        # length: _ENPASSANT_SLOTS
        side_to_move : int
        (aliases:)
        piece_keys   -> piece_square
    """

    # Class-level storages (initialized by init())
    piece_square: ClassVar[List[List[int]]] = []
    castling: ClassVar[List[int]] = []
    enpassant: ClassVar[List[int]] = []
    side_to_move: ClassVar[int] = 0

    # Alias kept for compatibility with some tests / naming expectations
    piece_keys: ClassVar[List[List[int]]] = []

    @classmethod
    def init(cls, seed: int = 0xC0FFEE, force: bool = False) -> None:
        """
        Initialize Zobrist tables deterministically from `seed`.

        - `seed`: integer seed for deterministic RNG.
        - `force`: if True, reinitializes even if already initialized.

        This method is idempotent by default (subsequent calls with same seed are no-op).
        To re-seed, call with force=True.
        """
        global _initialized
        with _init_lock:
            if _initialized and not force:
                return

            rng = random.Random(seed)

            # 12 piece indices x 64 squares
            cls.piece_square = [
                [rng.getrandbits(64) & U64 for _ in range(64)]
                for _ in range(_PIECE_INDEX_COUNT)
            ]

            # castling states (0..15)
            cls.castling = [rng.getrandbits(64) & U64 for _ in range(_CASTLING_STATES)]

            # enpassant by square (0..63)
            cls.enpassant = [rng.getrandbits(64) & U64 for _ in range(_ENPASSANT_SLOTS)]

            # side-to-move key
            cls.side_to_move = rng.getrandbits(64) & U64

            # alias for backwards compatibility in tests / code
            cls.piece_keys = cls.piece_square

            _initialized = True

    @classmethod
    def reset(cls) -> None:
        """
        Fully reset the Zobrist tables to uninitialized state.
        Use carefully in tests only.
        """
        global _initialized
        with _init_lock:
            cls.piece_square = []
            cls.castling = []
            cls.enpassant = []
            cls.side_to_move = 0
            cls.piece_keys = []
            _initialized = False

    # -----------------------
    # Incremental operations
    # -----------------------
    @classmethod
    def xor_piece(cls, h: int, piece_index: PieceIndex | int, square: int) -> int:
        """
        XOR a piece at `square` into hash `h`.
        piece_index: either PieceIndex enum or integer index (0..11).
        """
        idx = int(piece_index)
        return (h ^ cls.piece_square[idx][square]) & U64

    @classmethod
    def xor_castling(cls, h: int, castling_rights: int) -> int:
        """
        XOR castling rights encoded as an int (0..15).
        """
        return (h ^ cls.castling[castling_rights & 0xF]) & U64

    @classmethod
    def xor_enpassant(cls, h: int, enpassant_sq: int) -> int:
        """
        XOR enpassant square into hash (if enpassant_sq == -1, unchanged).
        """
        if enpassant_sq == -1:
            return h
        return (h ^ cls.enpassant[enpassant_sq & 63]) & U64

    @classmethod
    def xor_side(cls, h: int) -> int:
        """
        Toggle side-to-move in the hash.
        """
        return (h ^ cls.side_to_move) & U64

    # -----------------------
    # Diagnostics / testing helpers
    # -----------------------
    @classmethod
    def verify_entropy(cls) -> float:
        """
        Return fraction of unique keys across piece_square (value in (0.0..1.0]).
        Ideal ~1.0 (all keys unique). Useful for tests.
        """
        if not cls.piece_square:
            raise RuntimeError("Zobrist not initialized")

        seen = set()
        total = 0
        for row in cls.piece_square:
            for v in row:
                seen.add(v)
                total += 1
        return len(seen) / total if total else 0.0

    @classmethod
    def signature(cls) -> bytes:
        """
        Deterministic signature of the current tables suitable for quick equality checks
        between runs (used by determinism tests). It's a compact representation: repr()
        of first rows to avoid huge memory use while still being stable.
        """
        if not cls.piece_square:
            return b""
        parts = []
        # sample first N pieces (or all if small)
        N = min(len(cls.piece_square), 6)
        for i in range(N):
            # represent the first few entries of each row
            sample = cls.piece_square[i][:16]
            parts.append(repr(sample).encode("utf-8"))
        parts.append(repr(cls.castling[:8]).encode("utf-8"))
        parts.append(repr(cls.enpassant[:8]).encode("utf-8"))
        parts.append(repr(cls.side_to_move).encode("utf-8"))
        return b"||".join(parts)

    @classmethod
    def ensure_initialized(cls, seed: int = 0xC0FFEE) -> None:
        """
        Convenience to guarantee initialization (idempotent).
        """
        cls.init(seed=seed)

# Backwards-friendly module-level alias for tests that import the class directly
_default = Zobrist

