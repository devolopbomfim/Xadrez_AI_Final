from __future__ import annotations

from typing import List
from utils.constants import bit, pop_lsb
from core.moves.attack_tables import knight_attacks, king_attacks
from core.moves.magic_bitboards import rook_attacks, bishop_attacks
from utils.enums import Color, PieceType
from utils.constants import SQUARE_BB
from core.moves.move import Move


# ============ BIT ITERATOR ============

def _iter_bits(bb):
    while bb:
        lsb = bb & -bb
        yield lsb.bit_length() - 1
        bb ^= lsb

# ============ MAIN GENERATOR ============

def generate_pseudo_legal_moves(board) -> List[Move]:
    stm = board.side_to_move
    enemy = Color.BLACK if stm == Color.WHITE else Color.WHITE

    occ_all = board.all_occupancy
    occ_own = board.occupancy[stm]
    occ_enemy = board.occupancy[enemy]

    moves: List[Move] = []

    # ---- PAWNS ----
    moves.extend(_gen_pawn_moves(board, stm, occ_all, occ_enemy))

    # ---- KNIGHTS ----
    knights = board.bitboards[stm][PieceType.KNIGHT]
    while knights:
        knights, sq = pop_lsb(knights)
        attacks = knight_attacks(sq) & ~occ_own
        moves.extend(_bb_to_moves(board, sq, attacks, PieceType.KNIGHT, occ_enemy))

    # ---- BISHOPS ----
    bishops = board.bitboards[stm][PieceType.BISHOP]
    while bishops:
        bishops, sq = pop_lsb(bishops)
        attacks = bishop_attacks(sq, occ_all) & ~occ_own
        moves.extend(_bb_to_moves(board, sq, attacks, PieceType.BISHOP, occ_enemy))

    # ---- ROOKS ----
    rooks = board.bitboards[stm][PieceType.ROOK]
    while rooks:
        rooks, sq = pop_lsb(rooks)
        attacks = rook_attacks(sq, occ_all) & ~occ_own
        moves.extend(_bb_to_moves(board, sq, attacks, PieceType.ROOK, occ_enemy))

    # ---- QUEENS ----
    queens = board.bitboards[stm][PieceType.QUEEN]
    while queens:
        queens, sq = pop_lsb(queens)
        attacks = (rook_attacks(sq, occ_all) | bishop_attacks(sq, occ_all)) & ~occ_own
        moves.extend(_bb_to_moves(board, sq, attacks, PieceType.QUEEN, occ_enemy))

    # ---- KING ----
    king = board.bitboards[stm][PieceType.KING]
    if king:
        _, sq = pop_lsb(king)

        attacks = king_attacks(sq) & ~occ_own
        moves.extend(_bb_to_moves(board, sq, attacks, PieceType.KING, occ_enemy))

        # NÃO gerar roque aqui (roque gerado separadamente onde for conveniente)

    return moves

# ============ HELPERS ============

def _bb_to_moves(board, from_sq: int, target_bb: int, piece: PieceType, occ_enemy: int) -> List[Move]:
    moves = []

    while target_bb:
        target_bb, to_sq = pop_lsb(target_bb)
        is_capture = bool(bit(to_sq) & occ_enemy)

        moves.append(Move(
            from_sq=from_sq,
            to_sq=to_sq,
            piece=piece,
            is_capture=is_capture
        ))

    return moves

# ============ PAWNS ============

