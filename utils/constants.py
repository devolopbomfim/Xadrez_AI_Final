# utils/constants.py
"""
Constantes e utilitários bitboard do Xadrez_AI_Final.

Design:
    - Bitboard-first
    - A1 = 0 .. H8 = 63
    - 64-bit masking explícito (U64)
    - Estruturas imutáveis e O(1)
"""

from __future__ import annotations
from typing import Final

# =========================================================
# 64-bit mask
# =========================================================
U64: Final[int] = 0xFFFFFFFFFFFFFFFF


# =========================================================
# Helpers básicos
# =========================================================
def bit(square: int) -> int:
    """Retorna um bitboard com o bit de `square` ligado."""
    return (1 << square) & U64


def sq(file_idx: int, rank_idx: int) -> int:
    """
    Converte (file, rank) -> índice [0..63], A1 = 0.

    Layout:
        rank_idx * 8 + file_idx

    Visualização:
        A1 = (0,0) -> 0
        H8 = (7,7) -> 63
    """
    return (rank_idx << 3) | file_idx


# =========================================================
# File masks
# =========================================================
FILE_A = 0x0101010101010101
FILE_B = FILE_A << 1
FILE_C = FILE_A << 2
FILE_D = FILE_A << 3
FILE_E = FILE_A << 4
FILE_F = FILE_A << 5
FILE_G = FILE_A << 6
FILE_H = FILE_A << 7

FILES_MASKS = (
    FILE_A, FILE_B, FILE_C, FILE_D,
    FILE_E, FILE_F, FILE_G, FILE_H
)

# =========================================================
# Rank masks
# =========================================================
RANK_1 = 0x00000000000000FF
RANK_2 = RANK_1 << 8
RANK_3 = RANK_1 << 16
RANK_4 = RANK_1 << 24
RANK_5 = RANK_1 << 32
RANK_6 = RANK_1 << 40
RANK_7 = RANK_1 << 48
RANK_8 = RANK_1 << 56

RANKS_MASKS = (
    RANK_1, RANK_2, RANK_3, RANK_4,
    RANK_5, RANK_6, RANK_7, RANK_8
)

# =========================================================
# Center masks
# =========================================================
CENTER_4_MASK = (
    bit(sq(3, 3)) |  # D4
    bit(sq(4, 3)) |  # E4
    bit(sq(3, 4)) |  # D5
    bit(sq(4, 4))    # E5
) & U64

EXTENDED_CENTER = (RANK_4 | RANK_5) & U64


# =========================================================
# Diagonals
# =========================================================
DIAGONAL_A1H8 = 0x8040201008040201
ANTI_DIAGONAL_H1A8 = 0x0102040810204080


# =========================================================
# Directions (square deltas)
# =========================================================
NORTH = 8
SOUTH = -8
EAST  = 1
WEST  = -1

NORTH_EAST = 9
NORTH_WEST = 7
SOUTH_EAST = -7
SOUTH_WEST = -9


# =========================================================
# Counts (alinhadas à ABI interna)
# =========================================================
PIECE_TYPES = 6       # PAWN..KING
COLOR_COUNT = 2       # WHITE/BLACK
PIECE_COUNT = 12      # 6 * 2
MOVE_TYPE_COUNT = 6   # fixo, ABI com enums.MoveType


# =========================================================
# Square tables
# =========================================================
SQUARE_TO_FILE = tuple(i & 7 for i in range(64))
SQUARE_TO_RANK = tuple(i >> 3 for i in range(64))
SQUARE_BB = tuple((1 << i) & U64 for i in range(64))


# =========================================================
# Edge masks
# =========================================================
NOT_FILE_A  = (~FILE_A) & U64
NOT_FILE_H  = (~FILE_H) & U64
NOT_FILE_AB = (~(FILE_A | FILE_B)) & U64
NOT_FILE_GH = (~(FILE_G | FILE_H)) & U64


# =========================================================
# Pawn helpers
# =========================================================
PAWN_FORWARD = {
    0: NORTH,  # WHITE
    1: SOUTH,  # BLACK
}

PAWN_DOUBLE_RANK = {
    0: 1,  # rank 2
    1: 6,  # rank 7
}


# =========================================================
# Utilities
# =========================================================
def bitboard_to_str(bb: int) -> str:
    """
    Renderiza bitboard como grade 8x8.

    Exemplo visual:

    8  . . . . . . . .
    7  . . . . . . . .
    6  . . . . . . . .
    5  . . . X . . . .
    4  . . . X . . . .
    3  . . . . . . . .
    2  . . . . . . . .
    1  . . . . . . . .
       a b c d e f g h
    """
    output = []
    for rank_idx in range(7, -1, -1):
        row = []
        base = rank_idx << 3
        for file_idx in range(8):
            sqi = base + file_idx
            row.append("1" if (bb >> sqi) & 1 else ".")
        output.append("".join(row))
    return "\n".join(output)


def square_index(coord: str) -> int:
    """
    Exemplo: "d4" -> índice inteiro do bitboard
    """
    file = ord(coord[0].lower()) - ord("a")
    rank = int(coord[1]) - 1
    return (rank << 3) | file


CASTLE_WHITE_K = 1 << 0
CASTLE_WHITE_Q = 1 << 1
CASTLE_BLACK_K = 1 << 2
CASTLE_BLACK_Q = 1 << 3

CASTLING_ALL = (
    CASTLE_WHITE_K |
    CASTLE_WHITE_Q |
    CASTLE_BLACK_K |
    CASTLE_BLACK_Q
)

# =========================================================
# Public API
# =========================================================
__all__ = [
    "bit",
    "sq",
    "FILES_MASKS",
    "RANKS_MASKS",
    "CENTER_4_MASK",
    "EXTENDED_CENTER",
    "DIAGONAL_A1H8",
    "ANTI_DIAGONAL_H1A8",
    "NORTH",
    "SOUTH",
    "EAST",
    "WEST",
    "NORTH_EAST",
    "NORTH_WEST",
    "SOUTH_EAST",
    "SOUTH_WEST",
    "PIECE_TYPES",
    "COLOR_COUNT",
    "PIECE_COUNT",
    "MOVE_TYPE_COUNT",
    "SQUARE_TO_FILE",
    "SQUARE_TO_RANK",
    "SQUARE_BB",
    "NOT_FILE_A",
    "NOT_FILE_H",
    "NOT_FILE_AB",
    "NOT_FILE_GH",
    "PAWN_FORWARD",
    "PAWN_DOUBLE_RANK",
    "bitboard_to_str",
    "U64",
    "FILE_A",
    "FILE_H",
    "RANK_1",
    "RANK_8",
    "square_index",
    "CASTLE_WHITE_K",
    "CASTLE_WHITE_Q",
    "CASTLE_BLACK_K",
    "CASTLE_BLACK_Q",
]
