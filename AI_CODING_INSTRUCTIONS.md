# AI Coding Instructions for Xadrez_AI_Final

These guidelines enable AI coding agents to work productively and safely in this repository.

## 1. Big-Picture Architecture

The project is a **chess engine** with a strict, validated **core** and peripheral layers.  
Always preserve the correctness of the core; all other modules must adapt to it.

### Core Principles
- **Core is authoritative**: bitboards, magic bitboards, movegen, make/unmake, Zobrist, game status, repetition, and perft are fully validated (v1.0-core-stable-r1).
- **Perft = ground truth**: any change to moves, rules, board, or castling logic must keep perft identical.
- **Search engine is external**: lives in `/engine/`, does **not** modify core state; interacts only via `Board` API.

### Directory Overview
- `core/`
  - `board/board.py` — board state, make/unmake, zobrist, occupancy, invariants.
  - `moves/` — `move.py`, `movegen.py`, `legal_movegen.py`, magic bitboards, attack tables.
  - `rules/` — draw, repetition, game_status.
  - `perft/` — executable perft correctness oracle.
- `engine/` — minimax/alpha-beta (to be built). Must not reimplement rules.
- `interface/` — cli/gui frontends (rebuilding from scratch).
- `tools/magics/` — magic bitboard generator + autogen output.
- `utils/` — enums, constants, helpers.

## 2. Developer Workflows

### Running Tests

Perft tests and movegen tests must always pass. If a patch breaks any of them, revise logic instead of patching tests.

### Debugging Movegen
- Use `tools/debug/diag.py` (renamed from older debug module).
- Use `Board().divide(depth)` for per-square visualization.
- For castling debugging, inspect `_generate_castles_int()` and legality filtering in `generate_legal_moves_int()`.

### Regenerating Magic Tables
Outputs automatically to `core/moves/magic/magics_autogen.py`.  
Never hand-edit the autogen file.

## 3. Project-Specific Conventions

### Move Encoding
- Integer move encoding only; all helpers derive from this.  
- Castling generated separately (`_generate_castles_int`), never in pseudo-legal generator.

### Make/Unmake
- `make_move_int()` uses **internal stacks**; never receives reversed parameters.
- Order of operations is fixed: capture → main move → castle/promo → revocation of rights → EP update → clocks → Zobrist.

### Legal Movegen
- Pseudo-legal generator must **exclude** castling.
- Legal generator must:
  - test king-in-check,
  - test attacked intermediate squares,
  - verify special rules (EP legality, rook path in castling).

### File Organization Rules
- Only `attack_tables.py` belongs inside `moves/tables`.
- Only magics and autogen belong inside `moves/magic`.
- `move.py`, `movegen.py`, `legal_movegen.py` stay directly in `moves/`.

## 4. Integration Patterns

### Core ↔ Engine
- Engine receives only:
  - `Board` snapshot,
  - `generate_legal_moves_int(board)`,
  - `board.make_move_int(m)` / `board.unmake_last_move()`,
  - evaluation/API functions.
- Engine must remain stateless regarding rules.

### GUI / CLI
- May call core movegen and board operations.  
- Must not mutate board internals beyond public APIs.

## 5. Examples to Follow

### Example: asking for pseudo-legal moves
```python
moves = generate_pseudo_legal_moves_int(board)
```