def _gen_pawn_moves(board, stm, occ_all, occ_enemy):
    moves = []

    pawns = board.bitboards[int(stm)][int(PieceType.PAWN)]
    direction = 8 if stm == Color.WHITE else -8
    start_rank = 1 if stm == Color.WHITE else 6
    promo_rank = 7 if stm == Color.WHITE else 0

    ep_sq = board.en_passant_square

    while pawns:
        pawns, from_sq = pop_lsb(pawns)

        file = from_sq & 7
        rank = from_sq >> 3

        # =====================
        # Avanço simples
        # =====================
        forward = from_sq + direction

        if 0 <= forward < 64 and not (occ_all & SQUARE_BB[forward]):

            if (forward >> 3) == promo_rank:
                for promo in (
                    PieceType.QUEEN,
                    PieceType.ROOK,
                    PieceType.BISHOP,
                    PieceType.KNIGHT,
                ):
                    moves.append(Move(from_sq, forward, PieceType.PAWN, False, promo))
            else:
                moves.append(Move(from_sq, forward, PieceType.PAWN))

            # Avanço duplo
            if rank == start_rank:
                double_forward = from_sq + 2 * direction
                if not (occ_all & SQUARE_BB[double_forward]):
                    moves.append(Move(from_sq, double_forward, PieceType.PAWN))

        # =====================
        # Capturas normais
        # =====================
        for df in (-1, 1):
            nf = file + df
            if nf < 0 or nf > 7:
                continue

            target = from_sq + direction + df

            if not (0 <= target < 64):
                continue

            # captura normal
            if occ_enemy & SQUARE_BB[target]:

                if (target >> 3) == promo_rank:
                    for promo in (
                        PieceType.QUEEN,
                        PieceType.ROOK,
                        PieceType.BISHOP,
                        PieceType.KNIGHT,
                    ):
                        moves.append(Move(from_sq, target, PieceType.PAWN, True, promo))
                else:
                    moves.append(Move(from_sq, target, PieceType.PAWN, True))

            # =====================
            # En Passant
            # =====================
            elif ep_sq is not None and target == ep_sq:

                victim_sq = target - 8 if stm == Color.WHITE else target + 8

                if 0 <= victim_sq < 64:
                    victim = board.mailbox[victim_sq]

                    if victim is not None:
                        v_color, v_piece = victim

                        if v_piece == PieceType.PAWN and v_color != stm:
                            moves.append(Move(from_sq, target, PieceType.PAWN, True))

    return moves

# ============ CASTLING ============

from utils.constants import (
    CASTLE_WHITE_K,
    CASTLE_WHITE_Q,
    CASTLE_BLACK_K,
    CASTLE_BLACK_Q,
)

def _gen_castling_moves(board):
    moves = []
    stm = board.side_to_move
    enemy = Color.BLACK if stm == Color.WHITE else Color.WHITE

    king_bb = board.bitboards[int(stm)][int(PieceType.KING)]
    if not king_bb:
        return moves

    king_sq = king_bb.bit_length() - 1

    if stm == Color.WHITE:
        # e1 index = 4
        if board.castling_rights & CASTLE_WHITE_K:
            if not (board.all_occupancy & (SQUARE_BB[5] | SQUARE_BB[6])):
                if not board._is_square_attacked(4, enemy) \
                   and not board._is_square_attacked(5, enemy) \
                   and not board._is_square_attacked(6, enemy):
                    moves.append(Move(4, 6, PieceType.KING))

        if board.castling_rights & CASTLE_WHITE_Q:
            if not (board.all_occupancy & (SQUARE_BB[1] | SQUARE_BB[2] | SQUARE_BB[3])):
                if not board._is_square_attacked(4, enemy) \
                   and not board._is_square_attacked(3, enemy) \
                   and not board._is_square_attacked(2, enemy):
                    moves.append(Move(4, 2, PieceType.KING))

    else:
        # e8 index = 60
        if board.castling_rights & CASTLE_BLACK_K:
            if not (board.all_occupancy & (SQUARE_BB[61] | SQUARE_BB[62])):
                if not board._is_square_attacked(60, enemy) \
                   and not board._is_square_attacked(61, enemy) \
                   and not board._is_square_attacked(62, enemy):
                    moves.append(Move(60, 62, PieceType.KING))

        if board.castling_rights & CASTLE_BLACK_Q:
            if not (board.all_occupancy & (SQUARE_BB[57] | SQUARE_BB[58] | SQUARE_BB[59])):
                if not board._is_square_attacked(60, enemy) \
                   and not board._is_square_attacked(59, enemy) \
                   and not board._is_square_attacked(58, enemy):
                    moves.append(Move(60, 58, PieceType.KING))

    return moves
