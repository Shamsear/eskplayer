#!/usr/bin/env python
"""Test if database.py can be imported"""

try:
    import database
    print("✓ database.py imported successfully!")
    print(f"✓ TournamentDB class found: {hasattr(database, 'TournamentDB')}")
    print(f"✓ init_db function found: {hasattr(database, 'init_db')}")
    print(f"✓ get_db_connection function found: {hasattr(database, 'get_db_connection')}")
except SyntaxError as e:
    print(f"✗ SyntaxError: {e}")
    print(f"  File: {e.filename}")
    print(f"  Line: {e.lineno}")
    print(f"  Text: {e.text}")
except Exception as e:
    print(f"✗ Error: {e}")
