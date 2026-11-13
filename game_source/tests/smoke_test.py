#!/usr/bin/env python3
from pathlib import Path
import importlib.util
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
subprocess.run([sys.executable, str(ROOT / "build.py")], check=True)
os.environ["HOME"] = tempfile.mkdtemp(prefix="game_hall_test_")
release = ROOT / "dist" / "game_hall_lan_v6_2.py"
spec = importlib.util.spec_from_file_location("game_hall_v62", release)
game = importlib.util.module_from_spec(spec)
spec.loader.exec_module(game)
assert len(game.WORD_BANK) == 981
assert {x["library"] for x in game.WORD_BANK} == {"items", "animals", "food", "actions", "places", "campus", "fun"}
assert "拖轮顶推" not in {x["word"] for x in game.WORD_BANK}
assert "企鹅卖冰淇淋" in {x["word"] for x in game.WORD_BANK}
game.STATE = game.fresh_state()
game.STATE["mode"] = "dice"
game.STATE["settings"]["onesWild"] = True
game.STATE["players"] = [
    {"id":"a","name":"甲","diceCount":3,"dice":[4,4,1]},
    {"id":"b","name":"乙","diceCount":3,"dice":[4,2,6]},
]
for p in game.STATE["players"]:
    p.update({"ready":True,"connected":True,"lastSeen":game.time.time(),"seatKey":p["id"],"life":3,"hand":[],"score":0,"ddzHand":[],"ddzScore":0,"ddzHintCursor":0,"isBot":False,"cmHand":[],"cmMelds":[],"cmMissing":None,"cmWon":False,"cmScore":0,"cmDrawnId":None,"cmExchange":[]})
d = game.dice_count_detail(4)
assert (d["natural"], d["wild"], d["total"]) == (3,1,4)
game.STATE["hostPlayerId"] = "a"
game.STATE["phase"] = "finished"
payload, code = object.__new__(game.Handler).handle_action(game.STATE["players"][0], "reset", {})
assert code == 200 and payload == {}
assert game.STATE["phase"] == "lobby"
assert all(p["ready"] for p in game.STATE["players"])
h = game.HTML_PAGE
assert h.index('id="ddzPlayBtn"') < h.index('id="ddzPassBtn"') < h.index('id="ddzHintBtn"')
assert "至少 ${b.quantity} 个" in h
assert 'id="endGameBtn"' in h
print("game core smoke test passed")
