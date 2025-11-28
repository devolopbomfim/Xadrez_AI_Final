# tools/gui_pygame.py
from __future__ import annotations

import os
import sys
import pygame

from core.board.board import Board
from core.moves.legal_movegen import generate_legal_moves
from utils.enums import Color, PieceType, GameResult
from core.game_status import get_game_status

# IA real
from core.search.alphabeta import search_root
from core.search.tt import TranspositionTable


# ================== CONFIG ==================

WINDOW_SIZE = 640
SQ_SIZE = WINDOW_SIZE // 8
FPS = 60

LIGHT = (240, 217, 181)
DARK  = (181, 136, 99)
HIGHLIGHT = (0, 200, 0)
TARGET = (0, 120, 255)
TEXT_COLOR = (0, 0, 0)

BASE_DIR = os.path.dirname(__file__)
ASSETS_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "assets"))

AI_COLOR = Color.BLACK
AI_DEPTH = 2          # mais leve
AI_TIME_LIMIT = 0.3   # 300ms por lance


# ================== ASSETS ==================

PIECE_FILES = {
    (Color.WHITE, PieceType.PAWN):   "w_pawn.png",
    (Color.WHITE, PieceType.KNIGHT): "w_knight.png",
    (Color.WHITE, PieceType.BISHOP): "w_bishop.png",
    (Color.WHITE, PieceType.ROOK):   "w_rook.png",
    (Color.WHITE, PieceType.QUEEN):  "w_queen.png",
    (Color.WHITE, PieceType.KING):   "w_king.png",

    (Color.BLACK, PieceType.PAWN):   "b_pawn.png",
    (Color.BLACK, PieceType.KNIGHT): "b_knight.png",
    (Color.BLACK, PieceType.BISHOP): "b_bishop.png",
    (Color.BLACK, PieceType.ROOK):   "b_rook.png",
    (Color.BLACK, PieceType.QUEEN):  "b_queen.png",
    (Color.BLACK, PieceType.KING):   "b_king.png",
}

PIECE_IMAGES = {}


# ================== LOAD IMAGES ==================

def load_images():
    for key, filename in PIECE_FILES.items():
        path = os.path.join(ASSETS_DIR, filename)

        if not os.path.exists(path):
            raise FileNotFoundError(f"Imagem não encontrada: {path}")

        img = pygame.image.load(path).convert_alpha()
        img = pygame.transform.smoothscale(img, (SQ_SIZE, SQ_SIZE))
        PIECE_IMAGES[key] = img


# ================== GAME STATUS ==================

def check_game_result(board: Board) -> GameResult:
    return get_game_status(board)


# ================== DRAW ==================

def draw_board(screen, board, selected_square=None, legal_targets=None):
    colors = (LIGHT, DARK)

    for rank in range(8):
        for file in range(8):
            square = rank * 8 + file
            x = file * SQ_SIZE
            y = (7 - rank) * SQ_SIZE

            color = colors[(rank + file) % 2]
            pygame.draw.rect(screen, color, (x, y, SQ_SIZE, SQ_SIZE))

            piece = board.get_piece_at(square)
            if piece:
                screen.blit(PIECE_IMAGES[piece], (x, y))

    if selected_square is not None:
        file = selected_square % 8
        rank = selected_square // 8

        x = file * SQ_SIZE
        y = (7 - rank) * SQ_SIZE

        pygame.draw.rect(screen, HIGHLIGHT, (x, y, SQ_SIZE, SQ_SIZE), 3)

    if legal_targets:
        for target in legal_targets:
            file = target % 8
            rank = target // 8

            x = file * SQ_SIZE + SQ_SIZE // 2
            y = (7 - rank) * SQ_SIZE + SQ_SIZE // 2

            pygame.draw.circle(screen, TARGET, (x, y), 8)


# ================== ENDGAME OVERLAY ==================

def draw_endgame_text(screen, font, game_result: GameResult):
    if game_result == GameResult.ONGOING:
        return

    if game_result == GameResult.WHITE_WIN:
        text = "Vitória das Brancas"
    elif game_result == GameResult.BLACK_WIN:
        text = "Vitória das Pretas"
    elif game_result == GameResult.DRAW_STALEMATE:
        text = "Empate por afogamento"
    elif game_result == GameResult.DRAW_REPETITION:
        text = "Empate por repetição tripla"
    elif game_result == GameResult.DRAW_FIFTY_MOVE:
        text = "Empate pela regra dos 50 lances"
    elif game_result == GameResult.DRAW_INSUFFICIENT_MATERIAL:
        text = "Empate por material insuficiente"
    else:
        text = "Empate"

    overlay = pygame.Surface((WINDOW_SIZE, WINDOW_SIZE), pygame.SRCALPHA)
    overlay.fill((255, 255, 255, 180))
    screen.blit(overlay, (0, 0))

    surface = font.render(text, True, TEXT_COLOR)
    rect = surface.get_rect(center=(WINDOW_SIZE // 2, WINDOW_SIZE // 2))
    screen.blit(surface, rect)


# ================== MAIN ==================

def main():
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
    pygame.display.set_caption("Xadrez_AI_Final")

    load_images()
    font = pygame.font.SysFont("Arial", 28, bold=True)

    board = Board()
    board.set_startpos()

    tt = TranspositionTable(size_mb=32)

    selected_square = None
    legal_targets = []

    clock = pygame.time.Clock()
    running = True
    game_over = False
    ai_thinking = False

    while running:
        clock.tick(FPS)
        screen.fill((0, 0, 0))

        game_result = check_game_result(board)
        game_over = (game_result != GameResult.ONGOING)

        draw_board(screen, board, selected_square, legal_targets)
        draw_endgame_text(screen, font, game_result)

        # ================== IA ==================
        if not game_over and board.side_to_move == AI_COLOR and not ai_thinking:
            ai_thinking = True

            print("IA pensando...")

            best_move, score = search_root(
                board,
                max_depth=AI_DEPTH,
                time_limit=AI_TIME_LIMIT,
                tt=tt
            )

            if best_move is not None:
                board.make_move(best_move)

            ai_thinking = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            # RESET GLOBAL
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                board = Board()
                board.set_startpos()
                selected_square = None
                legal_targets = []
                game_over = False
                ai_thinking = False
                continue

            # Bloqueia interação se for vez da IA ou game over
            if board.side_to_move == AI_COLOR or game_over:
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_x, mouse_y = pygame.mouse.get_pos()

                file = mouse_x // SQ_SIZE
                rank = 7 - (mouse_y // SQ_SIZE)

                if not (0 <= file <= 7 and 0 <= rank <= 7):
                    continue

                square = rank * 8 + file

                if selected_square is None:
                    piece = board.get_piece_at(square)

                    if piece and piece[0] == board.side_to_move:
                        selected_square = square
                        legal_targets = [
                            mv.to_sq for mv in generate_legal_moves(board)
                            if mv.from_sq == selected_square
                        ]

                else:
                    for mv in generate_legal_moves(board):
                        if mv.from_sq == selected_square and mv.to_sq == square:
                            board.make_move(mv)
                            break

                    selected_square = None
                    legal_targets = []

        pygame.display.flip()

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
