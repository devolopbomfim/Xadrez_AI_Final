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
from typing import Final, Tuple

# =========================================================
# 64-bit mask
# =========================================================
U64: Final[int] = 0xFFFFFFFFFFFFFFFF

# =========================================================
# Helpers básicos
# =========================================================
def bit(square: int) -> int:
    """
    Retorna um bitboard com o bit de `square` ligado.

    Validações:
        - square deve estar em [0, 63]
    """
    if not (0 <= square < 64):
        raise ValueError(f"square fora de intervalo [0..63]: {square!r}")
    return (1 << square) & U64


def sq(file_idx: int, rank_idx: int) -> int:
    """
    Converte (file_idx, rank_idx) -> índice [0..63], A1 = 0.

    Layout:
        rank_idx * 8 + file_idx

    file_idx e rank_idx devem estar em 0..7.
    """
    if not (0 <= file_idx < 8) or not (0 <= rank_idx < 8):
        raise ValueError(f"file_idx/rank_idx fora de intervalo: {(file_idx, rank_idx)!r}")
    return (rank_idx << 3) | file_idx


# =========================================================
# File masks (geradas programaticamente para evitar duplicação)
# =========================================================
_FILE_A: Final[int] = 0x0101010101010101
FILES_MASKS: Final[Tuple[int, ...]] = tuple((_FILE_A << i) & U64 for i in range(8))
FILE_A, FILE_B, FILE_C, FILE_D, FILE_E, FILE_F, FILE_G, FILE_H = FILES_MASKS  # convenient aliases

# =========================================================
# Rank masks (geradas programaticamente)
# =========================================================
_RANK_1: Final[int] = 0x00000000000000FF
RANKS_MASKS: Final[Tuple[int, ...]] = tuple((_RANK_1 << (8 * i)) & U64 for i in range(8))
RANK_1, RANK_2, RANK_3, RANK_4, RANK_5, RANK_6, RANK_7, RANK_8 = RANKS_MASKS  # aliases


# =========================================================
# Center masks
# =========================================================
CENTER_4_MASK: Final[int] = (
    bit(sq(3, 3)) |  # D4
    bit(sq(4, 3)) |  # E4
    bit(sq(3, 4)) |  # D5
    bit(sq(4, 4))    # E5
) & U64

FILES_CDEF: Final[int] = FILE_C | FILE_D | FILE_E | FILE_F
CLASSIC_CENTER: Final[int] = FILES_CDEF & (RANK_3 | RANK_4 | RANK_5 | RANK_6)


# =========================================================
# Diagonals
# =========================================================
DIAGONAL_A1H8: Final[int] = 0x8040201008040201
ANTI_DIAGONAL_H1A8: Final[int] = 0x0102040810204080


# =========================================================
# Directions (square deltas)
# =========================================================
NORTH: Final[int] = 8
SOUTH: Final[int] = -8
EAST: Final[int] = 1
WEST: Final[int] = -1

NORTH_EAST: Final[int] = NORTH + EAST   # 9
NORTH_WEST: Final[int] = NORTH + WEST   # 7
SOUTH_EAST: Final[int] = SOUTH + EAST   # -7
SOUTH_WEST: Final[int] = SOUTH + WEST   # -9


# =========================================================
# Counts (alinhadas à ABI interna)
# =========================================================
PIECE_TYPES: Final[int] = 6       # PAWN..KING
COLOR_COUNT: Final[int] = 2       # WHITE/BLACK
PIECE_COUNT: Final[int] = 12      # 6 * 2
MOVE_TYPE_COUNT: Final[int] = 6   # fixo, ABI com enums.MoveType


# =========================================================
# Square tables
# =========================================================
SQUARE_TO_FILE: Final[Tuple[int, ...]] = tuple(i & 7 for i in range(64))
SQUARE_TO_RANK: Final[Tuple[int, ...]] = tuple(i >> 3 for i in range(64))
SQUARE_BB: Final[Tuple[int, ...]] = tuple(((1 << i) & U64) for i in range(64))


