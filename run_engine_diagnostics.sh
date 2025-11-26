#!/bin/bash

echo "========================================="
echo "   Xadrez_AI_Final — Diagnóstico Geral"
echo "========================================="

# ==================== ENUMS ====================
echo
echo "===> Testando utils/enums.py"

python - << 'EOF'
from utils.enums import Color, PieceType, MoveType, GameResult

print("Enums detectados:")
print("Color:", list(Color))
print("PieceType:", list(PieceType))
print("MoveType:", list(MoveType))
print("GameResult:", list(GameResult))

assert Color.WHITE.value == 0
assert Color.BLACK.value == 1
assert len(Color) == 2

assert PieceType.PAWN.value == 0
assert PieceType.KING.value == 5
assert len(PieceType) == 6

assert MoveType.QUIET.value == 0
assert len(MoveType) == 6

assert GameResult.ONGOING.value == 0

print("✅ enums.py OK")
EOF

# ==================== CONSTANTS ====================
echo
echo "===> Testando utils/constants.py"

python - << 'EOF'
from utils.constants import *

print("Testando constantes principais...")

assert isinstance(U64, int)

assert SQUARE_BB[0] == (1 << 0)
assert SQUARE_BB[63] == (1 << 63)

assert COLOR_COUNT == 2
assert MOVE_TYPE_COUNT == 6

assert isinstance(CENTER_4_MASK, int)
assert CENTER_4_MASK != 0

# Direções não são obrigatórias no seu design
# Apenas validamos estrutura global
assert len(FILES_MASKS) == 8
assert len(RANKS_MASKS) == 8

print("✅ constants.py OK")
EOF

# ==================== ZOBRIST ====================
echo
echo "===> Testando core/hash/zobrist.py"

python - << 'EOF'
from core.hash.zobrist import Zobrist

Zobrist.reset()
Zobrist.init(seed=12345)

sig1 = Zobrist.signature()

Zobrist.reset()
Zobrist.init(seed=12345)
sig2 = Zobrist.signature()

Zobrist.reset()
Zobrist.init(seed=99999)
sig3 = Zobrist.signature()

assert sig1 == sig2, "Seed igual deveria gerar mesmas chaves"
assert sig1 != sig3, "Seeds diferentes devem gerar chaves diferentes"

# Teste de reversibilidade XOR
h = 0
h = Zobrist.xor_side(h)
h = Zobrist.xor_side(h)
assert h == 0

print("✅ zobrist.py OK")
EOF

# ================= MAGIC BITBOARDS =================
echo
echo "===> Testando core/moves/magic_bitboards.py"

python - << 'EOF'
import core.moves.magic_bitboards as mb

mb.init()

assert len(mb.ROOK_GOOD_MAGICS) == 64
assert len(mb.BISHOP_GOOD_MAGICS) == 64
assert len(mb.ROOK_ATTACK_OFFSETS) == 64
assert len(mb.BISHOP_ATTACK_OFFSETS) == 64

atk = mb.rook_attacks(0, 0)
assert isinstance(atk, int)

print("✅ magic_bitboards.py OK")
EOF

# ================= ATTACK TABLES =================
echo
echo "===> Testando core/moves/attack_tables.py"

python - << 'EOF'
from core.moves.attack_tables import init, KNIGHT_ATTACKS, KING_ATTACKS, PAWN_ATTACKS
from utils.enums import Color

init()

assert KNIGHT_ATTACKS[0].bit_count() == 2
assert KING_ATTACKS[0].bit_count() == 3

assert PAWN_ATTACKS[Color.WHITE][8].bit_count() == 1
assert PAWN_ATTACKS[Color.BLACK][48].bit_count() == 1

print("✅ attack_tables.py OK")
EOF

# ==================== BOARD ====================
echo
echo "===> Testando core/board/board.py"

python - << 'EOF'
from core.board.board import Board

b = Board()

# Checagem estrutural, não funcional (board é mecânico)
assert hasattr(b, "bitboards")
assert hasattr(b, "occupancy")
assert hasattr(b, "all_occupancy")

assert isinstance(b.occupancy[0], int)
assert isinstance(b.occupancy[1], int)
assert isinstance(b.all_occupancy, int)

print("✅ board.py OK")
EOF

echo
echo "========================================="
echo "✅ DIAGNÓSTICO COMPLETO FINALIZADO"
echo "========================================="
