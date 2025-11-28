from __future__ import annotations

import threading
from typing import Dict, List, Tuple

from utils.constants import U64
from utils.enums import Color

# ============================================================
# Public tables (filled by init)
# ============================================================

KNIGHT_ATTACKS: List[int] = [0] * 64
KING_ATTACKS: List[int] = [0] * 64
PAWN_ATTACKS: Dict[Color, List[int]] = {
    Color.WHITE: [0] * 64,
    Color.BLACK: [0] * 64,
}

# Optional geometry rays (debug / consistency)
ROOK_GEOMETRY_RAYS: List[int] = [0] * 64
BISHOP_GEOMETRY_RAYS: List[int] = [0] * 64

# Bound at init (magic or fallback)
_magic_rook_attacks = None
_magic_bishop_attacks = None

# Initialization guard
_INITIALIZED: bool = False
_init_lock = threading.Lock()

# ============================================================
# File masks (A1 = 0 .. H8 = 63)
# ============================================================

FILE_A = 0x0101010101010101
FILE_B = 0x0202020202020202
FILE_G = 0x4040404040404040
FILE_H = 0x8080808080808080

FILE_AB = FILE_A | FILE_B
FILE_GH = FILE_G | FILE_H


# ============================================================
# Precomputation helpers
# ============================================================

def _build_attack_table(generator) -> List[int]:
    """
    Gera uma tabela de ataques 64x1 a partir de um gerador (sq -> bitboard).
    Centraliza a lógica e remove duplicidade.
    """
    table = [0] * 64
    for sq in range(64):
        table[sq] = generator(sq) & U64
    return table


def _knight_attack_from(sq: int) -> int:
    """Retorna o bitboard de ataques do cavalo a partir de sq."""
    bb = 1 << sq
    att = 0

    att |= (bb << 17) & ~FILE_A
    att |= (bb << 15) & ~FILE_H
    att |= (bb << 10) & ~FILE_AB
    att |= (bb << 6) & ~FILE_GH

    att |= (bb >> 17) & ~FILE_H
    att |= (bb >> 15) & ~FILE_A
    att |= (bb >> 10) & ~FILE_GH
    att |= (bb >> 6) & ~FILE_AB

    return att


def _king_attack_from(sq: int) -> int:
    """Retorna o bitboard de ataques do rei a partir de sq."""
    bb = 1 << sq
    att = 0

    # Vertical
    att |= (bb << 8)
    att |= (bb >> 8)

    # Horizontal + diagonais
    att |= (bb << 1) & ~FILE_A
    att |= (bb >> 1) & ~FILE_H
    att |= (bb << 9) & ~FILE_A
    att |= (bb << 7) & ~FILE_H
    att |= (bb >> 7) & ~FILE_A
    att |= (bb >> 9) & ~FILE_H

    return att


def _build_pawn_attack_tables() -> Dict[Color, List[int]]:
    """Gera tabelas de ataque para peões brancos e pretos."""
    white = [0] * 64
    black = [0] * 64

    for sq in range(64):
        bb = 1 << sq

        # Peão branco
        west_w = (bb & ~FILE_A) << 7
        east_w = (bb & ~FILE_H) << 9
        white[sq] = (west_w | east_w) & U64

        # Peão preto
        west_b = (bb & ~FILE_A) >> 9
        east_b = (bb & ~FILE_H) >> 7
        black[sq] = (west_b | east_b) & U64

    return {Color.WHITE: white, Color.BLACK: black}


# ============================================================
# Fallback sliding attacks (ray-walk seguro)
# ============================================================

def _fallback_sliding_attacks(
    sq: int,
    occ: int,
    directions: Tuple[int, ...],
) -> int:
    """
    Fallback genérico para peças deslizantes.

    Usado apenas se Magic Bitboards falharem ou não estiverem disponíveis.
    """
    attacks = 0
    file = sq & 7
    rank = sq >> 3

    for delta in directions:
        s = sq
        cf, cr = file, rank

        while True:
            s += delta
            if s < 0 or s >= 64:
                break

            nf, nr = s & 7, s >> 3

            # Detecção de wrap-around (especialmente horizontais/diagonais)
            if abs(nf - cf) > 1 or (abs(nr - cr) > 1 and abs(delta) != 8):
                break

            bit = 1 << s
            attacks |= bit

            if occ & bit:
                break

            cf, cr = nf, nr

    return attacks & U64


