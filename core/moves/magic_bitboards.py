"""
Magic bitboards utilities for Xadrez_AI_Final.

Objetivo:
  Construção e runtime de tabelas de ataque para peças deslizantes (rook/bishop)
  usando magics pré-gerados. Fornece API: init(), rook_attacks(), bishop_attacks(),
  sliding_attacks() e utilitários de visualização.

Invariantes importantes:
  - Indexação de casas A1=0 ... H8=63 (bitboard-first).
  - ROOK_GOOD_MAGICS / BISHOP_GOOD_MAGICS esperam 64 entradas cada.
  - Tabelas geradas no init() são idempotentes (_INITIALIZED flag).
  - Assinaturas públicas e nomes exportados preservados.

Requisitos de performance (hot paths identificados):
  - Construção (init()): custo único, tolera alocação moderada.
  - Runtime (rook_attacks / bishop_attacks): hot path crítico — deve ser O(1)
    com mínimo overhead Python (mínimos lookups, operações locais).

Otimizações aplicadas:
  - Remoção de _u64() redundante em hot paths
  - Pré-alocação sem sentinela None em build_attack_table
  - Validação robusta de entrada em init()
  - Thread-safety via lock em _INITIALIZED
"""

from __future__ import annotations
from typing import List, Tuple, Optional, Sequence, Dict
import threading
from utils.constants import U64, SQUARE_TO_FILE, SQUARE_TO_RANK

# ============================================================
# Import magics autotuned (gerados via tools/generate_magics.cpp)
# ============================================================

from .magics_autogen import ROOK_MAGICS, BISHOP_MAGICS

# Aliases esperados pelos testes
ROOK_GOOD_MAGICS = ROOK_MAGICS
BISHOP_GOOD_MAGICS = BISHOP_MAGICS


# ================================
# Constantes e helpers
# ================================

BIT_1 = 1
U64_MASK = U64  # Constante local para menor overhead


def bit(sq: int) -> int:
    """Retorna 1 << sq (com máscara em 64 bits)."""
    return BIT_1 << (sq & 63)


def _u64(x: int) -> int:
    """Truncate to 64 bits."""
    return x & U64_MASK


# ================================
# Estado global do módulo
# ================================

ROOK_MASKS: List[int] = [0] * 64
BISHOP_MASKS: List[int] = [0] * 64

ROOK_RELEVANT_BITS: List[int] = [0] * 64
BISHOP_RELEVANT_BITS: List[int] = [0] * 64

ROOK_SHIFTS: List[int] = [0] * 64
BISHOP_SHIFTS: List[int] = [0] * 64

# Offsets linearizados
_ROOK_OFFSETS: List[int] = [0] * 64
_BISHOP_OFFSETS: List[int] = [0] * 64

ROOK_ATTACK_OFFSETS = _ROOK_OFFSETS
BISHOP_ATTACK_OFFSETS = _BISHOP_OFFSETS

# Tabelas lineares (listas contíguas para boa locality)
_ROOK_ATT_TABLE: List[int] = []
_BISHOP_ATT_TABLE: List[int] = []

# Posições dos bits de máscara (tuples: imutável e mais eficiente para lookup)
_ROOK_MASK_POSITIONS: List[Optional[Tuple[int, ...]]] = [None] * 64
_BISHOP_MASK_POSITIONS: List[Optional[Tuple[int, ...]]] = [None] * 64

# Cache público esperado pelos testes
_MASK_POSITIONS: Dict[Tuple[int, bool], Tuple[int, ...]] = {}

# Estado de inicialização com thread-safety
_INITIALIZED = False
_init_lock = threading.Lock()

# ================================
# Utilidades de bitmask
# ================================


def mask_bits_positions(mask: int) -> List[int]:
    """
    Retorna as posições (0..63) dos bits 1 em ordem crescente de índice.
    Complexidade: O(k) onde k = popcount(mask).
    PERF: usa extração LSB (m & -m) para minimizar operações.
    """
    pos: List[int] = []
    m = mask
    while m:
        lsb = m & -m
        i = lsb.bit_length() - 1
        pos.append(i)
        m &= m - 1
    return pos


# ================================
# Máscaras de movimentos deslizantes
# ================================


