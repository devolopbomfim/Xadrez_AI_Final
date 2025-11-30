# core/moves/legal_movegen.py
from __future__ import annotations

from core.moves.castling import _gen_castling_moves
from core.moves.movegen import generate_pseudo_legal_moves
from utils.enums import PieceType


def _is_legal_ep(board, move) -> bool:
    """
    Verifica legalidade de en-passant.

    Um en-passant pseudolegal pode ser ilegal caso:
    - a captura remova um peão que protegia o rei
    - o lance exponha o próprio rei à captura

    Lógica:
        - simula make_move
        - consulta board.is_in_check(stm)
        - desfaz com unmake_move

    Retorna:
        True  → en-passant é legal
        False → EP expõe o rei e não pode ser jogado
    """
    stm = board.side_to_move

    board.make_move(move)
    try:
        in_check = board.is_in_check(stm)
    finally:
        board.unmake_move()

    return not in_check


def generate_legal_moves(board):
    """
    Gera todos os movimentos legais para a posição atual.

    Pipeline:
        1. Gera pseudo-legais (sem verificar cheque).
        2. Adiciona roques válidos via _gen_castling_moves.
        3. Filtra:
            - captura de rei (ilegal em Xadrez)
            - en-passant que expõe o rei
            - movimentos que deixam o rei em cheque (make/unmake)

    Retorna:
        list[Move] contendo apenas lances legalmente válidos.
    """

    stm = board.side_to_move

    # ----------------------------------------------------------------------
    # 1. Pseudo-legais
    # ----------------------------------------------------------------------
    pseudo = list(generate_pseudo_legal_moves(board))

    # ----------------------------------------------------------------------
    # 2. Movimentos de roque (sem duplicação)
    # ----------------------------------------------------------------------
    castlings = _gen_castling_moves(board)

    seen = {(m.from_sq, m.to_sq, int(m.piece)) for m in pseudo}
    for c in castlings:
        key = (c.from_sq, c.to_sq, int(c.piece))
        if key not in seen:
            pseudo.append(c)
            seen.add(key)

    # ----------------------------------------------------------------------
    # 3. Filtragem final
    # ----------------------------------------------------------------------
    legal_moves = []

    for move in pseudo:

        # ------------------------------------------------------------------
        # 3.a Bloqueio absoluto: não existe captura de rei no Xadrez
        # ------------------------------------------------------------------
        target = board.mailbox[move.to_sq]
        if target is not None:
            _, target_piece = target
            if target_piece == PieceType.KING:
                continue

        # ------------------------------------------------------------------
        # 3.b Caso especial: En-passant pode expor o rei
        # ------------------------------------------------------------------
        if (
            move.piece == PieceType.PAWN
            and move.is_capture
            and board.en_passant_square is not None
            and move.to_sq == board.en_passant_square
        ):
            if not _is_legal_ep(board, move):
                continue

        # ------------------------------------------------------------------
        # 3.c Teste universal: faz o lance → verifica cheque → desfaz
        # ------------------------------------------------------------------
        board.make_move(move)
        try:
            in_check = board.is_in_check(stm)
        finally:
            board.unmake_move()

        if not in_check:
            legal_moves.append(move)

    return legal_moves
