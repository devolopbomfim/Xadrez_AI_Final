#!/usr/bin/env python3
import py_compile
import sys

files = [
    "interface/tui/main.py",
    "interface/tui/renderer.py", 
    "interface/tui/commands.py",
    "interface/tui/game_history.py",
]

errors = []
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"✓ {f}")
    except py_compile.PyCompileError as e:
        print(f"✗ {f}")
        errors.append(str(e))

if errors:
    print("\nErrors:")
    for e in errors:
        print(e)
    sys.exit(1)
else:
    print("\n✓ All files OK")
