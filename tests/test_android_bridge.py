#!/usr/bin/env python3
"""Host-side lifecycle and port-fallback smoke test for the Android bridge."""

from pathlib import Path
import json
import os
import socket
import sys
import tempfile
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
TEST_HOME = Path(tempfile.mkdtemp(prefix="game_hall_android_test_"))
os.environ["HOME"] = str(TEST_HOME)
sys.path.insert(0, str(ROOT / "app" / "src" / "main" / "python"))

import android_bridge  # noqa: E402

android_bridge.game.STATE_FILE = TEST_HOME / ".game_hall_state_v6_2.json"
android_bridge.game.LEGACY_STATE_FILE = TEST_HOME / ".game_hall_state_v6_1.json"
android_bridge.game.STATE = android_bridge.game.fresh_state()
android_bridge.game.TOKENS = {}
android_bridge.game.ACTION_CACHE.clear()

occupied = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
occupied.bind(("0.0.0.0", 18000))
occupied.listen(1)
try:
    started = json.loads(android_bridge.start_server(18000, 18002))
    assert started["running"] is True
    assert started["port"] == 18001
    with urlopen(f"http://127.0.0.1:{started['port']}/", timeout=3) as response:
        page = response.read().decode("utf-8")
    assert response.status == 200
    assert "局域网游戏厅" in page
    android_bridge.game.STATE["players"] = [{"id": "stale-host", "name": "旧房主"}]
    android_bridge.game.STATE["hostPlayerId"] = "stale-host"
    android_bridge.game.TOKENS["old-token"] = "stale-host"
    stopped = json.loads(android_bridge.stop_server(clear_room=True))
    assert stopped["running"] is False
    assert android_bridge.game.STATE["players"] == []
    assert android_bridge.game.STATE["hostPlayerId"] is None
    assert android_bridge.game.TOKENS == {}
finally:
    occupied.close()
    android_bridge.stop_server()

print("Android bridge smoke test passed")
