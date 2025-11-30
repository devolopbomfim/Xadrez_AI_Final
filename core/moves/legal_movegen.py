# core/moves/legal_movegen.py
from __future__ import annotations

from core.moves.castling import _gen_castling_moves
from utils.enums import Color, PieceType
from core.moves.movegen import generate_pseudo_legal_moves


def _is_legal_ep(board, move) -> bool:
    """
    Verifica se um en-passant é legal.
    Simula o lance (make/unmake) e usa API pública board.is_in_check.
    Retorna True se legal, False se expõe o rei.
    """
    stm = board.side_to_move

    board.make_move(move)
    try:
        # usa API pública (evita warnings)
        in_check = board.is_in_check(stm)
    finally:
        board.unmake_move()

    return not in_check

def generate_legal_moves(board):
    """
    Gera e retorna uma lista de movimentos legais.
    - Filtra movimentos que deixam o rei em cheque
    - Bloqueia explicitamente captura de rei
    - Corrige problemas com generator (retorna lista real)
    """

    stm = board.side_to_move
    enemy = Color.BLACK if stm == Color.WHITE else Color.WHITE

    # 1. Coletar pseudo-legais
    pseudo = list(generate_pseudo_legal_moves(board))

    # 2. Coletar castlings
    try:
        castlings = list(_gen_castling_moves(board))
    except Exception:
        castlings = []

    # Evitar duplicação
    seen = {(m.from_sq, m.to_sq, int(m.piece)) for m in pseudo}
    for c in castlings:
        key = (c.from_sq, c.to_sq, int(c.piece))
        if key not in seen:
            pseudo.append(c)
            seen.add(key)

    legal_moves = []

    # 3. Filtrar movimentos legais
    for move in pseudo:

        # --- BLOQUEIO ABSOLUTO: não permitir captura de rei ---
        target = board.mailbox[move.to_sq]
        if target is not None:
            target_color, target_piece = target
            if target_piece == PieceType.KING:
                continue

        # --- En-passant: verificação especial ---
        if (
            move.piece == PieceType.PAWN
            and move.is_capture
            and board.en_passant_square is not None
            and move.to_sq == board.en_passant_square
        ):
            if not _is_legal_ep(board, move):
                continue

        # --- Teste de legalidade via make/unmake ---
        board.make_move(move)
        try:
            # Verifica se o lado que acabou de mover (stm) ficou em cheque.
            # Usamos API pública para reduzir acoplamento e evitar warnings.
            in_check = board.is_in_check(stm)
        finally:
            board.unmake_move()

        if not in_check:
            legal_moves.append(move)

    return legal_moves
