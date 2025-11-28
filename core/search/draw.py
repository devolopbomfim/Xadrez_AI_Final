from utils.enums import PieceType, Color

def is_insufficient_material(board) -> bool:
    """Detecta material insuficiente para mate."""
    # Conta peças
    wp = board.bitboards[int(Color.WHITE)]
    bp = board.bitboards[int(Color.BLACK)]

    white_pieces = sum(bb.bit_count() for bb in wp)
    black_pieces = sum(bb.bit_count() for bb in bp)

    # Só dois reis
    if white_pieces == 1 and black_pieces == 1:
        return True

    # K vs K + minor
    if white_pieces == 1 and black_pieces == 2:
        if bp[int(PieceType.BISHOP)].bit_count() == 1:
            return True
        if bp[int(PieceType.KNIGHT)].bit_count() == 1:
            return True

    if black_pieces == 1 and white_pieces == 2:
        if wp[int(PieceType.BISHOP)].bit_count() == 1:
            return True
        if wp[int(PieceType.KNIGHT)].bit_count() == 1:
            return True

    return False


def is_fifty_move_rule(board) -> bool:
    """50-move rule: 100 plies sem peão/captura."""
    return board.halfmove_clock >= 100
