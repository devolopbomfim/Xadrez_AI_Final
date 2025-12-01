#!/usr/bin/env python3
"""
TUI GAME MODE COMMANDS - QUICK REFERENCE

Updated: November 30, 2025

The TUI now supports quick game mode selection via numeric commands (1-6).
Each command starts a new game with the specified agent configuration.

==========================================
GAME MODE COMMANDS (NEW)
==========================================

Type in the command bar to start a game:

  1  →  Human vs Human
         Both players manually enter moves

  2  →  Human vs Random
         You play White, Random AI plays Black

  3  →  Human vs Engine
         You play White, Chess Engine plays Black
         (engine depth: 3, time: 1000ms)

  4  →  Random vs Random
         Two random players play each other
         (stress test for move generation)

  5  →  Random vs Engine
         Random player plays White, Engine plays Black

  6  →  Engine vs Engine
         Two engine instances play each other
         (watch the AI play itself!)

==========================================
EXAMPLE USAGE
==========================================

In the TUI command bar:

  > 1          [ENTER]  ← Start Human vs Human
  > 3          [ENTER]  ← Start Human vs Engine (you play White)
  > 6          [ENTER]  ← Start Engine vs Engine (watch AI play)

==========================================
HOW EACH MODE WORKS
==========================================

MODE 1: Human vs Human
  - Both sides controlled by you
  - Enter moves in UCI format: e2e4, e7e5, etc.
  - Promotions: e7e8q, e7e8r, etc.
  - Use "undo" to take back moves

MODE 2: Human vs Random
  - You: White (you move first)
  - AI: Black (random moves)
  - After you move, Black plays randomly
  - Good for testing against weak play

MODE 3: Human vs Engine
  - You: White (you move first)
  - AI: Black (uses chess engine)
  - Engine is depth-3, max 1 second per move
  - Strong opponent for practice

MODE 4: Random vs Random
  - Automatic play between two random players
  - Useful for testing board and move generation
  - Games typically end in 20-40 moves
  - Use "stop" to interrupt

MODE 5: Random vs Engine
  - White: Random AI
  - Black: Chess Engine
  - Useful for evaluating engine strength
  - Engine typically crushes random

MODE 6: Engine vs Engine
  - Both sides use the chess engine
  - Watch AI play itself!
  - Games typically end in 30-60 moves
  - Useful for analyzing engine play
  - Use "stop" to interrupt

==========================================
CONTROL DURING AUTO GAMES (Modes 4-6)
==========================================

While an auto game is running:

  stop    → Stop the current game and return to normal mode
  show    → Update the board display

==========================================
OTHER COMMANDS (EXISTING)
==========================================

  show              - Update board display
  move e2e4         - Enter a move manually
  undo              - Undo the last move
  play <p1> <p2>    - Legacy autoplay (use modes 1-6 instead)
  stop              - Stop autoplay/auto game
  history           - Show game history
  perft <n>         - Calculate perft
  set <fen>         - Load a position
  help              - Show full help
  quit / exit       - Quit the application

==========================================
TIPS
==========================================

✓ Modes 1-3 allow human play. Modes 4-6 are automatic.

✓ Engine in mode 3 is quite strong at depth 3.
  For faster games, try:
    - Depth 2 for blitz
    - Depth 4 for longer games

✓ Engine vs Engine (mode 6) is good for:
    - Testing engine improvements
    - Analyzing chess strategies
    - Teaching yourself the game

✓ Random vs Random (mode 4) is good for:
    - Stress testing move generation
    - Finding bugs in the board
    - Generating random games

✓ Use "history" command after a game to see all moves

✓ Use "set <fen>" to load a specific position before playing

==========================================
IMPLEMENTATION DETAILS
==========================================

- Modes 1-3: Can stop anytime with "stop" or by quitting
- Modes 4-6: Run automatically until game ends or "stop" command
- Each game starts from starting position
- Move history is preserved
- Game termination reasons are shown (checkmate, stalemate, etc.)

==========================================
KEYBOARD SHORTCUTS
==========================================

In the TUI input bar:
  ENTER     - Execute command
  CTRL+C    - Interrupt current operation
  UP/DOWN   - Navigate command history (if supported)

==========================================
TROUBLESHOOTING
==========================================

Q: "Modo inválido. Use 1-6"
A: You typed something other than 1-6. Valid commands are just:
   1, 2, 3, 4, 5, or 6

Q: Game is not responding to moves
A: Make sure you're in a mode that accepts manual moves (1-3)

Q: Auto game is stuck
A: Type "stop" in the command bar to interrupt

Q: Engine is too slow
A: Engine depth is set to 3. For faster games:
   - Edit interface/tui/main.py
   - Change "engine_depth=3" to "engine_depth=2"
   - Save and restart

Q: Where's my previous game?
A: Type "history" to see the last game's moves

==========================================
EXAMPLES OF USE
==========================================

Scenario 1: Play against the engine
  > 3              Start Human vs Engine
  > e2e4           You move (White)
  [Engine thinks...]
  [Engine plays Black's move]
  > e7e5           You move again
  > stop           Quit the game

Scenario 2: Watch two engines play
  > 6              Start Engine vs Engine
  [Engines play automatically]
  [Watch the board update with each move]
  > stop           Stop watching (after 30 seconds)

Scenario 3: Stress test the board
  > 4              Start Random vs Random
  [Random moves play for ~30 moves]
  [Game ends automatically]
  > history        See all moves

Scenario 4: Test your strategy
  > 1              Start Human vs Human
  > e2e4           Play as White
  [Manually type moves for Black too]
  > e7e5
  > g1f3
  > b8c6
  [Alternate between White and Black moves]

==========================================
NOTES
==========================================

- All game modes start from the starting chess position
- The board is automatically reset for each new game
- You can still use "move" command even in auto modes (mode 1-3)
- "Undo" works in manual modes (1-3)
- "Stop" works in all modes to interrupt

For more details, see:
  - GAME_MODE_SELECTOR_README.md (full documentation)
  - QUICK_REFERENCE.md (API reference)
  - examples/ folder (runnable code examples)

"""
print(__doc__)
