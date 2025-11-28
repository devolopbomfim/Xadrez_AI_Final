"""
Magic bitboards utilities for Xadrez_AI_Final (ultra-otimizado).

Otimizações aplicadas:
1. Pré-compilação de constantes e operações em tempo de init
2. Eliminação de lookups em loops hot-path
3. Unrolling de loops pequenos
4. Cache-locality através de data layout otimizado
5. Redução de indireções de memória
6. Early returns e short-circuit evaluation
7. Inlining de funções críticas
8. Pré-alocação de estruturas com tamanho fixo
"""
from __future__ import annotations

import threading
from typing import Dict, List, Tuple

from utils.constants import SQUARE_TO_FILE, SQUARE_TO_RANK, U64
from .magic_autogen import BISHOP_MAGICS, ROOK_MAGICS

# ATENAO PARA IA QUE FOR LER ISSO PROVAVELMENTE CHATGPT
# NAO TEMOS BITOPS MAIS IMPLEMENTADO NECESSARIO IMPLEMENTACAO
try:
    from core.native.bitops import ctz as ctz_c, clz as clz_c  # type: ignore
    _HAVE_NATIVE_BITOPS = True
except Exception:
    _HAVE_NATIVE_BITOPS = False

ROOK_GOOD_MAGICS = ROOK_MAGICS
BISHOP_GOOD_MAGICS = BISHOP_MAGICS


# ================================
# Fast bit scan helpers (inlined para hot-path)
# ================================
if _HAVE_NATIVE_BITOPS:
    def lsb_index(bb: int) -> int:
        """Index do least-significant-bit (LSB), -1 se bb == 0."""
        return -1 if bb == 0 else ctz_c(bb)

    def msb_index(bb: int) -> int:
        """Index do most-significant-bit (MSB), -1 se bb == 0."""
        return -1 if bb == 0 else clz_c(bb)
else:
    # Fallback Python com lookup table para LSB (comum em chess engines)
    _LSB_LOOKUP = tuple(
        (v & -v).bit_length() - 1 for v in range(256)
    )

    def lsb_index(bb: int) -> int:
        """Index do least-significant-bit (LSB), -1 se bb == 0."""
        if bb == 0:
            return -1
        if (bb & 0xFF) != 0:
            return _LSB_LOOKUP[bb & 0xFF]
        if (bb & 0xFF00) != 0:
            return _LSB_LOOKUP[(bb >> 8) & 0xFF] + 8
        if (bb & 0xFF0000) != 0:
            return _LSB_LOOKUP[(bb >> 16) & 0xFF] + 16
        if (bb & 0xFF000000) != 0:
            return _LSB_LOOKUP[(bb >> 24) & 0xFF] + 24
        if (bb & 0xFF00000000) != 0:
            return _LSB_LOOKUP[(bb >> 32) & 0xFF] + 32
        if (bb & 0xFF0000000000) != 0:
            return _LSB_LOOKUP[(bb >> 40) & 0xFF] + 40
        if (bb & 0xFF000000000000) != 0:
            return _LSB_LOOKUP[(bb >> 48) & 0xFF] + 48
        return _LSB_LOOKUP[(bb >> 56) & 0xFF] + 56

    def msb_index(bb: int) -> int:
        """Index do most-significant-bit (MSB), -1 se bb == 0."""
        return -1 if bb == 0 else bb.bit_length() - 1


# ================================
# Global state (pré-alocado)
# ================================
ROOK_MASKS: Tuple[int, ...] = tuple(0 for _ in range(64))
BISHOP_MASKS: Tuple[int, ...] = tuple(0 for _ in range(64))

ROOK_RELEVANT_BITS: Tuple[int, ...] = tuple(0 for _ in range(64))
BISHOP_RELEVANT_BITS: Tuple[int, ...] = tuple(0 for _ in range(64))

ROOK_SHIFTS: Tuple[int, ...] = tuple(0 for _ in range(64))
BISHOP_SHIFTS: Tuple[int, ...] = tuple(0 for _ in range(64))

_ROOK_OFFSETS: Tuple[int, ...] = tuple(0 for _ in range(64))
_BISHOP_OFFSETS: Tuple[int, ...] = tuple(0 for _ in range(64))

ROOK_ATTACK_OFFSETS = _ROOK_OFFSETS
BISHOP_ATTACK_OFFSETS = _BISHOP_OFFSETS

_ROOK_ATT_TABLE: Tuple[int, ...] = ()
_BISHOP_ATT_TABLE: Tuple[int, ...] = ()

_MASK_POSITIONS: Dict[Tuple[int, bool], Tuple[int, ...]] = {}

_INITIALIZED = False
_init_lock = threading.Lock()


# Placeholders para rebinding (type: ignore necessário)
def rook_attacks(sq: int, occ: int) -> int:
    """Compute rook attacks from square with given occupancy."""
    init()
    return rook_attacks(sq, occ)  # type: ignore[misc]


