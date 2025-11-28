# core/moves/legal_movegen.py
from __future__ import annotations

from utils.enums import Color, PieceType
from utils.constants import U64, NOT_FILE_A, NOT_FILE_H, SQUARE_BB
from core.moves.tables.attack_tables import knight_attacks, king_attacks
from core.moves.magic.magic_bitboards import rook_attacks, bishop_attacks
from core.moves.movegen import generate_pseudo_legal_moves, _gen_castling_moves

BIT_ONE = 1

def _bit(sq: int) -> int:
    return (BIT_ONE << sq) & U64

def _opposite(color: Color) -> Color:
    return Color.BLACK if color == Color.WHITE else Color.WHITE

def _find_king_square(board, color: Color) -> int:
    for sq, cell in enumerate(board.mailbox):
        if cell is not None:
            c, p = cell
            if c == color and p == PieceType.KING:
                return sq
    raise RuntimeError("Rei não encontrado no tabuleiro.")

def _is_square_attacked(board, sq: int, by_color: Color) -> bool:
    """
    Função utilitária (API livre) que delega ao método de instância se presente,
    ou em último caso replica a lógica mínima usando as tabelas de ataque.
    Mantém compatibilidade com chamadas existentes em generate_legal_moves.
    """
    # se a instância implementa o método membro, use-o
    if hasattr(board, "_is_square_attacked") and callable(getattr(board, "_is_square_attacked")):
        return board._is_square_attacked(sq, by_color)

    # fallback (não esperado se Board já tem o método)
    occ = board.all_occupancy
    target = SQUARE_BB[sq]
    ci = int(by_color)

    # pawn attacks
    # reusar a mesma lógica do _is_legal_ep para pawns
    enemy_pawns = board.bitboards[ci][int(PieceType.PAWN)]
    if by_color == Color.WHITE:
        pawn_attacks = ((enemy_pawns << 7) & NOT_FILE_H) | ((enemy_pawns << 9) & NOT_FILE_A)
    else:
        pawn_attacks = ((enemy_pawns >> 7) & NOT_FILE_A) | ((enemy_pawns >> 9) & NOT_FILE_H)
    if pawn_attacks & target:
        return True

    # knight
    knights = board.bitboards[ci][int(PieceType.KNIGHT)]
    if knights & knight_attacks(sq):
        return True

    # bishops + queens (diagonals)
    diag_attackers = board.bitboards[ci][int(PieceType.BISHOP)] | board.bitboards[ci][int(PieceType.QUEEN)]
    if diag_attackers and (bishop_attacks(sq, occ) & diag_attackers):
        return True

    # rooks + queens (straights)
    straight_attackers = board.bitboards[ci][int(PieceType.ROOK)] | board.bitboards[ci][int(PieceType.QUEEN)]
    if straight_attackers and (rook_attacks(sq, occ) & straight_attackers):
        return True

    # king adjacency
    king = board.bitboards[ci][int(PieceType.KING)]
    if king and (king_attacks(sq) & king):
        return True

    return False

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
