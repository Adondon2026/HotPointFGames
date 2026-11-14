#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# Single source for Web game version; regenerated with every online game update.
GAME_DISPLAY_VERSION = "ZMZ v0.20.1"

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8").replace("@@ZMZ_GAME_VERSION@@", GAME_DISPLAY_VERSION)

def build_html():
    markup = "".join([
        read("web/00_shell_before_games.html"),
        read("web/games/liar_cards.html"),
        read("web/games/liar_dice.html"),
        read("web/games/doudizhu.html"),
        read("web/games/chuanma.html"),
        read("web/games/draw_guess.html"),
        read("web/games/army.html"),
        read("web/90_shell_after_games.html"),
    ])
    script = "".join([
        read("web/00_common.js"),
        read("web/games/liar_cards.js"),
        read("web/games/liar_dice.js"),
        read("web/games/doudizhu.js"),
        read("web/games/chuanma.js"),
        read("web/games/draw_guess.js"),
        read("web/table_games.js"),
        read("web/90_common.js"),
        read("web/lite.js"),
        read("web/feedback.js"),
        read("web/games/army.js"),
    ])
    return markup.replace("</style>", read("web/lite.css") + "\n" + read("web/table_games.css") + "\n" + read("web/feedback.css") + "\n" + read("web/games/army.css") + "\n</style>", 1) + script + read("web/99_document_end.html")

def army_engine():
    # Embed original modules in isolated namespaces; release remains one Python file.
    chunks = ["import types as _army_types\n"]
    for name in ("topology", "rules", "game_state"):
        src = read("parts/army/" + name + ".py").replace("import topology\n", "").replace("import rules\n", "")
        chunks.append(f"_army_{name} = _army_types.ModuleType('army_{name}')\n")
        if name != "topology": chunks.append(f"_army_{name}.__dict__['topology'] = _army_topology\n")
        if name == "game_state": chunks.append("_army_game_state.__dict__['rules'] = _army_rules\n")
        chunks.append(f"exec(compile({src!r}, 'army/{name}.py', 'exec'), _army_{name}.__dict__)\n")
    return "".join(chunks)

def build_release():
    html = build_html()
    chunks = [
        read("parts/00_header.pyfrag"),
        "HTML_PAGE = " + repr(html) + "\n\n",
        "HUB_PAGE = " + repr(read("web/hub.html")) + "\n\n",
        "SIEGE_PAGE = " + repr(read("web/games/siege.html").replace("<script>", "<script>\n" + read("web/games/siege_audio.js") + "\n", 1)) + "\n\n",
        read("parts/01_draw_constants.pyfrag"),
        read("parts/games/doudizhu_backend.pyfrag"),
        read("parts/games/chuanma_backend.pyfrag"),
        read("parts/20_core_state_room.pyfrag"),
        read("parts/games/liar_cards_backend.pyfrag"),
        read("parts/games/liar_dice_backend.pyfrag"),
        read("parts/games/draw_guess_backend.pyfrag"),
        read("parts/70_server_common_prefix.pyfrag"),
        read("parts/games/liar_cards_actions.pyfrag"),
        read("parts/games/liar_dice_actions.pyfrag"),
        read("parts/games/doudizhu_actions.pyfrag"),
        read("parts/games/chuanma_actions.pyfrag"),
        read("parts/games/draw_guess_actions.pyfrag"),
        read("parts/99_server_common_suffix.pyfrag").replace('if __name__ == "__main__":', read("parts/95_lite.pyfrag") + "\n" + read("parts/96_bots.pyfrag") + "\n" + read("parts/97_table_events.pyfrag") + "\n" + army_engine() + "\n" + read("parts/98_army.pyfrag") + "\n" + read("parts/98_siege.pyfrag") + "\n" + read("parts/99_rooms.pyfrag") + '\nif __name__ == "__main__":', 1),
    ]
    release = "".join(chunks)
    compile(release, "game_hall_lan_v6_2.py", "exec")
    out = ROOT / "dist" / "game_hall_lan_v6_2.py"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(release, encoding="utf-8")
    (ROOT / "dist" / "game_hall_lan_v6_2.txt").write_text(release, encoding="utf-8")
    print(out)

if __name__ == "__main__":
    build_release()
