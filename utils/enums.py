# utils/enums.py
"""
Enums fundamentais do Xadrez_AI_Final.

Objetivo:
    Definir enums primários usados por todo o projeto (cores, tipos de peças,
    tipos de movimento e resultado do jogo) mantendo compatibilidade binária
    (IntEnum) e a indexação A1=0 .. H8=63.

Invariantes importantes:
    - Indexação do tabuleiro A1=0 .. H8=63 é mantida por todo o projeto.
    - Valores numéricos dos enums são ABI interna e NÃO devem ser alterados.
    - PieceIndex é um alias semântico para índices 0..11 (bitboards).
"""

from __future__ import annotations

from enum import IntEnum
from typing import TypeAlias, Tuple

# ---------------------------------------------------------------------
# Semantic alias (não é wrapper, não é classe, é contrato semântico)
# ---------------------------------------------------------------------
PieceIndex: TypeAlias = int

__all__ = [
    "Color",
    "PieceType",
    "MoveType",
    "GameResult",
    "PieceIndex",
    "piece_index",
]

# ---------------------------------------------------------------------
# Base offsets para cálculo de peça por cor
# ---------------------------------------------------------------------
# WHITE -> 0
# BLACK -> 6
_PIECE_INDEX_BASE: Tuple[int, int] = (0, 6)


# ---------------------------------------------------------------------
# Color
# ---------------------------------------------------------------------
class Color(IntEnum):
    WHITE = 0
    BLACK = 1


# ---------------------------------------------------------------------
# PieceType
# ---------------------------------------------------------------------
class PieceType(IntEnum):
    PAWN   = 0
    KNIGHT = 1
    BISHOP = 2
    ROOK   = 3
    QUEEN  = 4
    KING   = 5


# ---------------------------------------------------------------------
# MoveType (ENXUTO: 6 tipos, conforme sua suíte de testes)
# ---------------------------------------------------------------------
class MoveType(IntEnum):
    QUIET      = 0
    CAPTURE    = 1
    PROMOTION  = 2
    PROMO_CAP  = 3
    EN_PASSANT = 4
    CASTLE     = 5


# ---------------------------------------------------------------------
# GameResult
# ---------------------------------------------------------------------
class GameResult(IntEnum):
    ONGOING   = 0
    WHITE_WIN = 1
    BLACK_WIN = 2
    DRAW      = 3


# ---------------------------------------------------------------------
# Fast mapping: (PieceType, Color) -> PieceIndex
# ---------------------------------------------------------------------
def piece_index(piece_type: PieceType, color: Color) -> PieceIndex:
    """
    Mapeia (piece_type, color) -> PieceIndex [0..11].

    Layout fixo:
        0..5  = White: [P, N, B, R, Q, K]
        6..11 = Black: [P, N, B, R, Q, K]

    Formula:
        idx = base[color] + piece_type

    Isso é equivalente ao que Stockfish faz internamente:
        piece = pieceType + (color << 3)   (em C/C++)
    mas usando offset 6 pela tua decisão arquitetural.

    Sem multiplicação.
    Sem branches.
    O(1), 2 loads, 1 soma.
    """
    return _PIECE_INDEX_BASE[int(color)] + int(piece_type)
