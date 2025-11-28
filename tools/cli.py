from __future__ import annotations
import sys
from typing import Optional

from core.game_status import get_game_status
from utils.enums import GameResult


from core.board.board import Board
from core.moves.legal_movegen import generate_legal_moves
from core.moves.move import Move
from core.search.alphabeta import search_root
from core.search.tt import TranspositionTable
from core.game_status import get_game_status
from utils.enums import GameResult

PIECE_SYMBOLS = {
    ("WHITE", "PAWN"):   "♙",
    ("WHITE", "KNIGHT"): "♘",
    ("WHITE", "BISHOP"): "♗",
    ("WHITE", "ROOK"):   "♖",
    ("WHITE", "QUEEN"):  "♕",
    ("WHITE", "KING"):   "♔",
    ("BLACK", "PAWN"):   "♟",
    ("BLACK", "KNIGHT"): "♞",
    ("BLACK", "BISHOP"): "♝",
    ("BLACK", "ROOK"):   "♜",
    ("BLACK", "QUEEN"):  "♛",
    ("BLACK", "KING"):   "♚",
}

def square_to_char(sq):
    """Converte mailbox para caractere exibível."""
    if sq is None:
        return "."
    color, piece = sq
    key = (color.name, piece.name)
    return PIECE_SYMBOLS.get(key, "?")

def print_board(board):
    print("\n  a b c d e f g h")
    print(" +-----------------+")
    for rank in range(7, -1, -1):
        row = []
        for file in range(8):
            sq = rank * 8 + file
            piece = board.mailbox[sq]
            row.append(square_to_char(piece))
        print(f"{rank+1}| {' '.join(row)} |")
    print(" +-----------------+")

def find_move_from_uci(board: Board, uci: str) -> Optional[Move]:
    """Converte uma string UCI em um Move válido do gerador legal."""
    uci = uci.strip()

    for mv in generate_legal_moves(board):
        if mv.to_uci() == uci:
            return mv
    return None


def show_game_status(board: Board):
    status = get_game_status(board)

    if status == GameResult.ONGOING:
        return

    print("\n== FIM DE JOGO ==")

    if status == GameResult.WHITE_WIN:
        print("Vitória das Brancas")
    elif status == GameResult.BLACK_WIN:
        print("Vitória das Pretas")
    elif status == GameResult.DRAW_STALEMATE:
        print("Empate por afogamento")
    elif status == GameResult.DRAW_REPETITION:
        print("Empate por repetição tripla")
    elif status == GameResult.DRAW_FIFTY_MOVE:
        print("Empate pela regra dos 50 lances")
    elif status == GameResult.DRAW_INSUFFICIENT_MATERIAL:
        print("Empate por material insuficiente")

    sys.exit(0)


def main():
    print("=== Xadrez_AI_Final - CLI ===")
    print("Digite movimentos em UCI (ex: e2e4, g1f3, e7e8q).")
    print("Digite 'quit' para sair.\n")

    board = Board()
    board.set_startpos()

    tt = TranspositionTable(size_mb=64)

    while True:
        print_board(board)
        show_game_status(board)

        if board.side_to_move.name == "WHITE":
            user_input = input("Seu lance (UCI): ").strip()

            if user_input.lower() in ("quit", "exit"):
                print("Encerrando...")
                break

            move = find_move_from_uci(board, user_input)
            if move is None:
                print("Lance inválido.")
                continue

            board.make_move(move)

        else:
            print("IA pensando...")

            best_move, score = search_root(
                board,
                max_depth=4,
                time_limit=None,
                tt=tt
            )

            if best_move is None:
                print("Nenhum lance encontrado pela IA.")
                break

            print(f"IA jogou: {best_move.to_uci()} | score: {score}")
            board.make_move(best_move)


if __name__ == "__main__":
    main()