def _fallback_rook_attacks(sq: int, occ: int) -> int:
    """Fallback para torre: N, S, E, W."""
    return _fallback_sliding_attacks(sq, occ, (8, -8, 1, -1))


def _fallback_bishop_attacks(sq: int, occ: int) -> int:
    """Fallback para bispo: diagonais."""
    return _fallback_sliding_attacks(sq, occ, (9, 7, -9, -7))


# ============================================================
# Geometry rays sync (debug)
# ============================================================

def _compute_ray_masks_from_magic(mb_module) -> None:
    """
    Sincroniza máscaras geométricas (rook/bishop) se disponíveis
    no módulo magic_bitboards.
    """
    rook_masks = getattr(mb_module, "ROOK_MASKS", None)
    if isinstance(rook_masks, (list, tuple)) and len(rook_masks) == 64:
        ROOK_GEOMETRY_RAYS[:] = rook_masks

    bishop_masks = getattr(mb_module, "BISHOP_MASKS", None)
    if isinstance(bishop_masks, (list, tuple)) and len(bishop_masks) == 64:
        BISHOP_GEOMETRY_RAYS[:] = bishop_masks


# ============================================================
# Init
# ============================================================

def init() -> None:
    """
    Inicializa tabelas de ataque e resolve a implementação
    de sliding attacks (Magic Bitboards ou fallback).
    """
    global _INITIALIZED, _magic_rook_attacks, _magic_bishop_attacks

    if _INITIALIZED:
        return

    with _init_lock:
        if _INITIALIZED:
            return

        # Pré-computação de ataques fixos
        knight_table = _build_attack_table(_knight_attack_from)
        king_table = _build_attack_table(_king_attack_from)
        pawn_tables = _build_pawn_attack_tables()

        KNIGHT_ATTACKS[:] = knight_table
        KING_ATTACKS[:] = king_table

        for color in (Color.WHITE, Color.BLACK):
            PAWN_ATTACKS[color][:] = pawn_tables[color]

        # Magic Bitboards (se disponíveis)
        try:
            from core.moves import magic_bitboards as mb

            mb.init()
            _magic_rook_attacks = getattr(mb, "rook_attacks", _fallback_rook_attacks)
            _magic_bishop_attacks = getattr(mb, "bishop_attacks", _fallback_bishop_attacks)

            _compute_ray_masks_from_magic(mb)

        except Exception:
            # Fallback seguro
            _magic_rook_attacks = _fallback_rook_attacks
            _magic_bishop_attacks = _fallback_bishop_attacks

        # Sanidade mínima
        assert len(KNIGHT_ATTACKS) == 64
        assert len(KING_ATTACKS) == 64
        assert len(PAWN_ATTACKS[Color.WHITE]) == 64
        assert len(PAWN_ATTACKS[Color.BLACK]) == 64

        _INITIALIZED = True


# ============================================================
# Public runtime API
# ============================================================

def knight_attacks(sq: int) -> int:
    """Retorna ataques de cavalo a partir de sq."""
    if not _INITIALIZED:
        init()
    return KNIGHT_ATTACKS[sq]


def king_attacks(sq: int) -> int:
    """Retorna ataques de rei a partir de sq."""
    if not _INITIALIZED:
        init()
    return KING_ATTACKS[sq]


def pawn_attacks(sq: int, color: Color) -> int:
    """Retorna ataques de peão por cor."""
    if not _INITIALIZED:
        init()
    return PAWN_ATTACKS[color][sq]


def rook_attacks(sq: int, occ: int) -> int:
    """Retorna ataques de torre considerando ocupação."""
    if not _INITIALIZED:
        init()
    return _magic_rook_attacks(sq, occ)


def bishop_attacks(sq: int, occ: int) -> int:
    """Retorna ataques de bispo considerando ocupação."""
    if not _INITIALIZED:
        init()
    return _magic_bishop_attacks(sq, occ)


def queen_attacks(sq: int, occ: int) -> int:
    """Retorna ataques de dama combinando torre + bispo."""
    if not _INITIALIZED:
        init()
    return _magic_rook_attacks(sq, occ) | _magic_bishop_attacks(sq, occ)


# ============================================================
# Exports
# ============================================================

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
    "ROOK_GEOMETRY_RAYS",
    "BISHOP_GEOMETRY_RAYS",
    "_INITIALIZED",
]