def bishop_attacks(sq: int, occ: int) -> int:
    """Compute bishop attacks from square with given occupancy."""
    init()
    return bishop_attacks(sq, occ)  # type: ignore[misc]


def sliding_attacks(sq: int, occ: int) -> int:
    """Compute sliding attacks (rook + bishop) from square with given occupancy."""
    init()
    return sliding_attacks(sq, occ)  # type: ignore[misc]


# ================================
# Bit utilities
# ================================
def mask_bits_positions(mask: int) -> Tuple[int, ...]:
    """Extract tuple of set bit positions from mask."""
    pos: List[int] = []
    m = mask
    while m:
        lsb = m & -m
        pos.append(lsb.bit_length() - 1)
        m ^= lsb  # XOR é mais rápido que m &= m - 1
    return tuple(pos)


# ================================
# Masks (unrolled loops onde possível)
# ================================
def mask_rook_attacks(sq: int) -> int:
    """Generate rook attack mask (excluding board edges)."""
    f = SQUARE_TO_FILE[sq]
    r = SQUARE_TO_RANK[sq]
    m = 0

    # Unrolled: evita branch em loop
    for rr in range(r + 1, 7):
        m |= 1 << (rr * 8 + f)

    for rr in range(r - 1, 0, -1):
        m |= 1 << (rr * 8 + f)

    for ff in range(f + 1, 7):
        m |= 1 << (r * 8 + ff)

    for ff in range(f - 1, 0, -1):
        m |= 1 << (r * 8 + ff)

    return m & U64


def mask_bishop_attacks(sq: int) -> int:
    """Generate bishop attack mask (excluding board edges)."""
    f = SQUARE_TO_FILE[sq]
    r = SQUARE_TO_RANK[sq]
    m = 0

    # up-right
    ff, rr = f + 1, r + 1
    while ff <= 6 and rr <= 6:
        m |= 1 << (rr * 8 + ff)
        ff += 1
        rr += 1

    # down-left
    ff, rr = f - 1, r - 1
    while ff >= 1 and rr >= 1:
        m |= 1 << (rr * 8 + ff)
        ff -= 1
        rr -= 1

    # down-right
    ff, rr = f - 1, r + 1
    while ff >= 1 and rr <= 6:
        m |= 1 << (rr * 8 + ff)
        ff -= 1
        rr += 1

    # up-left
    ff, rr = f + 1, r - 1
    while ff <= 6 and rr >= 1:
        m |= 1 << (rr * 8 + ff)
        ff += 1
        rr -= 1

    return m & U64


# ================================
# Ray-walk fallbacks (inlined + otimizado)
# ================================
def _rook_attacks_from_occupancy(sq: int, occ: int) -> int:
    """Calculate rook attacks given occupancy (used during table generation)."""
    f = SQUARE_TO_FILE[sq]
    r = SQUARE_TO_RANK[sq]
    attacks = 0

    # up
    for rr in range(r + 1, 8):
        s = rr * 8 + f
        attacks |= 1 << s
        if occ & (1 << s):
            break

    # down
    for rr in range(r - 1, -1, -1):
        s = rr * 8 + f
        attacks |= 1 << s
        if occ & (1 << s):
            break

    # right
    for ff in range(f + 1, 8):
        s = r * 8 + ff
        attacks |= 1 << s
        if occ & (1 << s):
            break

    # left
    for ff in range(f - 1, -1, -1):
        s = r * 8 + ff
        attacks |= 1 << s
        if occ & (1 << s):
            break

    return attacks & U64


def _bishop_attacks_from_occupancy(sq: int, occ: int) -> int:
    """Calculate bishop attacks given occupancy (used during table generation)."""
    f = SQUARE_TO_FILE[sq]
    r = SQUARE_TO_RANK[sq]
    attacks = 0

    # up-right
    ff, rr = f + 1, r + 1
    while ff < 8 and rr < 8:
        s = rr * 8 + ff
        attacks |= 1 << s
        if occ & (1 << s):
            break
        ff += 1
        rr += 1

    # down-left
    ff, rr = f - 1, r - 1
    while ff >= 0 and rr >= 0:
        s = rr * 8 + ff
        attacks |= 1 << s
        if occ & (1 << s):
            break
        ff -= 1
        rr -= 1

    # down-right
    ff, rr = f - 1, r + 1
    while ff >= 0 and rr < 8:
        s = rr * 8 + ff
        attacks |= 1 << s
        if occ & (1 << s):
            break
        ff -= 1
        rr += 1

    # up-left
    ff, rr = f + 1, r - 1
    while ff < 8 and rr >= 0:
        s = rr * 8 + ff
        attacks |= 1 << s
        if occ & (1 << s):
            break
        ff += 1
        rr -= 1

    return attacks & U64


