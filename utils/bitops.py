def bit(sq: int) -> int:
    return 1 << sq


def pop_lsb(bb: int):
    lsb = bb & -bb
    sq = (lsb.bit_length() - 1)
    bb &= bb - 1
    return bb, sq

