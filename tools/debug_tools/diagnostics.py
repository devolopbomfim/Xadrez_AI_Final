# debug_tools/diagnostics.py

from __future__ import annotations

import time

# ---- Ajuste os imports conforme sua estrutura ----
from core.board.board import Board
from core.moves.legal_movegen import generate_legal_moves
from core.perft.perft import perft  # se você já moveu para core/perft/perft.py
from core.rules.game_status import get_game_status
from core.hash.zobrist import Zobrist

from utils.enums import GameResult

Zobrist.init()
sig = Zobrist.signature()

class Diagnostics:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.errors = 0
        self.warnings = 0

    def log(self, msg: str):
        if self.verbose:
            print(msg)

    def error(self, msg: str):
        self.errors += 1
        print(f"[ERRO] {msg}")

    def warn(self, msg: str):
        self.warnings += 1
        print(f"[AVISO] {msg}")

    # ------------------------------
    # Tests
    # ------------------------------

    def test_board_init(self):
        self.log(">> Teste: inicialização do board")
        try:
            board = Board()
            board.set_startpos()
        except Exception as e:
            self.error(f"Falha ao inicializar board: {e}")
            return

        if board.all_occupancy == 0:
            self.error("Board inicial sem peças (all_occupancy == 0)")
        else:
            self.log("Board inicial OK")

        # Teste de coerência básica
        occ = board.occupancy[0] | board.occupancy[1]
        if occ != board.all_occupancy:
            self.error("all_occupancy inconsistente com occupancy por cor")

    def test_movegen_legal(self):
        self.log(">> Teste: geração de movimentos legais")

        board = Board()
        board.set_startpos()

        try:
            moves = list(generate_legal_moves(board))
        except Exception as e:
            self.error(f"Erro ao gerar movimentos: {e}")
            return

        self.log(f"Movimentos iniciais: {len(moves)}")

        if len(moves) == 0:
            self.error("Nenhum movimento legal na posição inicial")
        elif len(moves) < 20:
            self.warn("Movimentos iniciais menos que o esperado (normal ~20)")

    def test_game_status(self):
        self.log(">> Teste: game_status")

        board = Board()
        board.set_startpos()

        status = get_game_status(board)

        if status != GameResult.ONGOING:
            self.error(f"Status inicial incorreto: {status}")
        else:
            self.log("Status inicial OK (ONGOING)")

    def test_zobrist(self):
        self.log(">> Teste: zobrist")

        try:
            Zobrist.init()
        except Exception as e:
            self.warn(f"Falha ao inicializar zobrist: {e}")
            return

        try:
            sig1 = Zobrist.signature()
            sig2 = Zobrist.signature()
        except Exception as e:
            self.error(f"Erro gerando signature: {e}")
            return

        if sig1 != sig2:
            self.error("Zobrist não determinístico")
        else:
            self.log("Zobrist determinístico OK")

        entropy = Zobrist.verify_entropy()
        self.log(f"Entropy Zobrist: {entropy:.6f}")

    def test_perft(self, depth: int = 3):
        self.log(f">> Teste: perft(depth={depth})")

        board = Board()
        board.set_startpos()

        start = time.time()
        try:
            nodes = perft(board, depth)
        except Exception as e:
            self.error(f"Erro no perft: {e}")
            return
        end = time.time()

        self.log(f"Perft({depth}) = {nodes} nodes em {end-start:.3f}s")

        # Valores esperados para startpos
        expected = {1: 20, 2: 400, 3: 8902}

        if depth in expected and nodes != expected[depth]:
            self.warn(
                f"Perft({depth}) fora do esperado: {nodes} (esperado {expected[depth]})"
            )
        else:
            self.log("Perft OK")

    # ------------------------------
    # Runner
    # ------------------------------

    def run_all(self):
        self.log("=== INICIANDO DIAGNÓSTICO ===")

        self.test_board_init()
        self.test_movegen_legal()
        self.test_game_status()
        self.test_zobrist()
        self.test_perft(2)
        self.test_perft(3)
        self.test_perft(4)
        self.test_perft(5)
        self.test_perft(6)

        self.log("\n=== RESUMO ===")
        self.log(f"Erros: {self.errors}")
        self.log(f"Avisos: {self.warnings}")

        if self.errors == 0:
            self.log("Diagnóstico final: OK")
        else:
            self.log("Diagnóstico final: FALHAS DETECTADAS")


# ------------------------------
# Execução direta
# ------------------------------

if __name__ == "__main__":
    diag = Diagnostics()
    diag.run_all()
