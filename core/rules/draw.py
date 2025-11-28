from utils.enums import PieceType, Color

def is_insufficient_material(board) -> bool:
    wp = board.bitboards[int(Color.WHITE)]
    bp = board.bitboards[int(Color.BLACK)]

    white_counts = [bb.bit_count() for bb in wp]
    black_counts = [bb.bit_count() for bb in bp]

    white_total = sum(white_counts)
    black_total = sum(black_counts)

    # K vs K
    if white_total == 1 and black_total == 1:
        return True

    # K vs K + minor
    if white_total == 1 and black_total == 2:
        if black_counts[int(PieceType.BISHOP)] == 1:
            return True
        if black_counts[int(PieceType.KNIGHT)] == 1:
            return True

    if black_total == 1 and white_total == 2:
        if white_counts[int(PieceType.BISHOP)] == 1:
            return True
        if white_counts[int(PieceType.KNIGHT)] == 1:
            return True

    # K+B vs K+B (mesma cor)
    if white_total == 2 and black_total == 2:
        if white_counts[int(PieceType.BISHOP)] == 1 and black_counts[int(PieceType.BISHOP)] == 1:
            # verificar cor da casa dos bispos
            wb_sq = (wp[int(PieceType.BISHOP)]).bit_length() - 1
            bb_sq = (bp[int(PieceType.BISHOP)]).bit_length() - 1

            wb_color = (wb_sq + (wb_sq // 8)) % 2
            bb_color = (bb_sq + (bb_sq // 8)) % 2

            if wb_color == bb_color:
                return True

    # K+N vs K+N
    if white_total == 2 and black_total == 2:
        if white_counts[int(PieceType.KNIGHT)] == 1 and black_counts[int(PieceType.KNIGHT)] == 1:
            return True

    return False


def is_fifty_move_rule(board) -> bool:
    """50-move rule: 100 plies sem peão/captura."""
    return board.halfmove_clock >= 100