# =========================================================
# Edge masks
# =========================================================
NOT_FILE_A: Final[int] = (~FILE_A) & U64
NOT_FILE_H: Final[int] = (~FILE_H) & U64
NOT_FILE_AB: Final[int] = (~(FILE_A | FILE_B)) & U64
NOT_FILE_GH: Final[int] = (~(FILE_G | FILE_H)) & U64


# =========================================================
# Pawn helpers
# =========================================================
# Mapeamento por cor: 0 = WHITE, 1 = BLACK (coerente com utils/enums.Color)
PAWN_FORWARD: Final[dict[int, int]] = {
    0: NORTH,  # WHITE
    1: SOUTH,  # BLACK
}

PAWN_DOUBLE_RANK: Final[dict[int, int]] = {
    0: 1,  # rank index 1 == rank 2 (WHITE double)
    1: 6,  # rank index 6 == rank 7 (BLACK double)
}


# =========================================================
# Utilities
# =========================================================
def bitboard_to_str(bb: int) -> str:
    """
    Renderiza bitboard como grade 8x8 (string).

    O formato usa '.' para casas vazias e '1' para bits ativos. A primeira
    linha corresponde ao rank 8 e a última ao rank 1, conforme convenção.
    """
    bb &= U64
    rows = []
    for rank_idx in range(7, -1, -1):
        base = rank_idx << 3
        row_chars = []
        for file_idx in range(8):
            sqi = base + file_idx
            row_chars.append("1" if ((bb >> sqi) & 1) else ".")
        rows.append("".join(row_chars))
    # rodapé de arquivos é opcional e deliberadamente omitido aqui para simplicidade
    return "\n".join(rows)


def square_index(coord: str) -> int:
    """
    Converte notação algébrica curta (ex: "d4") para índice [0..63].

    Validações:
      - coord deve ter comprimento 2
      - file entre 'a'..'h', rank entre '1'..'8'
    """
    if not isinstance(coord, str) or len(coord) != 2:
        raise ValueError(f"coord deve ser string de 2 chars, ex 'd4'; recebeu: {coord!r}")
    file_ch, rank_ch = coord[0].lower(), coord[1]
    if file_ch < "a" or file_ch > "h":
        raise ValueError(f"file inválido em coord: {coord!r}")
    if rank_ch < "1" or rank_ch > "8":
        raise ValueError(f"rank inválido em coord: {coord!r}")
    file_idx = ord(file_ch) - ord("a")
    rank_idx = int(rank_ch) - 1
    return (rank_idx << 3) | file_idx


def pop_lsb(bb: int) -> tuple[int, int]:
    """
    Remove o bit menos significativo de um bitboard.

    Retorna:
        (novo_bb, square)
        - novo_bb: bb sem o LSB
        - square: índice [0..63] do bit removido

    Lança ValueError se bb == 0.
    """
    if bb == 0:
        raise ValueError("pop_lsb chamado com bb == 0")
    lsb = bb & -bb
    sq = lsb.bit_length() - 1
    bb = bb & (bb - 1)
    return bb, sq


# =========================================================
# Castling flags
# =========================================================
CASTLE_WHITE_K: Final[int] = 1 << 0
CASTLE_WHITE_Q: Final[int] = 1 << 1
CASTLE_BLACK_K: Final[int] = 1 << 2
CASTLE_BLACK_Q: Final[int] = 1 << 3

CASTLING_ALL: Final[int] = (
    CASTLE_WHITE_K |
    CASTLE_WHITE_Q |
    CASTLE_BLACK_K |
    CASTLE_BLACK_Q
)


# =========================================================
# Public API
# =========================================================
__all__ = [
    "U64",
    "bit",
    "sq",
    "FILES_MASKS",
    "RANKS_MASKS",
    "FILE_A",
    "FILE_H",
    "RANK_1",
    "RANK_8",
    "CENTER_4_MASK",
    "CLASSIC_CENTER",
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
    "square_index",
    "pop_lsb",
    "CASTLE_WHITE_K",
    "CASTLE_WHITE_Q",
    "CASTLE_BLACK_K",
    "CASTLE_BLACK_Q",
    "CASTLING_ALL",
]
