#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent

WEB_PARTS = [
    "web/00_shell_before_games.html",
    "web/games/liar_cards.html",
    "web/games/liar_dice.html",
    "web/games/doudizhu.html",
    "web/games/chuanma.html",
    "web/games/draw_guess.html",
    "web/90_shell_after_games.html",
    "web/00_common.js",
    "web/games/liar_cards.js",
    "web/games/liar_dice.js",
    "web/games/doudizhu.js",
    "web/games/chuanma.js",
    "web/games/draw_guess.js",
    "web/90_common.js",
    "web/99_document_end.html"
]
PY_PARTS = [
    "parts/01_draw_constants.pyfrag",
    "parts/games/doudizhu_backend.pyfrag",
    "parts/games/chuanma_backend.pyfrag",
    "parts/20_core_state_room.pyfrag",
    "parts/games/liar_cards_backend.pyfrag",
    "parts/games/liar_dice_backend.pyfrag",
    "parts/games/draw_guess_backend.pyfrag",
    "parts/70_server_common_prefix.pyfrag",
    "parts/games/liar_cards_actions.pyfrag",
    "parts/games/liar_dice_actions.pyfrag",
    "parts/games/doudizhu_actions.pyfrag",
    "parts/games/chuanma_actions.pyfrag",
    "parts/games/draw_guess_actions.pyfrag",
    "parts/99_server_common_suffix.pyfrag"
]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")

def build_html():
    return "".join(read(rel) for rel in WEB_PARTS)

def build_release():
    release = (read("parts/00_header.pyfrag") +
               "HTML_PAGE = " + repr(build_html()) + "\n\n" +
               "".join(read(rel) for rel in PY_PARTS))
    compile(release, "game_hall_lan_v6_2.py", "exec")
    out = ROOT / "dist" / "game_hall_lan_v6_2.py"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(release, encoding="utf-8")
    (out.with_suffix(".txt")).write_text(release, encoding="utf-8")
    print(out)
    return out

if __name__ == "__main__":
    build_release()
