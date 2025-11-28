# core/rules/game_status.py

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

from utils.enums import GameResult, Color
from core.moves.legal_movegen import generate_legal_moves
from core.rules.draw import is_insufficient_material, is_fifty_move_rule



class GameOverReason(Enum):
    CHECKMATE = auto()
    STALEMATE = auto()
    REPETITION = auto()
    FIFTY_MOVE = auto()
    INSUFFICIENT_MATERIAL = auto()


@dataclass(frozen=True)
class GameStatus:
    is_game_over: bool
    result: GameResult
    reason: Optional[GameOverReason] = None

    def __eq__(self, other):
        from utils.enums import GameResult

        # Compatibilidade temporária com código legado baseado em GameResult
        if isinstance(other, GameResult):
            return self.result == other

        if not isinstance(other, GameStatus):
            return False

        return (
            self.is_game_over == other.is_game_over and
            self.result == other.result and
            self.reason == other.reason
        )

    # --- Convenience properties ---
    @property
    def is_checkmate(self) -> bool:
        return self.reason == GameOverReason.CHECKMATE

    @property
    def is_stalemate(self) -> bool:
        return self.reason == GameOverReason.STALEMATE

    @property
    def is_draw_by_repetition(self) -> bool:
        return self.is_game_over and self.reason == GameOverReason.REPETITION

    @property
    def is_draw_by_fifty_move(self) -> bool:
        return self.is_game_over and self.reason == GameOverReason.FIFTY_MOVE

    @property
    def is_insufficient_material(self) -> bool:
        return self.is_game_over and self.reason == GameOverReason.INSUFFICIENT_MATERIAL

def get_game_status(board, repetition_table=None) -> GameStatus:
    moves = list(generate_legal_moves(board))

    if not moves:
        if board.is_in_check(board.side_to_move):
            return GameStatus(
                is_game_over=True,
                result=GameResult.WHITE_WIN if board.side_to_move == Color.BLACK else GameResult.BLACK_WIN,
                reason=GameOverReason.CHECKMATE
            )
        else:
            return GameStatus(
                is_game_over=True,
                result=GameResult.DRAW_STALEMATE,
                reason=GameOverReason.STALEMATE
            )

    if repetition_table and repetition_table.is_threefold(board.zobrist_key):
        return GameStatus(
            is_game_over=True,
            result=GameResult.DRAW_REPETITION,
            reason=GameOverReason.REPETITION
        )

    if is_fifty_move_rule(board):
        return GameStatus(
            is_game_over=True,
            result=GameResult.DRAW_FIFTY_MOVE,
            reason=GameOverReason.FIFTY_MOVE
        )

    if is_insufficient_material(board):
        return GameStatus(
            is_game_over=True,
            result=GameResult.DRAW_INSUFFICIENT_MATERIAL,
            reason=GameOverReason.INSUFFICIENT_MATERIAL
        )

    return GameStatus(
        is_game_over=False,
        result=GameResult.ONGOING,
        reason=None
    )