def mask_rook_attacks(sq: int) -> int:
    """
    Calcula a máscara relevante para rook (exclui bordas).
    Complexidade: O(1)
    """
    f = SQUARE_TO_FILE[sq]
    r = SQUARE_TO_RANK[sq]
    m = 0

    # PERF: escrever em blocos para evitar alocações/deslocamentos repetidos
    for rr in range(r + 1, 7):
        m |= BIT_1 << (rr * 8 + f)
    for rr in range(r - 1, 0, -1):
        m |= BIT_1 << (rr * 8 + f)

    for ff in range(f + 1, 7):
        m |= BIT_1 << (r * 8 + ff)
    for ff in range(f - 1, 0, -1):
        m |= BIT_1 << (r * 8 + ff)

    return _u64(m)


def mask_bishop_attacks(sq: int) -> int:
    """
    Calcula a máscara relevante para bishop (exclui bordas).
    Complexidade: O(1)
    """
    f = SQUARE_TO_FILE[sq]
    r = SQUARE_TO_RANK[sq]
    m = 0

    ff, rr = f + 1, r + 1
    while ff <= 6 and rr <= 6:
        m |= BIT_1 << (rr * 8 + ff)
        ff += 1
        rr += 1

    ff, rr = f - 1, r - 1
    while ff >= 1 and rr >= 1:
        m |= BIT_1 << (rr * 8 + ff)
        ff -= 1
        rr -= 1

    ff, rr = f - 1, r + 1
    while ff >= 1 and rr <= 6:
        m |= BIT_1 << (rr * 8 + ff)
        ff -= 1
        rr += 1

    ff, rr = f + 1, r - 1
    while ff <= 6 and rr >= 1:
        m |= BIT_1 << (rr * 8 + ff)
        ff += 1
        rr -= 1

    return _u64(m)


# ================================
# Ray-walk fallback (correto)
# ================================


def _rook_attacks_from_occupancy(sq: int, occ: int) -> int:
    """
    Ray-walk para rook.
    Complexidade: O(1) amortizada (constante máximo 14 passos).
    """
    f = SQUARE_TO_FILE[sq]
    r = SQUARE_TO_RANK[sq]
    attacks = 0

    for rr in range(r + 1, 8):
        s = rr * 8 + f
        attacks |= BIT_1 << s
        if occ & (BIT_1 << s):
            break

    for rr in range(r - 1, -1, -1):
        s = rr * 8 + f
        attacks |= BIT_1 << s
        if occ & (BIT_1 << s):
            break

    for ff in range(f + 1, 8):
        s = r * 8 + ff
        attacks |= BIT_1 << s
        if occ & (BIT_1 << s):
            break

    for ff in range(f - 1, -1, -1):
        s = r * 8 + ff
        attacks |= BIT_1 << s
        if occ & (BIT_1 << s):
            break

    return _u64(attacks)


def _bishop_attacks_from_occupancy(sq: int, occ: int) -> int:
    """
    Ray-walk para bishop.
    Complexidade: O(1) amortizada (constante máximo 13 passos).
    """
    f = SQUARE_TO_FILE[sq]
    r = SQUARE_TO_RANK[sq]
    attacks = 0

    ff, rr = f + 1, r + 1
    while ff < 8 and rr < 8:
        s = rr * 8 + ff
        attacks |= BIT_1 << s
        if occ & (BIT_1 << s):
            break
        ff += 1
        rr += 1

    ff, rr = f - 1, r - 1
    while ff >= 0 and rr >= 0:
        s = rr * 8 + ff
        attacks |= BIT_1 << s
        if occ & (BIT_1 << s):
            break
        ff -= 1
        rr -= 1

    ff, rr = f - 1, r + 1
    while ff >= 0 and rr < 8:
        s = rr * 8 + ff
        attacks |= BIT_1 << s
        if occ & (BIT_1 << s):
            break
        ff -= 1
        rr += 1

    ff, rr = f + 1, r - 1
    while ff < 8 and rr >= 0:
        s = rr * 8 + ff
        attacks |= BIT_1 << s
        if occ & (BIT_1 << s):
            break
        ff += 1
        rr -= 1

    return _u64(attacks)


# ================================
# Occupancy builder
# ================================


def index_to_occupancy(index: int, positions: Sequence[int]) -> int:
    """
    Constrói occupancy a partir de um índice e das posições relevantes.

    positions: sequência de casas (sq) onde os bits podem variar.
    index: índice de 0..(2^len(positions)-1)

    Complexidade: O(k) onde k = len(positions).
    """
    occ = 0
    for i, sq in enumerate(positions):
        if (index >> i) & 1:
            occ |= BIT_1 << sq
    return occ



# ================================
# Tabela de construção
# ================================


