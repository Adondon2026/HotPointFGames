#!/usr/bin/env python3
"""Release metadata covers the precise bytes to be installed."""
from pathlib import Path
import hashlib
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from game_update_manifest import make_manifest, MAX_BYTES
with tempfile.TemporaryDirectory() as tmp:
    game = Path(tmp) / "game.py"
    game.write_text("x = 42\n", encoding="utf-8")
    m = make_manifest(game, "game-1-1-abcdef0", "abcdef0" + "0" * 33, 123)
    assert m["size"] == len(game.read_bytes())
    assert m["sha256"] == hashlib.sha256(game.read_bytes()).hexdigest()
    assert m["sourceEpoch"] == 123 and m["minHostVersionCode"] == 4
    game.write_text("not valid !!!", encoding="utf-8")
    try:
        make_manifest(game, "x", "x", 0)
    except SyntaxError:
        pass
    else:
        raise AssertionError("invalid Python accepted")
    game.write_bytes(b"#" * (MAX_BYTES + 1))
    try:
        make_manifest(game, "x", "x", 0)
    except ValueError:
        pass
    else:
        raise AssertionError("oversize game accepted")
print("Game update manifest tests passed")
