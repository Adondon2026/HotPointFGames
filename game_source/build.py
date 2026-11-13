#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def build_html():
    markup = "".join([
        read("web/00_shell_before_games.html"),
        read("web/games/liar_cards.html"),
        read("web/games/liar_dice.html"),
        read("web/games/doudizhu.html"),
        read("web/games/chuanma.html"),
        read("web/games/draw_guess.html"),
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
    ])
    return markup.replace("</style>", read("web/lite.css") + "\n" + read("web/table_games.css") + "\n</style>", 1) + script + read("web/99_document_end.html")

def build_release():
    html = build_html()
    chunks = [
        read("parts/00_header.pyfrag"),
        "HTML_PAGE = " + repr(html) + "\n\n",
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
        read("parts/99_server_common_suffix.pyfrag").replace('if __name__ == "__main__":', read("parts/95_lite.pyfrag") + "\n" + read("parts/96_bots.pyfrag") + "\n" + read("parts/97_table_events.pyfrag") + '\nif __name__ == "__main__":', 1),
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
