# core/search/tt.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Any

# TT entry flags
EXACT = 0
LOWERBOUND = 1
UPPERBOUND = 2


@dataclass
class TTEntry:
    key: int = 0
    depth: int = -1
    flag: int = EXACT
    value: int = 0
    best_move: Optional[Any] = None
    age: int = 0


class TranspositionTable:
    """
    Simple fixed-size transposition table with single-slot replacement policy
    biased by depth and age.

    Usage:
        tt = TranspositionTable(size_mb=32)
        entry = tt.probe(key)
        tt.store(key, depth, flag, value, best_move)
    """

    def __init__(self, size_mb: int = 32):
        # compute number of entries as power-of-two
        bytes_per_entry = 32  # rough estimate (fits dataclass fields)
        target_bytes = max(1, size_mb) * 1024 * 1024
        n = max(1, target_bytes // bytes_per_entry)
        # round down to power of two
        size = 1 << (n.bit_length() - 1)
        self._size = size
        self._mask = size - 1
        self._table = [TTEntry() for _ in range(size)]
        self._age = 0  # incremented per search iteration

    def clear(self) -> None:
        self._table = [TTEntry() for _ in range(self._size)]
        self._age = 0

    def new_search(self) -> None:
        """Call at start of a new iterative-deepening root search to age entries."""
        self._age = (self._age + 1) & 0xFF

    def _index(self, key: int) -> int:
        # use lower bits of key for index
        return key & self._mask

    def probe(self, key: int) -> Optional[TTEntry]:
        e = self._table[self._index(key)]
        if e.key == key:
            return e
        return None

    def store(self, key: int, depth: int, flag: int, value: int, best_move: Optional[Any]) -> None:
        idx = self._index(key)
        e = self._table[idx]

        # Replacement policy:
        # - If empty slot, replace
        # - If incoming depth > existing depth, replace
        # - If same depth, prefer newer age
        # - Otherwise keep existing
        replace = False
        if e.key == 0:
            replace = True
        elif depth > e.depth:
            replace = True
        elif (self._age != e.age) and (depth == e.depth):
            replace = True

        if replace:
            self._table[idx] = TTEntry(
                key=key,
                depth=depth,
                flag=flag,
                value=value,
                best_move=best_move,
                age=self._age,
            )