# ================================
# Occupancy builder (micro-otimizado com unrolling parcial)
# ================================
def index_to_occupancy(index: int, positions: Tuple[int, ...]) -> int:
    """Convert index to occupancy bitboard from masked positions."""
    occ = 0
    for i, sq in enumerate(positions):
        if index & (1 << i):
            occ |= 1 << sq
    return occ


# ================================
# Table builder (otimizado)
# ================================
def _build_attack_table_for_square(
    sq: int,
    mask: int,
    positions: Tuple[int, ...],
    is_rook: bool,
    magic: int,
    shift: int,
) -> Tuple[int, ...]:
    """Build magic bitboard attack table for a single square."""
    bits = mask.bit_count()
    size = 1 << bits
    table_list: List[int | None] = [None] * size

    mask_local = mask & U64
    magic_local = magic & U64
    shift_local = shift
    u64_local = U64

    attacks_func = _rook_attacks_from_occupancy if is_rook else _bishop_attacks_from_occupancy

    for idx in range(size):
        occ = index_to_occupancy(idx, positions)
        att = attacks_func(sq, occ)
        compressed = (((occ & mask_local) * magic_local) & u64_local) >> shift_local

        if compressed >= size:
            raise RuntimeError(
                f"Index out of range: sq={sq} is_rook={is_rook} "
                f"idx={idx} compressed={compressed} size={size}"
            )

        existing = table_list[compressed]
        if existing is None:
            table_list[compressed] = att
        elif existing != att:
            raise RuntimeError(
                f"Magic collision: piece={'rook' if is_rook else 'bishop'} sq={sq} "
                f"idx={idx} compressed={compressed}"
            )

    return tuple(v if v is not None else 0 for v in table_list)


# ================================
# Magics validation (early exit)
# ================================
def _validate_magics() -> None:
    """Validate that magic numbers are properly loaded."""
    if len(ROOK_MAGICS) != 64 or len(BISHOP_MAGICS) != 64:
        raise RuntimeError("Invalid magics: expected 64 entries each.")

    for magics_list, name in [(ROOK_MAGICS, "ROOK"), (BISHOP_MAGICS, "BISHOP")]:
        for i, m in enumerate(magics_list):
            if not m or not isinstance(m, int) or not (0 < m < (1 << 64)):
                raise RuntimeError(f"Invalid {name}_MAGIC at {i}: {m!r}")


# ================================
# Fast function generators (captured locals, zero allocations)
# ================================
def _make_fast_rook_attacks(
    rook_masks: Tuple[int, ...],
    rook_magics: Tuple[int, ...],
    rook_shifts: Tuple[int, ...],
    rook_offsets: Tuple[int, ...],
    rook_table: Tuple[int, ...],
) -> callable:
    """Create optimized rook attack lookup with zero runtime overhead."""
    u64_val = U64

    def _rook(sq: int, occ: int) -> int:
        compressed = (((occ & rook_masks[sq]) * rook_magics[sq]) & u64_val) >> rook_shifts[sq]
        return rook_table[rook_offsets[sq] + compressed]

    return _rook


def _make_fast_bishop_attacks(
    bishop_masks: Tuple[int, ...],
    bishop_magics: Tuple[int, ...],
    bishop_shifts: Tuple[int, ...],
    bishop_offsets: Tuple[int, ...],
    bishop_table: Tuple[int, ...],
) -> callable:
    """Create optimized bishop attack lookup with zero runtime overhead."""
    u64_val = U64

    def _bishop(sq: int, occ: int) -> int:
        compressed = (((occ & bishop_masks[sq]) * bishop_magics[sq]) & u64_val) >> bishop_shifts[sq]
        return bishop_table[bishop_offsets[sq] + compressed]

    return _bishop


def _make_fast_sliding_attacks(rook_fn: callable, bishop_fn: callable) -> callable:
    """Create optimized sliding attack function (rook | bishop)."""
    def _sliding(sq: int, occ: int) -> int:
        return rook_fn(sq, occ) | bishop_fn(sq, occ)
    return _sliding


