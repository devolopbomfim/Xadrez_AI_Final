from core.board.board import Board
from core.search.alphabeta import search_root
from core.search.tt import TranspositionTable


def test_search_returns_legal_move():
    board = Board()
    tt = TranspositionTable(size_mb=4)

    move, score = search_root(board, max_depth=2, tt=tt)

    assert move is not None, "Search returned None move"
    assert isinstance(score, int), "Score is not integer"

    # Verifica se o move é legal
    legal_moves = list(board.__class__.from_fen(board.to_fen())._gen_legal_moves()
                       if hasattr(board, "_gen_legal_moves")
                       else [])

    # fallback: gerar novamente
    from core.moves.legal_movegen import generate_legal_moves
    legal_moves = list(generate_legal_moves(board))

    assert move in legal_moves, "Returned move is not legal"


def test_tt_usage():
    board = Board()
    tt = TranspositionTable(size_mb=4)

    # Primeira busca
    move1, score1 = search_root(board, max_depth=2, tt=tt)
    # Segunda busca — deve reaproveitar TT
    move2, score2 = search_root(board, max_depth=2, tt=tt)

    assert move1 is not None
    assert move2 is not None
    assert isinstance(score1, int)
    assert isinstance(score2, int)

def test_tt_key_consistency():
    board = Board()
    tt = TranspositionTable(size_mb=4)

    key_before = board.zobrist_key
    move, _ = search_root(board, 2, tt=tt)
    key_after = board.zobrist_key

    assert key_before == key_after, "Zobrist key changed after search"
