from core.board.board import Board
from core.search.alphabeta import search_root
from core.search.tt import TranspositionTable

# posição inicial
board = Board()

tt = TranspositionTable(size_mb=8)

best_move, score = search_root(board, max_depth=3, tt=tt)

print("Best move:", best_move)
print("Score:", score)