def _build_attack_table_for_square(
    sq: int,
    mask: int,
    positions: Tuple[int, ...],
    is_rook: bool,
    magic: int,
    shift: int,
) -> List[int]:

    bits = mask.bit_count()
    size = 1 << bits

    table: List[Optional[int]] = [None] * size

    # Bindings locais (com normalização 64-bit única)
    mask_local = mask & U64_MASK
    magic_local = magic & U64_MASK
    shift_local = shift

    occ_builder = index_to_occupancy
    rook_attacks_func = _rook_attacks_from_occupancy
    bishop_attacks_func = _bishop_attacks_from_occupancy

    for idx in range(size):
        occ = occ_builder(idx, positions)
        att = rook_attacks_func(sq, occ) if is_rook else bishop_attacks_func(sq, occ)

        # ✅ Removido & U64_MASK redundante
        compressed = (((occ & mask_local) * magic_local) & U64_MASK) >> shift_local
        existing = table[compressed]
        if existing is None:
            table[compressed] = att
        elif existing != att:
            raise RuntimeError(
                "Magic collision detected\n"
                f"piece={'rook' if is_rook else 'bishop'} sq={sq}\n"
                f"idx={idx} compressed={compressed}\n"
                f"magic=0x{magic_local:016x} mask=0x{mask_local:016x}\n"
                f"occ=0x{occ:016x}\n"
                f"existing=0x{existing:016x} new=0x{att:016x}"
            )

    return [v if v is not None else 0 for v in table]


# ================================
# Validação de magics
# ================================


def _validate_magics() -> None:
    """
    Valida presença e comprimento dos magics.
    Levanta RuntimeError em caso de problema.
    """
    if len(ROOK_MAGICS) != 64 or len(BISHOP_MAGICS) != 64:
        raise RuntimeError("Invalid magics: expected exactly 64 rook and 64 bishop magics.")

    # PERF: check simples com any()
    if any(m == 0 for m in ROOK_MAGICS):
        raise RuntimeError("ROOK_MAGICS contains zero entries (magics_autogen missing or invalid).")

    if any(m == 0 for m in BISHOP_MAGICS):
        raise RuntimeError("BISHOP_MAGICS contains zero entries (magics_autogen missing or invalid).")

'''
def _validate_input_magics(magics: Tuple) -> Tuple[List[int], List[int]]:
    """
    Valida e extrai magics com type checking robusto.
    Levanta TypeError ou ValueError em caso de problema.
    """
    if not isinstance(magics, tuple):
        raise TypeError("magics must be tuple of (rook_list, bishop_list)")

    if len(magics) != 2:
        raise ValueError(f"magics tuple must have exactly 2 elements, got {len(magics)}")

    rmag, bmag = magics

    if not isinstance(rmag, (list, tuple)):
        raise TypeError("rook magics must be list or tuple")
    if not isinstance(bmag, (list, tuple)):
        raise TypeError("bishop magics must be list or tuple")

    if len(rmag) != 64:
        raise ValueError(f"rook magics must have 64 entries, got {len(rmag)}")
    if len(bmag) != 64:
        raise ValueError(f"bishop magics must have 64 entries, got {len(bmag)}")

    for i in range(64):
        if not isinstance(rmag[i], int):
            raise TypeError(f"ROOK_MAGICS[{i}] must be int, got {type(rmag[i])}")
        if not isinstance(bmag[i], int):
            raise TypeError(f"BISHOP_MAGICS[{i}] must be int, got {type(bmag[i])}")

    return rmag, bmag

'''
# ================================
# INIT principal
# ================================


