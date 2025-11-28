# scripts/bench_bitops.py
from time import perf_counter
from core.native.bitops import ctz, clz

def py_ctz(bb):
    if bb == 0:
        return -1
    return (bb & -bb).bit_length() - 1

def py_clz(bb):
    if bb == 0:
        return -1
    return bb.bit_length() - 1

N = 10_000_000
bb = 1 << 37

# Python
t0 = perf_counter()
for _ in range(N):
    py_ctz(bb)
    py_clz(bb)
t1 = perf_counter()
print("[PY]   ", t1 - t0)

# C
t0 = perf_counter()
for _ in range(N):
    ctz(bb)
    clz(bb)
t1 = perf_counter()
print("[C]    ", t1 - t0)
