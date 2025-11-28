from utils.enums import GameResult, Color
from core.moves.legal_movegen import generate_legal_moves
from core.search.draw import is_insufficient_material, is_fifty_move_rule

def get_game_status(board, repetition_table=None) -> GameResult:
    moves = list(generate_legal_moves(board))

    if not moves:
        if board.is_in_check(board.side_to_move):
            return GameResult.WHITE_WIN if board.side_to_move == Color.BLACK else GameResult.BLACK_WIN
        else:
            return GameResult.DRAW_STALEMATE

    # ✅ ORDEM CORRETA
    if repetition_table and repetition_table.is_threefold(board.zobrist_key):
        return GameResult.DRAW_REPETITION

    if is_fifty_move_rule(board):
        return GameResult.DRAW_FIFTY_MOVE

    if is_insufficient_material(board):
        return GameResult.DRAW_INSUFFICIENT_MATERIAL

    return GameResult.ONGOING
