#!/usr/bin/env python3
"""Host-side tests: import, validation, fresh process, port fallback, and room reset."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "app" / "src" / "main" / "python"
sys.path.insert(0, str(PYTHON))

with tempfile.TemporaryDirectory(prefix="gamehall_runner_") as tmp:
    root = Path(tmp)
    os.environ["HOME"] = tmp
    import android_bridge as bridge

    pending = root / bridge.PENDING
    active = root / bridge.ACTIVE
    pending.write_text("not valid Python !!!", encoding="utf-8")
    assert not json.loads(bridge.install_game(tmp))["ok"]
    assert not active.exists()
    shutil.copyfile(PYTHON / (bridge.BUILTIN + ".py"), pending)
    assert json.loads(bridge.install_game(tmp))["ok"]
    assert json.loads(bridge.status())["restartRequired"]
    # The process which installed the update cannot restart using the old module.
    assert not json.loads(bridge.start_server(18000, 18002, tmp))["running"]

    def run(script):
        subprocess.run([sys.executable, "-c", script, tmp], check=True, cwd=PYTHON)

    run("""import android_bridge as b, json, sys, socket
from urllib.request import urlopen
with socket.socket() as occupied:
    occupied.bind(('0.0.0.0',18000)); occupied.listen(1)
    r=json.loads(b.start_server(18000,18002,sys.argv[1]))
    assert r['running'] and r['source']=='imported' and r['port']==18001, r
    with urlopen('http://127.0.0.1:18001/',timeout=3) as p:
        assert '局域网游戏厅' in p.read().decode()
    assert not json.loads(b.restore_builtin(sys.argv[1]))['ok']
    b.game.STATE['players']=[{'id':'stale','name':'旧房主'}]
    b.game.STATE['hostPlayerId']='stale'; b.game.TOKENS['old']='stale'
    assert not json.loads(b.stop_server(True))['running']
    assert b.game.STATE['players']==[] and b.game.TOKENS=={}
""")

    # Syntax-compatible but runtime-broken file must fall back to bundled game.
    active.write_text('raise RuntimeError("test")\nclass Handler: pass\nclass ReliableThreadingHTTPServer: pass\ndef fresh_state(): pass\ndef flush_state(): pass\n', encoding="utf-8")
    run("""import android_bridge as b, json, sys
r=json.loads(b.start_server(18000,18002,sys.argv[1]))
assert r['running'] and r['source']=='builtin' and r['warning'], r
assert not json.loads(b.stop_server(True))['running']
""")
    assert not active.exists() and (root / bridge.FAILED).exists()
    print("Runner import / fallback / lifecycle tests passed")
