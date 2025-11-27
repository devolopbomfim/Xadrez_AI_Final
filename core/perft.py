from core.moves.legal_movegen import generate_legal_moves


def _move_to_key(move):
    for attr in ("uci", "to_uci", "to_uci_string"):
        fn = getattr(move, attr, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                pass
    return str(move)


def perft(board, depth: int) -> int:
    """Perft padrão (legal)."""
    if depth == 0:
        return 1

    nodes = 0
    for move in generate_legal_moves(board):
        board.make_move(move)
        nodes += perft(board, depth - 1)
        board.unmake_move()
    return nodes


def perft_divide(board, depth: int):
    """
    Perft divide:
    - imprime cada lance raiz + número de nós gerados por ele
    - ordena os lances por representação para facilitar comparação
    """

    if depth < 1:
        raise ValueError("perft_divide requer depth >= 1")

    total = 0
    results = []

    # gerar lista fixa primeiro (evita surpresas se algo alterar o generator)
    moves = list(generate_legal_moves(board))

    for move in moves:
        board.make_move(move)
        count = perft(board, depth - 1)
        board.unmake_move()
        total += count

        # nome do lance
        if hasattr(move, "uci"):
            mv_str = move.uci()
        else:
            mv_str = str(move)

        results.append((mv_str, count))

    # ordenar para saída estável
    results.sort(key=lambda x: x[0])

    print(f"\n=== PERFT DIVIDE (depth {depth}) ===")
    for mv, count in results:
        print(f"{mv}: {count}")

    print("\nTOTAL:", total)
    return total
