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
# Semantic alias (contrato semântico, não é wrapper)
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
# MoveType (6 tipos, alinhado com a suíte de testes)
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

    # Draw reasons
    DRAW_STALEMATE = 3
    DRAW_REPETITION = 4
    DRAW_FIFTY_MOVE = 5
    DRAW_INSUFFICIENT_MATERIAL = 6

    # Generic draw catch-all (optional)
    DRAW_OTHER = 7


# ---------------------------------------------------------------------
# Fast mapping: (PieceType, Color) -> PieceIndex
# ---------------------------------------------------------------------
def piece_index(piece_type: PieceType, color: Color) -> PieceIndex:
    """
    Mapeia (piece_type, color) -> PieceIndex [0..11].

    Layout fixo:
        0..5  = White: [P, N, B, R, Q, K]
        6..11 = Black: [P, N, B, R, Q, K]

    Fórmula:
        idx = _PIECE_INDEX_BASE[color] + piece_type

    Propriedades:
        - O(1)
        - Sem branches de controle
        - Apenas 2 loads + 1 soma

    Validação:
        Garante tipos corretos para evitar corrupção silenciosa de índice.
    """
    if not isinstance(piece_type, PieceType):
        raise TypeError(f"piece_type inválido: esperado PieceType, recebido {type(piece_type).__name__}")
    if not isinstance(color, Color):
        raise TypeError(f"color inválido: esperado Color, recebido {type(color).__name__}")

    return _PIECE_INDEX_BASE[int(color)] + int(piece_type)
