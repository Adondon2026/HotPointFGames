"""Keep abandoned naval and docking experiments out of public game selection.

Existing URLs and rooms intentionally remain available for backwards compatibility.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
hub=(ROOT/"web/hub.html").read_text(encoding="utf-8")
lite=(ROOT/"web/lite.js").read_text(encoding="utf-8")
assert 'href="/trial/ship"' not in hub, "Docking demo should not occupy the hall"
assert '单人试航 · 最后一百米' not in hub
assert 'id=\'modeShip\'' not in lite and 'modeShip' not in lite, "Naval battle must not appear in game selector"
assert "Ship:{mode:'ship'" not in lite
assert 'liteGameCount" class="lite-game-count">7<' in lite
assert "siege:'保卫子刊'" in lite, "The original Siege entry must remain"
assert "id='modeSiege'" in lite
print("Main hall: 7 visible games, Siege retained, experimental entries hidden")
