# core/moves/move.py
from __future__ import annotations

from dataclasses import dataclass
from utils.enums import PieceType

@dataclass(frozen=True)
class Move:
    from_sq: int
    to_sq: int
    piece: PieceType
    is_capture: bool = False
    promotion: PieceType | None = None

    def to_uci(self):

        files = "abcdefgh"
        ranks = "12345678"

        f_file = files[self.from_sq & 7]
        f_rank = ranks[self.from_sq >> 3]
        t_file = files[self.to_sq & 7]
        t_rank = ranks[self.to_sq >> 3]

        if self.promotion:
            promo = {
                PieceType.QUEEN: "q",
                PieceType.ROOK: "r",
                PieceType.BISHOP: "b",
                PieceType.KNIGHT: "n",
            }[self.promotion]
            return f"{f_file}{f_rank}{t_file}{t_rank}{promo}"

        return f"{f_file}{f_rank}{t_file}{t_rank}"