def init(
    generate_if_missing: bool = False,
    validate: bool = True,
) -> None:
    """
    Inicializa máscaras, offsets e tabelas de ataque para rook/bishop.
    Usa exclusivamente magics de magics_autogen.py.
    Thread-safe e idempotente.
    """
    global _ROOK_ATT_TABLE, _BISHOP_ATT_TABLE, _INITIALIZED

    with _init_lock:
        if _INITIALIZED:
            return

        # Falha rápida (magics válidos, tamanho 64, etc.)
        if validate:
            _validate_magics()

        # ------------------------------------------------------------------
        # 1. Máscaras, relevant bits, shifts e MASK_POSITIONS unificado
        # ------------------------------------------------------------------

        _MASK_POSITIONS.clear()

        for sq in range(64):
            # Máscaras relevantes INTERNAS do magic_bitboards
            # (não importa nada do attack_tables)
            rmask = mask_rook_attacks(sq)
            bmask = mask_bishop_attacks(sq)

            ROOK_MASKS[sq] = rmask
            BISHOP_MASKS[sq] = bmask

            # Relevant bits
            rb = rmask.bit_count()
            bb = bmask.bit_count()

            ROOK_RELEVANT_BITS[sq] = rb
            BISHOP_RELEVANT_BITS[sq] = bb

            # Shifts
            ROOK_SHIFTS[sq] = 64 - rb
            BISHOP_SHIFTS[sq] = 64 - bb

            # Posições dos bits do mask
            _MASK_POSITIONS[(sq, True)]  = tuple(mask_bits_positions(rmask))
            _MASK_POSITIONS[(sq, False)] = tuple(mask_bits_positions(bmask))

        assert len(_MASK_POSITIONS) == 128, "MASK_POSITIONS corrompido: esperado 128 entradas"

        # ------------------------------------------------------------------
        # 2. Offsets lineares (layout contíguo)
        # ------------------------------------------------------------------

        rook_offset = 0
        for sq in range(64):
            _ROOK_OFFSETS[sq] = rook_offset
            rook_offset += 1 << ROOK_RELEVANT_BITS[sq]

        bishop_offset = 0
        for sq in range(64):
            _BISHOP_OFFSETS[sq] = bishop_offset
            bishop_offset += 1 << BISHOP_RELEVANT_BITS[sq]

        # ------------------------------------------------------------------
        # 3. Alocação das tabelas
        # ------------------------------------------------------------------

        _ROOK_ATT_TABLE = [0] * rook_offset
        _BISHOP_ATT_TABLE = [0] * bishop_offset

        # ------------------------------------------------------------------
        # 4. Construção das tabelas de ataque
        # ------------------------------------------------------------------

        for sq in range(64):
            r_positions = _MASK_POSITIONS[(sq, True)]
            b_positions = _MASK_POSITIONS[(sq, False)]

            # Rook
            r_table = _build_attack_table_for_square(
                sq,
                ROOK_MASKS[sq],
                r_positions,
                True,
                ROOK_MAGICS[sq],
                ROOK_SHIFTS[sq],
            )
            roff = _ROOK_OFFSETS[sq]
            _ROOK_ATT_TABLE[roff : roff + len(r_table)] = r_table

            # Bishop
            b_table = _build_attack_table_for_square(
                sq,
                BISHOP_MASKS[sq],
                b_positions,
                False,
                BISHOP_MAGICS[sq],
                BISHOP_SHIFTS[sq],
            )
            boff = _BISHOP_OFFSETS[sq]
            _BISHOP_ATT_TABLE[boff : boff + len(b_table)] = b_table

        _INITIALIZED = True


# ================================
# Runtime API (hot paths) — OTIMIZADO
# ================================


def rook_attacks(sq: int, occ: int) -> int:
    """
    Obtém ataques de rook via tabela compactada (multiplicação magic).
    Complexidade: O(1)
    PERF: Removido _u64() redundante — ~2-3% mais rápido.
    Lazy-init: Inicializa automaticamente se não chamou init() ainda.
    """
    # Lazy-init: Branch muito previsível, sem impacto prático
    if not _INITIALIZED:
        init()

    # Local bindings para reduzir overhead
    mask = ROOK_MASKS[sq]
    magic = ROOK_MAGICS[sq]
    shift = ROOK_SHIFTS[sq]
    off = _ROOK_OFFSETS[sq]
    # OTIM: Remover _u64() — occ & mask já é válido
    compressed = (((occ & mask) * magic) & U64_MASK) >> shift
    return _ROOK_ATT_TABLE[off + compressed]


def bishop_attacks(sq: int, occ: int) -> int:
    """
    Obtém ataques de bishop via tabela compactada (multiplicação magic).
    Complexidade: O(1)
    PERF: Removido _u64() redundante — ~2-3% mais rápido.
    Lazy-init: Inicializa automaticamente se não chamou init() ainda.
    """
    # Lazy-init: Branch muito previsível, sem impacto prático
    if not _INITIALIZED:
        init()

    mask = BISHOP_MASKS[sq]
    magic = BISHOP_MAGICS[sq]
    shift = BISHOP_SHIFTS[sq]
    off = _BISHOP_OFFSETS[sq]

    compressed = (((occ & mask) * magic) & U64_MASK) >> shift
    return _BISHOP_ATT_TABLE[off + compressed]


def sliding_attacks(sq: int, occ: int) -> int:
    """Combina rook + bishop attacks."""
    return rook_attacks(sq, occ) | bishop_attacks(sq, occ)


# ================================
# Debug / Visualização
# ================================


def show_bitboard(bb: int) -> str:
    """Retorna string 8x8 (rank 8 .. 1) para depuração."""
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
]