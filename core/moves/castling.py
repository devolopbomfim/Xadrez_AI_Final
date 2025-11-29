from __future__ import annotations

from typing import List
from utils.constants import SQUARE_BB
from utils.enums import Color, PieceType
from core.moves.move import Move
from utils.constants import (
    CASTLE_WHITE_K, CASTLE_WHITE_Q, CASTLE_BLACK_K, CASTLE_BLACK_Q
)


def _gen_castling_moves(board) -> List[Move]:
    """
    Castling generation extracted from movegen.py.
    API identical: returns list[Move] representing king moves for castling.
    """
    moves: List[Move] = []
    stm = board.side_to_move
    enemy = Color.BLACK if stm == Color.WHITE else Color.WHITE

    king_bb = board.bitboards[int(stm)][int(PieceType.KING)]
    if not king_bb:
        return moves

    if stm == Color.WHITE:
        # king-side
        if board.castling_rights & CASTLE_WHITE_K:
            if not (board.all_occupancy & (SQUARE_BB[5] | SQUARE_BB[6])):
                if not board._is_square_attacked(4, enemy) and not board._is_square_attacked(5, enemy) and not board._is_square_attacked(6, enemy):
                    moves.append(Move(4, 6, PieceType.KING))
        # queen-side
        if board.castling_rights & CASTLE_WHITE_Q:
            if not (board.all_occupancy & (SQUARE_BB[1] | SQUARE_BB[2] | SQUARE_BB[3])):
                if not board._is_square_attacked(4, enemy) and not board._is_square_attacked(3, enemy) and not board._is_square_attacked(2, enemy):
                    moves.append(Move(4, 2, PieceType.KING))
    else:
        # black king-side
        if board.castling_rights & CASTLE_BLACK_K:
            if not (board.all_occupancy & (SQUARE_BB[61] | SQUARE_BB[62])):
                if not board._is_square_attacked(60, enemy) and not board._is_square_attacked(61, enemy) and not board._is_square_attacked(62, enemy):
                    moves.append(Move(60, 62, PieceType.KING))
        # black queen-side
        if board.castling_rights & CASTLE_BLACK_Q:
            if not (board.all_occupancy & (SQUARE_BB[57] | SQUARE_BB[58] | SQUARE_BB[59])):
                if not board._is_square_attacked(60, enemy) and not board._is_square_attacked(59, enemy) and not board._is_square_attacked(58, enemy):
                    moves.append(Move(60, 58, PieceType.KING))

    return moves