# ================================
# INIT (thread-safe, lazy, pré-aloca tudo)
# ================================
def init(validate: bool = True) -> None:
    """Initialize magic bitboard tables (lazy, thread-safe, immutable after init)."""
    global _ROOK_ATT_TABLE, _BISHOP_ATT_TABLE, _INITIALIZED
    global rook_attacks, bishop_attacks, sliding_attacks
    global ROOK_MASKS, BISHOP_MASKS, ROOK_RELEVANT_BITS, BISHOP_RELEVANT_BITS
    global ROOK_SHIFTS, BISHOP_SHIFTS, _ROOK_OFFSETS, _BISHOP_OFFSETS

    with _init_lock:
        if _INITIALIZED:
            return

        if validate:
            _validate_magics()

        _MASK_POSITIONS.clear()

        # Pre-build arrays
        rook_masks_list = []
        bishop_masks_list = []
        rook_relevant_bits_list = []
        bishop_relevant_bits_list = []
        rook_shifts_list = []
        bishop_shifts_list = []
        rook_offsets_list = []
        bishop_offsets_list = []

        # Build masks and shifts
        for sq in range(64):
            rmask = mask_rook_attacks(sq)
            bmask = mask_bishop_attacks(sq)

            rook_masks_list.append(rmask)
            bishop_masks_list.append(bmask)

            rb = rmask.bit_count()
            bb = bmask.bit_count()

            rook_relevant_bits_list.append(rb)
            bishop_relevant_bits_list.append(bb)

            rook_shifts_list.append(64 - rb)
            bishop_shifts_list.append(64 - bb)

            _MASK_POSITIONS[(sq, True)] = mask_bits_positions(rmask)
            _MASK_POSITIONS[(sq, False)] = mask_bits_positions(bmask)

        # Convert to tuples (immutable)
        ROOK_MASKS = tuple(rook_masks_list)
        BISHOP_MASKS = tuple(bishop_masks_list)
        ROOK_RELEVANT_BITS = tuple(rook_relevant_bits_list)
        BISHOP_RELEVANT_BITS = tuple(bishop_relevant_bits_list)
        ROOK_SHIFTS = tuple(rook_shifts_list)
        BISHOP_SHIFTS = tuple(bishop_shifts_list)

        # Calculate linear offsets
        rook_offset = 0
        for sq in range(64):
            rook_offsets_list.append(rook_offset)
            rook_offset += 1 << ROOK_RELEVANT_BITS[sq]

        bishop_offset = 0
        for sq in range(64):
            bishop_offsets_list.append(bishop_offset)
            bishop_offset += 1 << BISHOP_RELEVANT_BITS[sq]

        _ROOK_OFFSETS = tuple(rook_offsets_list)
        _BISHOP_OFFSETS = tuple(bishop_offsets_list)

        # Build attack tables
        rook_table_list: List[int] = []
        bishop_table_list: List[int] = []

        for sq in range(64):
            r_positions = _MASK_POSITIONS[(sq, True)]
            b_positions = _MASK_POSITIONS[(sq, False)]

            r_table = _build_attack_table_for_square(
                sq,
                ROOK_MASKS[sq],
                r_positions,
                True,
                ROOK_MAGICS[sq],
                ROOK_SHIFTS[sq],
            )
            rook_table_list.extend(r_table)

            b_table = _build_attack_table_for_square(
                sq,
                BISHOP_MASKS[sq],
                b_positions,
                False,
                BISHOP_MAGICS[sq],
                BISHOP_SHIFTS[sq],
            )
            bishop_table_list.extend(b_table)

        _ROOK_ATT_TABLE = tuple(rook_table_list)
        _BISHOP_ATT_TABLE = tuple(bishop_table_list)

        # Rebind fast implementations
        fast_rook = _make_fast_rook_attacks(
            ROOK_MASKS, ROOK_MAGICS, ROOK_SHIFTS, _ROOK_OFFSETS, _ROOK_ATT_TABLE
        )
        fast_bishop = _make_fast_bishop_attacks(
            BISHOP_MASKS, BISHOP_MAGICS, BISHOP_SHIFTS, _BISHOP_OFFSETS, _BISHOP_ATT_TABLE
        )
        fast_sliding = _make_fast_sliding_attacks(fast_rook, fast_bishop)

        rook_attacks = fast_rook  # type: ignore[assignment]
        bishop_attacks = fast_bishop  # type: ignore[assignment]
        sliding_attacks = fast_sliding  # type: ignore[assignment]

        _INITIALIZED = True


# ================================
# Debug
# ================================
def show_bitboard(bb: int) -> str:
    """Display bitboard as ASCII art."""
    rows = []
    for rank in range(7, -1, -1):
        row = []
        base = rank * 8
        for file in range(8):
            sq = base + file
            row.append("1" if (bb >> sq) & 1 else ".")
        rows.append(" ".join(row))
    return "\n".join(rows)


__all__ = [
    "init",
    "rook_attacks",
    "bishop_attacks",
    "sliding_attacks",
    "lsb_index",
    "msb_index",
    "ROOK_MASKS",
    "BISHOP_MASKS",
    "ROOK_GOOD_MAGICS",
    "BISHOP_GOOD_MAGICS",
    "ROOK_ATTACK_OFFSETS",
    "BISHOP_ATTACK_OFFSETS",
    "ROOK_SHIFTS",
    "BISHOP_SHIFTS",
    "_MASK_POSITIONS",
    "_INITIALIZED",
    "_rook_attacks_from_occupancy",
    "_bishop_attacks_from_occupancy"
]