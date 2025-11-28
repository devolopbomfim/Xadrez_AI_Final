from __future__ import annotations

import copy
import os
import sys
import threading
import traceback
from typing import Optional, Dict, Tuple, List

import pygame

from core.board.board import Board
from core.moves.legal_movegen import generate_legal_moves
from utils.enums import Color, PieceType, GameResult
from core.game_status import get_game_status
from core.search.alphabeta import search_root
from core.search.tt import TranspositionTable

# ================== CONFIG ==================

WINDOW_SIZE = 640
SQ_SIZE = WINDOW_SIZE // 8
FPS = 30

LIGHT = (240, 217, 181)
DARK = (181, 136, 99)
HIGHLIGHT = (0, 200, 0)
TARGET = (0, 120, 255)
TEXT_COLOR = (0, 0, 0)
OVERLAY_COLOR = (255, 255, 255, 180)

BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "assets"))

AI_PLAYS = Color.BLACK
MAX_DEPTH = 1
TT_SIZE_MB = 32

# ================== ASSETS ==================

PIECE_FILES = {
    (Color.WHITE, PieceType.KING):   "w_king.png",
    (Color.WHITE, PieceType.QUEEN):  "w_queen.png",
    (Color.WHITE, PieceType.ROOK):   "w_rook.png",
    (Color.WHITE, PieceType.BISHOP): "w_bishop.png",
    (Color.WHITE, PieceType.KNIGHT): "w_knight.png",
    (Color.WHITE, PieceType.PAWN):   "w_pawn.png",

    (Color.BLACK, PieceType.KING):   "b_king.png",
    (Color.BLACK, PieceType.QUEEN):  "b_queen.png",
    (Color.BLACK, PieceType.ROOK):   "b_rook.png",
    (Color.BLACK, PieceType.BISHOP): "b_bishop.png",
    (Color.BLACK, PieceType.KNIGHT): "b_knight.png",
    (Color.BLACK, PieceType.PAWN):   "b_pawn.png",
}


PIECE_IMAGES: Dict[Tuple[Color, PieceType], pygame.Surface] = {}
DEBUG_GUI = True

# ================== UTILITIES ==================
def _log_debug(msg: str) -> None:
    if DEBUG_GUI:
        print("[GUI DEBUG]", msg)

def _asset_path(name: str) -> str:
    return os.path.join(ASSETS_DIR, name)


