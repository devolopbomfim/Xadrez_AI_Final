mkdir -p utils core/hash core/board core/moves core/rules core/io tests

touch utils/__init__.py utils/enums.py utils/constants.py
touch core/__init__.py
touch core/hash/__init__.py core/hash/zobrist.py
touch core/board/__init__.py core/board/board.py
touch core/moves/__init__.py core/moves/attack_tables.py core/moves/move_encoding.py core/moves/move_generator.py
touch core/rules/__init__.py core/rules/rules.py
touch core/io/__init__.py core/io/fen.py
touch tests/test_enums.py tests/test_constants.py tests/test_attack_tables.py tests/test_zobrist.py tests/test_board.py tests/test_fen.py tests/test_move_encoding.py tests/test_move_generator.py tests/test_rules.py
