# core/search/alphabeta.py
from __future__ import annotations
from typing import Optional, Tuple, List
import time
from core.search.repetition import RepetitionTable
from core.search.draw import is_insufficient_material, is_fifty_move_rule


from core.moves.legal_movegen import generate_legal_moves
from core.hash.zobrist import Zobrist
from core.search.tt import TranspositionTable, TTEntry, EXACT, LOWERBOUND, UPPERBOUND

# Simple material values (centipawns)
MATERIAL = {
    0: 100,   # PAWN
    1: 320,   # KNIGHT
    2: 330,   # BISHOP
    3: 500,   # ROOK
    4: 900,   # QUEEN
    5: 20000, # KING (large)
}

MATE_SCORE = 1000000
CHECKMATE_PLY_ADJUST = 1000  # small adjustment to prefer faster mate


def evaluate_material(board) -> int:
    """Very fast material-only evaluation. Positive = White advantage."""
    score = 0
    # piece_index mapping: color * 6 + piece
    for color in (0, 1):
        sign = 1 if color == 0 else -1
        for p in range(6):
            bb = board.bitboards[color][p]
            if bb:
                cnt = bb.bit_count()
                score += sign * (MATERIAL[p] * cnt)
    return score


def quiescence(board, alpha: int, beta: int) -> int:
    """Simple quiescence search considering only captures."""
    stand_pat = evaluate_material(board)
    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat

    # generate captures only
    moves = [m for m in generate_legal_moves(board) if getattr(m, "is_capture", False)]
    # Simple capture ordering: none -> as-is
    for mv in moves:
        board.make_move(mv)
        score = -quiescence(board, -beta, -alpha)
        board.unmake_move()

        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha


def _tt_probe(tt: Optional[TranspositionTable], key: int, depth: int, alpha: int, beta: int) -> Optional[int]:
    if tt is None:
        return None
    entry = tt.probe(key)
    if entry is None:
        return None
    if entry.depth >= depth:
        val = entry.value
        if entry.flag == EXACT:
            return val
        if entry.flag == LOWERBOUND and val >= beta:
            return val
        if entry.flag == UPPERBOUND and val <= alpha:
            return val
    return None


def _tt_store(tt: Optional[TranspositionTable], key: int, depth: int, flag: int, value: int, best_move) -> None:
    if tt is None:
        return
    tt.store(key, depth, flag, value, best_move)


def negamax(board, depth: int, alpha: int, beta: int,
            tt: Optional[TranspositionTable],
            repetition_table,
            ply: int = 0) -> int:
    """
    Negamax with alpha-beta, TT integration, quiescence and repetition detection.
    Returns score in centipawns (positive = white advantage).
    """


    # ============================
    # DRAW CONDITIONS
    # ============================

    if is_fifty_move_rule(board):
        return 0

    if is_insufficient_material(board):
        return 0

    if repetition_table.is_threefold(board.zobrist_key):
        return 0

    key = board.zobrist_key

    # ============================
    # TRANSPOSITION TABLE
    # ============================
    tt_val = _tt_probe(tt, key, depth, alpha, beta)
    if tt_val is not None:
        return tt_val

    # ============================
    # QUIESCENCE
    # ============================
    if depth <= 0:
        return quiescence(board, alpha, beta)

    legal_moves = list(generate_legal_moves(board))

    if not legal_moves:
        if board.is_in_check(board.side_to_move):
            return -MATE_SCORE + ply * CHECKMATE_PLY_ADJUST
        else:
            return 0

    best_value = -10**9
    best_move = None
    orig_alpha = alpha

    # ============================
    # TT MOVE ORDERING
    # ============================
    if tt is not None:
        entry = tt.probe(key)
        if entry is not None and entry.best_move is not None:
            for i, mv in enumerate(legal_moves):
                if mv == entry.best_move:
                    legal_moves.insert(0, legal_moves.pop(i))
                    break

    # ============================
    # SEARCH LOOP
    # ============================
    for mv in legal_moves:

        board.make_move(mv)

        # >>> PUSH ZOBRIST AFTER MOVE <<<
        repetition_table.push(board.zobrist_key)

        score = -negamax(
            board,
            depth - 1,
            -beta,
            -alpha,
            tt,
            repetition_table,
            ply + 1
        )

        # >>> POP ZOBRIST BEFORE UNMAKE <<<
        repetition_table.pop()
        board.unmake_move()

        if score > best_value:
            best_value = score
            best_move = mv

        if best_value > alpha:
            alpha = best_value

        if alpha >= beta:
            break

    # ============================
    # STORE IN TT
    # ============================
    flag = EXACT
    if best_value <= orig_alpha:
        flag = UPPERBOUND
    elif best_value >= beta:
        flag = LOWERBOUND

    _tt_store(tt, key, depth, flag, best_value, best_move)

    return best_value


def search_root(board, max_depth: int,
                time_limit: Optional[float] = None,
                tt: Optional[TranspositionTable] = None) -> Tuple[Optional[object], int]:
    """
    Iterative deepening root driver.
    Returns (best_move, best_score).
    """

    repetition_table = RepetitionTable()
    repetition_table.push(board.zobrist_key)

    if tt is not None:
        tt.new_search()

    start = time.time()
    best_move = None
    best_score = -10**9

    for depth in range(1, max_depth + 1):

        if time_limit is not None and (time.time() - start) > time_limit:
            break

        score = negamax(
            board,
            depth,
            -MATE_SCORE,
            MATE_SCORE,
            tt,
            repetition_table,
            ply=0
        )

        entry = tt.probe(board.zobrist_key) if tt is not None else None
        if entry is not None and entry.best_move is not None:
            best_move = entry.best_move
            best_score = score
            continue

        # Fallback manual root search (caso TT falhe)
        best_mv = None
        best_val = -10**9

        for mv in generate_legal_moves(board):

            board.make_move(mv)

            # push repetição após o move
            repetition_table.push(board.zobrist_key)

            val = -negamax(
                board,
                depth - 1,   # <<< aqui estava errado: era depth
                -MATE_SCORE,
                MATE_SCORE,
                tt,
                repetition_table,
                ply=1
            )

            repetition_table.pop()
            board.unmake_move()

            if val > best_val:
                best_val = val
                best_mv = mv

        best_move = best_mv
        best_score = best_val

    return best_move, best_score