def load_images() -> None:
    """
    Carrega e cacheia todas as imagens de peças.
    Deve ser chamado após pygame.init() e após inicializar display/font se necessário.
    """
    if not pygame.get_init():
        raise RuntimeError("pygame não inicializado — chame pygame.init() antes de load_images()")

    PIECE_IMAGES.clear()

    for key, filename in PIECE_FILES.items():
        path = _asset_path(filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Imagem não encontrada: {path}")

        try:
            img = pygame.image.load(path).convert_alpha()
            img = pygame.transform.smoothscale(img, (SQ_SIZE, SQ_SIZE))
            PIECE_IMAGES[key] = img
        except pygame.error as e:
            raise RuntimeError(f"Erro ao carregar imagem {filename}: {e}")


def get_piece_key_from_board(board: Board, square: int) -> Optional[Tuple[Color, PieceType]]:
    """
    Robust lookup da peça no square.
    Aceita vários formatos que board.get_piece_at() pode retornar:
      - (Color, PieceType)
      - (PieceType, Color)
      - objeto com .color/.piece_type ou .piece_type/.color
      - inteiro/enum (PieceType) -> neste caso tenta inferir color via mailbox/bitboards
      - None
    Retorna (Color, PieceType) ou None.
    """
    # 1) se houver mailbox (mais direto e explícito)
    mailbox = getattr(board, "mailbox", None)
    if mailbox is not None:
        try:
            entry = mailbox[square]
            if entry is None:
                return None
            # entry possivelmente (color, piece) ou objeto
            if isinstance(entry, tuple) and len(entry) == 2:
                a, b = entry
                # detectar qual é color / piece
                if isinstance(a, Color):
                    return (a, b)  # type: ignore[return-value]
                if isinstance(b, Color):
                    return (b, a)  # type: ignore[return-value]
            if hasattr(entry, "color") and hasattr(entry, "piece_type"):
                return (entry.color, entry.piece_type)  # type: ignore[return-value]
        except Exception:
            pass

    # 2) tentar usar API pública get_piece_at()
    try:
        piece = board.get_piece_at(square)
    except Exception:
        piece = None

    if piece is None:
        return None

    # já (Color, PieceType)
    if isinstance(piece, tuple) and len(piece) == 2:
        a, b = piece
        if isinstance(a, Color):
            return (a, b)  # type: ignore[return-value]
        if isinstance(b, Color):
            return (b, a)  # type: ignore[return-value]

    # objeto com atributos
    if hasattr(piece, "color") and hasattr(piece, "piece_type"):
        return (piece.color, piece.piece_type)  # type: ignore[return-value]

    # se for apenas PieceType (enum/int), inferir cor consultando bitboards/mailbox
    if isinstance(piece, (int, PieceType)):
        # procurar bit em bitboards para descobrir cor
        try:
            # bitboard-first API esperada: board.bitboards[color][piece_type]
            for col in (Color.WHITE, Color.BLACK):
                bb = board.bitboards[col][piece]  # type: ignore[index]
                if bb != 0:
                    return (col, piece)  # type: ignore[return-value]
        except Exception:
            pass

        # fallback: tentar mailbox scan
        if mailbox is not None:
            entry = mailbox[square]
            if isinstance(entry, tuple) and len(entry) == 2:
                a, b = entry
                if isinstance(a, Color):
                    return (a, b)  # type: ignore[return-value]

    # não foi possível reconhecer
    _log_debug(f"get_piece_key_from_board: formato desconhecido em square={square}, value={piece!r}")
    return None

# ================== DRAW HELPERS ==================


def build_board_surface(board: Board, selected_square: Optional[int], legal_targets: List[int]) -> pygame.Surface:
    """
    Gera uma superfície contendo o tabuleiro e as peças.
    É relativamente barato e permite aplicar dirty-rect logic no loop principal.
    """
    surf = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE))
    colors = (LIGHT, DARK)

    for rank in range(8):
        for file in range(8):
            square = rank * 8 + file
            x = file * SQ_SIZE
            y = (7 - rank) * SQ_SIZE
            color = colors[(rank + file) % 2]
            pygame.draw.rect(surf, color, (x, y, SQ_SIZE, SQ_SIZE))

            key = get_piece_key_from_board(board, square)
            if key is not None and key in PIECE_IMAGES:
                surf.blit(PIECE_IMAGES[key], (x, y))

    # seleção sobreposta (não preenchida para manter peça visível)
    if selected_square is not None:
        file = selected_square % 8
        rank = selected_square // 8
        x = file * SQ_SIZE
        y = (7 - rank) * SQ_SIZE
        pygame.draw.rect(surf, HIGHLIGHT, (x, y, SQ_SIZE, SQ_SIZE), 3)

    # alvos legais
    for target in legal_targets:
        file = target % 8
        rank = target // 8
        x = file * SQ_SIZE + SQ_SIZE // 2
        y = (7 - rank) * SQ_SIZE + SQ_SIZE // 2
        pygame.draw.circle(surf, TARGET, (x, y), max(6, SQ_SIZE // 12))

    return surf


def draw_endgame_overlay(screen: pygame.Surface, font: pygame.font.Font, game_result: GameResult) -> None:
    text_map = {
        GameResult.WHITE_WIN: "Vitória das Brancas",
        GameResult.BLACK_WIN: "Vitória das Pretas",
        GameResult.DRAW_STALEMATE: "Empate por afogamento",
        GameResult.DRAW_REPETITION: "Empate por repetição tripla",
        GameResult.DRAW_FIFTY_MOVE: "Empate pela regra dos 50 lances",
        GameResult.DRAW_INSUFFICIENT_MATERIAL: "Empate por material insuficiente",
    }
    text = text_map.get(game_result)
    if text is None:
        return

    overlay = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
    overlay.fill(OVERLAY_COLOR)
    screen.blit(overlay, (0, 0))

    surface = font.render(text, True, TEXT_COLOR)
    rect = surface.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2))
    screen.blit(surface, rect)


