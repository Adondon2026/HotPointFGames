#!/usr/bin/env python3

from pathlib import Path
import os
import sys
import tempfile
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TEST_HOME = Path(tempfile.mkdtemp(prefix="game_hall_e2e_"))
os.environ["HOME"] = str(TEST_HOME)
os.environ["GAMEHALL_DATA_DIR"] = str(TEST_HOME)
subprocess.run([sys.executable, str(ROOT / "game_source" / "build.py")], check=True)
sys.path.insert(0, str(ROOT / "game_source" / "dist"))

import game_hall_lan_v6_2 as game  # noqa: E402

game.STATE_FILE = TEST_HOME / ".game_hall_state_v6_2.json"
game.LEGACY_STATE_FILE = TEST_HOME / ".game_hall_state_v6_1.json"
game.STATE = game.fresh_state()
game.TOKENS = {}
game.ACTION_CACHE.clear()
game.PORT = 18080
server = game.ReliableThreadingHTTPServer((game.HOST, game.PORT), game.Handler)
try:
    server.serve_forever(poll_interval=0.2)
finally:
    server.server_close()
