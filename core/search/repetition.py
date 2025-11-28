# core/search/repetition.py

class RepetitionTable:
    """
    Controle de repetição de posição via zobrist incremental.
    Usa uma pilha + contador por chave.
    """

    __slots__ = ("_count", "_stack")

    def __init__(self):
        self._count = {}   # key (int) -> ocorrências
        self._stack = []   # histórico em ordem

    def push(self, zobrist_key: int):
        self._stack.append(zobrist_key)
        self._count[zobrist_key] = self._count.get(zobrist_key, 0) + 1

    def pop(self):
        key = self._stack.pop()
        cnt = self._count[key] - 1
        if cnt <= 0:
            del self._count[key]
        else:
            self._count[key] = cnt

    def is_threefold(self, zobrist_key: int) -> bool:
        """True se a posição já ocorreu >= 3 vezes."""
        return self._count.get(zobrist_key, 0) >= 3