def square_from_mouse(mouse_pos: Tuple[int, int]) -> Optional[int]:
    mouse_x, mouse_y = mouse_pos
    file = mouse_x // SQ_SIZE
    rank = 7 - (mouse_y // SQ_SIZE)
    if 0 <= file <= 7 and 0 <= rank <= 7:
        return rank * 8 + file
    return None


# ================== ZOBRIST SAFE SETUP ==================


def setup_board_zobrist(board_snapshot: Board) -> None:
    """Tenta configurar zobrist_key no snapshot — não falha em caso de erro."""
    try:
        from core.hash import zobrist as zobrist_mod  # lazy import
        if hasattr(zobrist_mod, "compute_zobrist"):
            board_snapshot.zobrist_key = zobrist_mod.compute_zobrist(board_snapshot)
        elif hasattr(zobrist_mod, "signature"):
            board_snapshot.zobrist_key = zobrist_mod.signature(board_snapshot)
    except Exception:
        # não falhar por motivos de IA; manter valor existente ou 0
        board_snapshot.zobrist_key = getattr(board_snapshot, "zobrist_key", 0)


# ================== AI WORKER ==================


class AIWorker:
    """Thread-safe worker para executar search_root em background."""

    def __init__(self, tt: TranspositionTable):
        self.tt = tt
        self.thread: Optional[threading.Thread] = None
        self._thinking = False
        self.best_move: Optional[object] = None
        self._lock = threading.RLock()
        self._stop_event = threading.Event()

    def _make_snapshot(self, board: Board) -> Board:
        # 1) deepcopy
        try:
            return copy.deepcopy(board)
        except Exception:
            pass

        # 2) fen-like
        try:
            if hasattr(board, "to_fen") and hasattr(board.__class__, "from_fen"):
                fen = board.to_fen()
                return board.__class__.from_fen(fen)
            if hasattr(board, "fen") and hasattr(board.__class__, "from_fen"):
                fen = board.fen()
                return board.__class__.from_fen(fen)
        except Exception:
            pass

        # 3) fallback para board.copy()
        try:
            snap = board.copy()
            # aviso não-letal — console para debug
            print("[AIWorker] Aviso: fallback board.copy() usado para snapshot (pode compartilhar referências).")
            return snap
        except Exception:
            raise RuntimeError("Não foi possível gerar snapshot estável do board para a IA")

    def start(self, board: Board) -> None:
        """Inicia thread caso não haja uma ativa."""
        with self._lock:
            if self._thinking:
                return

            try:
                board_snapshot = self._make_snapshot(board)
            except Exception as e:
                print("[AIWorker] Erro ao criar snapshot para IA:", e)
                traceback.print_exc()
                return

            self._stop_event.clear()
            self._thinking = True
            self.best_move = None
            self.thread = threading.Thread(target=self._worker, args=(board_snapshot,), daemon=True)
            self.thread.start()

    def _worker(self, board_snapshot: Board) -> None:
        try:
            setup_board_zobrist(board_snapshot)
            best_move, _ = search_root(board_snapshot, max_depth=MAX_DEPTH, tt=self.tt)
            with self._lock:
                self.best_move = best_move
        except Exception as e:
            print(f"[AIWorker] Erro na IA: {repr(e)}")
            traceback.print_exc()
            with self._lock:
                self.best_move = None
        finally:
            with self._lock:
                self._thinking = False

    def is_ready(self) -> bool:
        with self._lock:
            return (not self._thinking) and (self.best_move is not None)

    @property
    def thinking(self) -> bool:
        with self._lock:
            return self._thinking

    def reset(self, join_timeout: float = 0.5) -> None:
        """Reseta e tenta juntar thread (não bloqueante por padrão)."""
        with self._lock:
            self._stop_event.set()
            thread = self.thread
            self.thread = None
            self._thinking = False
            self.best_move = None

        if thread is not None and thread.is_alive():
            try:
                thread.join(join_timeout)
            except Exception:
                pass

    def join(self, timeout: Optional[float] = None) -> None:
        """Join na thread se existir."""
        thread = None
        with self._lock:
            thread = self.thread
        if thread is not None:
            thread.join(timeout)


# ================== GAME STATE ==================


class GameState:
    """Gerencia estado do jogo e caching de superfície para dirty-rect rendering simples."""

    def __init__(self):
        self.board = Board()
        self.board.set_startpos()
        self.selected_square: Optional[int] = None
        self.legal_targets: List[int] = []
        self._board_surface: Optional[pygame.Surface] = None
        self._dirty = True

    def reset(self) -> None:
        self.board = Board()
        self.board.set_startpos()
        self.selected_square = None
        self.legal_targets = []
        self._dirty = True
        self._board_surface = None

    def mark_dirty(self) -> None:
        self._dirty = True

    def try_move(self, to_square: int) -> bool:
        if self.selected_square is None:
            return False

        for mv in generate_legal_moves(self.board):
            if mv.from_sq == self.selected_square and mv.to_sq == to_square:
                self.board.make_move(mv)
                self.clear_selection()
                self._dirty = True
                return True

        self.clear_selection()
        return False

    def clear_selection(self) -> None:
        self.selected_square = None
        self.legal_targets = []
        self._dirty = True

    def get_board_surface(self) -> pygame.Surface:
        """Retorna (e gera se dirty) a superfície com o tabuleiro desenhado."""
        if self._dirty or self._board_surface is None:
            self._board_surface = build_board_surface(self.board, self.selected_square, self.legal_targets)
            self._dirty = False
        return self._board_surface

    def select_piece(self, square: int) -> None:
        """Seleciona uma peça no quadrado (resiliente a diferentes representações)."""
        piece_key = get_piece_key_from_board(self.board, square)
        if piece_key is None:
            _log_debug(f"select_piece: nenhuma peça em square={square}")
            self.clear_selection()
            return

        piece_color, piece_type = piece_key
        if piece_color != self.board.side_to_move:
            _log_debug(f"select_piece: tentativa de selecionar peça adversária em {square} (color={piece_color}, stm={self.board.side_to_move})")
            self.clear_selection()
            return

        self.selected_square = square
        # gerar alvos legais apenas para essa peça (gera legal_movegen do estado atual)
        try:
            self.legal_targets = [mv.to_sq for mv in generate_legal_moves(self.board) if mv.from_sq == square]
        except Exception as e:
            _log_debug(f"select_piece: erro ao gerar legal targets: {e}")
            self.legal_targets = []

        self._dirty = True
        _log_debug(f"select_piece: peça selecionada em {square} (type={piece_type}), targets={self.legal_targets}")
# ================== MAIN LOOP ==================


def main() -> None:
    pygame.init()
    try:
        flags = pygame.HWSURFACE | pygame.DOUBLEBUF
        screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE), flags)
        pygame.display.set_caption("Xadrez_AI_Final")

        # carregar assets (após inicializar pygame)
        load_images()

        # fonte robusta com fallback
        try:
            font = pygame.font.SysFont("Arial", 28, bold=True)
        except Exception:
            font = pygame.font.Font(None, 28)

        game = GameState()
        tt = TranspositionTable(size_mb=TT_SIZE_MB)
        ai = AIWorker(tt)

        clock = pygame.time.Clock()
        running = True

        while running:
            # cap FPS
            dt_ms = clock.tick(FPS)

            # eventos (processar todos)
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                    break

                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    game.reset()
                    ai.reset()
                    continue

                # mouse
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # aceitamos input apenas quando não for turno da IA e jogo não acabado
                    game_result = get_game_status(game.board)
                    game_over = game_result != GameResult.ONGOING
                    can_input = not (game_over or ai.thinking or game.board.side_to_move == AI_PLAYS)
                    if not can_input:
                        continue

                    if event.button == 1:
                        square = square_from_mouse(event.pos)
                        if square is None:
                            continue

                        if game.selected_square is None:
                            game.select_piece(square)
                        else:
                            moved = game.try_move(square)
                            # se o jogador moveu e agora é turno da IA iremos iniciar IA no loop fora dos eventos
                            if moved:
                                # mover feito: força atualização de superfície
                                game.mark_dirty()

            # lógica por frame — desenhar e IA
            screen.fill((0, 0, 0))

            # Atualiza surface do tabuleiro (usa caching se nada mudou)
            board_surf = game.get_board_surface()
            screen.blit(board_surf, (0, 0))

            # Overlay de fim de jogo
            game_result = get_game_status(game.board)
            game_over = game_result != GameResult.ONGOING
            if game_over:
                draw_endgame_overlay(screen, font, game_result)

            # IA: iniciar quando for seu turno e não estiver pensando
            if (not game_over) and (game.board.side_to_move == AI_PLAYS):
                #with threading.RLock():
                    if not ai.thinking and ai.best_move is None:
                        # passar board (AIWorker fará snapshot seguro internamente)
                        ai.start(game.board)
                    elif ai.is_ready():
                        # aplicar movimento prontamente no main thread
                        if ai.best_move is not None:
                            try:
                                game.board.make_move(ai.best_move)
                                game.mark_dirty()
                            except Exception as e:
                                print("[Main] Erro aplicando movimento da IA:", e)
                            finally:
                                ai.reset()

            # flip display
            pygame.display.flip()

        # cleanup
        ai.reset(join_timeout=0.2)
        pygame.quit()

    except FileNotFoundError as e:
        print(f"Erro crítico: {e}")
        try:
            pygame.quit()
        finally:
            sys.exit(1)
    except Exception as e:
        print(f"Erro inesperado: {e}")
        traceback.print_exc()
        try:
            pygame.quit()
        finally:
            sys.exit(1)



if __name__ == "__main__":
    main()
