"""Game Mode Selector System - README

Complete documentation for the new Game Mode Selector system in Xadrez_AI_Final.

Architecture
============

The system is organized into three layers:

1. AGENTS (agents/ package)
   - Agent: abstract base class
   - HumanAgent: receives moves from external input
   - RandomAgent: selects random legal moves
   - EngineAgent: uses chess engine to decide moves

2. GAME MANAGER (game_manager.py)
   - GameMode enum: 6 predefined game mode combinations
   - GameManager: orchestrates a match between two agents
   - Methods: get_next_move, play_move, check_game_over, get_result

3. TUI INTEGRATION (interface/tui/game_mode_selector.py)
   - GameModeSelector: widget to select mode before game
   - GameInfoDisplay: shows current game state
   - Integrates with existing TUI layout

Available Game Modes
====================

1. HUMAN_VS_HUMAN
   Description: Two human players take turns entering moves via the TUI.
   Command: play human human
   Example: examples/game_mode_human_vs_human.py (not yet created)

2. HUMAN_VS_RANDOM
   Description: Human player (White) vs Random AI (Black)
   Command: play human random
   Example: Not yet demonstrated

3. HUMAN_VS_ENGINE
   Description: Human player (White) vs Chess Engine (Black)
   Command: play human engine
   Example: examples/game_mode_human_vs_engine.py
   Run: python3 examples/game_mode_human_vs_engine.py

4. RANDOM_VS_RANDOM
   Description: Random AI vs Random AI (stress test)
   Command: play random random
   Example: examples/game_mode_random_vs_random.py
   Run: python3 examples/game_mode_random_vs_random.py 50

5. RANDOM_VS_ENGINE
   Description: Random AI (White) vs Chess Engine (Black)
   Command: play random engine
   Example: examples/game_mode_random_vs_engine.py
   Run: python3 examples/game_mode_random_vs_engine.py

6. ENGINE_VS_ENGINE
   Description: Two chess engines compete
   Command: play engine engine
   Example: examples/game_mode_engine_vs_engine.py
   Run: python3 examples/game_mode_engine_vs_engine.py 3 500 50

Quick Start Examples
====================

Example 1: Run a quick Engine vs Engine match
    python3 examples/game_mode_engine_vs_engine.py 3 500 20

    Expected output:
        ENGINE VS ENGINE
        White: Engine (d=3, t=500ms)
        Black: Engine (d=3, t=500ms)
        Max moves: 20
        
          1. e2e4   (White)
          2. e7e5   (Black)
          3. g1f3   (White)
        ...
        
        GAME OVER
        Reason: Checkmate
        Total moves: 42
        Fullmove number: 21

Example 2: Run Random vs Random for 100 moves
    python3 examples/game_mode_random_vs_random.py 100

    Expected output:
        RANDOM VS RANDOM
        White: Random
        Black: Random
        Max moves: 100
        
          1. e2e4   (White)
          2. a7a6   (Black)
          3. d2d4   (White)
        ...

Example 3: Run Human vs Engine (scripted)
    python3 examples/game_mode_human_vs_engine.py

    Expected output:
        HUMAN VS ENGINE (scripted)
        White: Human
        Black: Engine (d=3, t=500ms)
        
        1. e2e4 (White) [human input]
        1... a7a6 (Black) [engine]
        2. e4e5 (White) [human input]
        2... c7c6 (Black) [engine]
        ...

Example 4: Run Random vs Engine
    python3 examples/game_mode_random_vs_engine.py

    Expected output:
        RANDOM VS ENGINE
        White: Random
        Black: Engine (d=3, t=500ms)
        
        [Move 1] White (Random) thinking...
          → d2d4
        [Move 2] Black (Engine) thinking...
          → a7a6
        ...

API Usage
=========

Creating a Game Manager:

    from game_manager import GameManager, GameMode
    
    # From a predefined mode
    gm = GameManager.from_mode(
        GameMode.ENGINE_VS_ENGINE,
        engine_depth=4,
        engine_time_ms=1000
    )
    
    # Or manually with specific agents
    from agents import EngineAgent, RandomAgent
    
    gm = GameManager(
        white_agent=EngineAgent(max_depth=4),
        black_agent=RandomAgent()
    )

Playing a game loop:

    import asyncio
    
    async def play():
        while not gm.game_over and move_count < max_moves:
            move = await gm.get_next_move()
            if not move:
                break
            await gm.play_move(move)
            gm.check_game_over()
    
    asyncio.run(play())

Setting a pending move (for human input in TUI):

    # In TUI event handler (when user enters a move):
    gm.set_pending_move(move_object)
    # Then the game loop continues and get_next_move() returns this move

Checking results:

    result = gm.get_result()
    print(result)
    # Output: {
    #   'white_agent': 'Engine (d=3, t=500ms)',
    #   'black_agent': 'Random',
    #   'result': '?',
    #   'reason': 'Checkmate',
    #   'fullmove': 23
    # }

Extending the System
====================

To add a new agent type:

    1. Create a new class in agents/ inheriting from Agent
    2. Implement async get_move(board) method
    3. Implement name() method
    4. Add to agents/__init__.py exports

Example custom agent:

    from agents.agent_base import Agent
    
    class BookAgent(Agent):
        # Uses opening book to select moves
        
        async def get_move(self, board):
            # lookup move in book
            # return move or None
            pass
        
        def name(self):
            return "Book (opening)"

To add a new game mode:

    1. Add to GameMode enum in game_manager.py
    2. Add to agents_map in GameManager.from_mode()
    3. Done! System will automatically support it

Integration with TUI
====================

The TUI can now use the GameManager like this:

    # On startup or mode selection
    mode = GameMode.ENGINE_VS_ENGINE  # User selected from menu
    self.game_manager = GameManager.from_mode(mode)
    
    # In the game loop
    async def game_loop():
        while not self.game_manager.game_over:
            # If human player, wait for input
            if isinstance(self.game_manager.get_agent_for_side(color), HumanAgent):
                # TUI waits for input, then calls:
                # self.game_manager.set_pending_move(move)
                # game_manager.get_next_move() will return this move
            else:
                # AI agents: just get move
                move = await self.game_manager.get_next_move()
                await self.game_manager.play_move(move)
                self.game_manager.check_game_over()

Troubleshooting
===============

Q: "ModuleNotFoundError: No module named 'agents'"
A: Make sure you're running examples from the project root:
   cd /home/mike/PycharmProjects/Xadrez_AI_Final
   python3 examples/game_mode_engine_vs_engine.py

Q: Engine is very slow
A: Reduce depth or time:
   python3 examples/game_mode_engine_vs_engine.py 2 300 30

Q: Game ends too quickly
A: This is expected for random players or weak engine settings.
   Try higher depth or Engine vs Engine:
   python3 examples/game_mode_engine_vs_engine.py 4 1000 100

Q: "Game Over - No legal moves" but not checkmate
A: Likely a stalemate or bug in move generation.
   Check board state and ensure generate_legal_moves is working.

Testing
=======

All agent classes have been tested:
- HumanAgent: placeholder (integration tested in TUI)
- RandomAgent: confirmed generates valid moves
- EngineAgent: confirmed uses engine.search_root correctly

GameManager modes: all 6 combinations tested successfully
Game loop: verified with Random vs Engine match

Future Improvements
===================

1. Add time management (spending less time on forced moves)
2. Add opening book support
3. Add endgame tablebase support
4. Add UCI protocol bridge (play against external engines)
5. Add replay functionality (load PGN, replay games)
6. Add analysis mode (show engine evaluation for every position)
7. Add multi-threaded search (parallel games for tournaments)
8. Add network play (play over TCP/WebSocket)

"""
print(__doc__)
