#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
局域网游戏厅 v6.2
模式：骗子牌、大话骰、你画我猜、经典斗地主、四川麻将。
单文件、零第三方依赖、热点局域网、断线续座、状态落盘。
"""

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import json
import random
import secrets
import socket
import struct
import threading
import time
import re
from collections import Counter

try:
    import fcntl
except Exception:
    fcntl = None

HOST = "0.0.0.0"
PORT = 8000
STATE_FILE = Path.home() / ".game_hall_state_v6_2.json"
LEGACY_STATE_FILE = Path.home() / ".game_hall_state_v6_1.json"
LOCK = threading.RLock()
ONLINE_TIMEOUT = 30
ZOMBIE_TIMEOUT = 180
ACTION_CACHE_TTL = 180
ACTION_CACHE_LIMIT = 256

HTML_PAGE = '<!doctype html>\n<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no">\n<meta name="theme-color" content="#101116">\n<title>局域网游戏厅</title>\n<style>\n:root{--bg:#0d0e12;--panel:#17191f;--panel2:#20232b;--line:#323640;--text:#f7f4ed;--muted:#a7abb4;--gold:#e4b966;--red:#df7070;--green:#71c797;--blue:#78abe2;--shadow:0 14px 42px rgba(0,0,0,.36)}\n*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}html,body{margin:0;min-height:100%;background:radial-gradient(circle at 50% -10%,#30251d 0,transparent 34%),var(--bg);color:var(--text);font-family:system-ui,-apple-system,"Noto Sans SC","Microsoft YaHei",sans-serif}button,input,select{font:inherit}button{touch-action:manipulation}.app{max-width:760px;margin:auto;padding:12px 14px 104px}.top{height:48px;display:flex;align-items:center;justify-content:space-between}.brand{font-weight:950;letter-spacing:.5px}.top-actions{display:flex;align-items:center;gap:8px}.icon-btn{width:38px;height:38px;padding:0;border-radius:50%;background:transparent;color:var(--muted);border:1px solid var(--line);font-weight:850}.net{width:10px;height:10px;border-radius:50%;background:#5c626d}.net.ok{background:var(--green)}.net.wait{background:var(--gold)}.net.bad{background:var(--red)}.card{background:rgba(23,25,31,.96);border:1px solid rgba(255,255,255,.06);border-radius:20px;padding:15px;margin:11px 0;box-shadow:var(--shadow)}.hidden{display:none!important}.row{display:flex;gap:9px;align-items:center}.grow{flex:1}.title{font-size:18px;font-weight:950}.muted{font-size:13px;color:var(--muted);line-height:1.5}input,select{width:100%;min-height:48px;border-radius:14px;border:1px solid var(--line);background:#101217;color:var(--text);padding:12px;outline:none}input:focus,select:focus{border-color:var(--gold)}button{min-height:46px;border:0;border-radius:14px;padding:11px 15px;background:var(--gold);color:#2b2418;font-weight:900;cursor:pointer}button.secondary{background:var(--panel2);color:var(--text);border:1px solid var(--line)}button.red{background:var(--red);color:#2b0d0d}button.green{background:var(--green);color:#09291a}button.blue{background:var(--blue);color:#10233a}button:disabled{opacity:.38;filter:grayscale(.35)}.full{width:100%}.mode-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:9px}.mode{background:#111319;border:1px solid var(--line);border-radius:17px;padding:12px;min-height:105px;display:flex;flex-direction:column;justify-content:space-between;cursor:pointer}.mode.active{border-color:var(--gold);box-shadow:inset 0 0 0 1px var(--gold)}.mode-emoji{font-size:27px}.mode-name{font-weight:950}.mode-desc{font-size:12px;color:var(--muted)}.players{display:flex;gap:8px;overflow-x:auto;padding:2px 0 3px;scrollbar-width:none}.players::-webkit-scrollbar,.hand::-webkit-scrollbar{display:none}.player{min-width:126px;background:#101217;border:1px solid var(--line);border-radius:15px;padding:10px}.player.me{border-color:var(--gold)}.player.turn{box-shadow:inset 0 0 0 2px var(--green)}.player.out{opacity:.47}.player.offline{opacity:.58;border-style:dashed}.player.self-edit{cursor:pointer}.seat-kick{margin-top:8px;width:100%;min-height:32px;padding:5px 8px;border-radius:10px;font-size:12px;background:transparent;color:var(--red);border:1px solid rgba(223,112,112,.45)}.pname{font-weight:850;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.pmeta{font-size:12px;color:var(--muted);margin-top:5px}.stage{text-align:center;padding:13px 8px 7px}.stage-kicker{font-size:12px;color:var(--muted)}.stage-main{font-size:30px;font-weight:950;color:var(--gold);margin-top:5px}.stage-sub{font-size:13px;color:var(--muted);margin-top:3px}.notice{background:#111319;border:1px solid var(--line);border-radius:15px;padding:11px 12px;font-size:13px;color:var(--muted);text-align:center}.hand{display:flex;gap:8px;overflow-x:auto;padding:9px 3px 12px;min-height:112px;scrollbar-width:none}.play-card{width:66px;height:94px;border-radius:11px;background:linear-gradient(150deg,#fbf8ef,#d9d3c4);color:#151515;flex:none;padding:7px;display:flex;flex-direction:column;justify-content:space-between;box-shadow:0 5px 0 #999284,0 10px 20px rgba(0,0,0,.35);font-weight:950;user-select:none}.play-card .big{font-size:29px;text-align:center}.play-card.selected{transform:translateY(-10px);outline:3px solid var(--gold)}.play-card.joker{background:linear-gradient(150deg,#342e43,#1f1b28);color:#f1d38e;box-shadow:0 5px 0 #0b0a0e,0 10px 20px rgba(0,0,0,.35)}.dice-reveal-list{display:grid;gap:7px;margin:12px 0}.dice-reveal-row{display:flex;align-items:center;gap:10px;background:#101217;border:1px solid var(--line);border-radius:13px;padding:9px 10px}.dice-reveal-name{width:82px;font-size:13px;font-weight:850;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.dice-reveal-dice{display:flex;gap:5px;flex-wrap:wrap}.dice-reveal-dice span{font-size:29px;line-height:1}\n.dice{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;padding:13px 0}.die{width:58px;height:58px;border-radius:14px;background:linear-gradient(145deg,#fff,#d9deea);color:#161b26;display:grid;place-items:center;font-size:35px;box-shadow:0 5px 0 #9299aa,0 9px 18px rgba(0,0,0,.3)}.actions{display:grid;grid-template-columns:1fr 1fr;gap:9px;margin-top:11px}.actions.three{grid-template-columns:1fr 1fr 1fr}.faces{display:grid;grid-template-columns:repeat(6,1fr);gap:6px;margin-top:9px}.face{padding:3px 0;background:#101217;color:var(--text);border:1px solid var(--line);font-size:25px}.face.active{background:var(--blue);color:#0c2238;border-color:transparent}.counter{display:grid;grid-template-columns:48px 1fr 48px;gap:8px;align-items:center}.counter strong{text-align:center;font-size:25px}.counter button{padding:0}.reveal{border-top:1px solid var(--line);margin-top:14px;padding-top:14px}.reveal-cards{display:flex;gap:7px;justify-content:center;flex-wrap:wrap;margin:10px 0}.mini-card{width:48px;height:68px;border-radius:8px;background:#f3efe4;color:#151515;display:grid;place-items:center;font-size:22px;font-weight:950}.mini-card.joker{background:#292433;color:#f1d18d}.result{font-size:17px;font-weight:850;line-height:1.55;text-align:center}.selection-hint{text-align:center;font-size:13px;color:var(--muted);margin-top:7px}\n.ddz-hand{display:flex;align-items:flex-end;overflow-x:auto;padding:24px 4px 14px;min-height:120px;scrollbar-width:none;isolation:isolate}.ddz-hand::-webkit-scrollbar{display:none}\n.ddz-card{width:52px;height:78px;flex:0 0 52px;margin-left:-22px;border-radius:9px;background:linear-gradient(150deg,#fffdf7,#ddd8cd);color:#171717;box-shadow:0 4px 0 #999388,0 8px 16px rgba(0,0,0,.28);padding:5px;display:flex;flex-direction:column;justify-content:space-between;font-weight:950;user-select:none;transition:transform .12s;position:relative}\n.ddz-card:first-child{margin-left:0}.ddz-card.red-suit{color:#c43d43}.ddz-card.joker-black{background:linear-gradient(150deg,#32343b,#17191e);color:#f2f2f2}.ddz-card.joker-red{background:linear-gradient(150deg,#76333a,#35171b);color:#ffe1ca}.ddz-card.selected{transform:translateY(-16px);outline:3px solid var(--gold)}.ddz-card .rank{font-size:17px;line-height:1}.ddz-card .suit{font-size:24px;text-align:center;line-height:1}.ddz-card .mini-rank{font-size:10px;text-align:right;opacity:.7}\n.ddz-small-row{display:flex;gap:5px;justify-content:center;flex-wrap:wrap;margin:8px 0}.ddz-mini{width:35px;height:49px;border-radius:7px;background:#f6f2e8;color:#171717;display:grid;place-items:center;font-weight:900;box-shadow:0 2px 0 #8d887e;font-size:15px}.ddz-mini.red-suit{color:#c43d43}.ddz-mini.joker-black{background:#24272e;color:#f2f2f2}.ddz-mini.joker-red{background:#6d3036;color:#ffe3ce}\n.ddz-role{display:inline-block;margin-left:4px;padding:2px 6px;border-radius:999px;font-size:10px;background:#3a3021;color:#f1cb7c}.ddz-trick{margin-top:10px}.actions.four{grid-template-columns:repeat(4,1fr)}\n\n.cm-hand{display:flex;align-items:flex-end;overflow-x:auto;padding:24px 4px 16px;min-height:112px;scrollbar-width:none;isolation:isolate}.cm-hand::-webkit-scrollbar{display:none}\n.cm-tile{width:48px;height:68px;flex:0 0 48px;margin-left:-18px;border-radius:8px;background:linear-gradient(150deg,#fffdf5,#ddd8ca);color:#171717;box-shadow:0 4px 0 #989184,0 8px 16px rgba(0,0,0,.28);display:flex;flex-direction:column;align-items:center;justify-content:center;position:relative;user-select:none;transition:transform .12s}.cm-tile:first-child{margin-left:0}.cm-tile strong{font-size:25px;line-height:1}.cm-tile span{font-size:13px;font-weight:900;margin-top:3px}.cm-tile.suit-W{color:#c94343}.cm-tile.suit-T{color:#3477c8}.cm-tile.suit-B{color:#27895c}.cm-tile.selected{transform:translateY(-15px);outline:3px solid var(--gold)}.cm-tile.drawn{margin-left:-9px}.cm-tile.missing-suit{box-shadow:0 4px 0 #989184,0 0 0 2px rgba(223,112,112,.5),0 8px 16px rgba(0,0,0,.28)}.cm-mini{width:33px;height:46px;flex:0 0 33px;margin-left:-8px;border-radius:6px;box-shadow:0 2px 0 #989184;font-size:12px}.cm-mini strong{font-size:17px}.cm-mini span{font-size:10px}.cm-river{display:grid;grid-template-columns:repeat(9,minmax(0,1fr));gap:5px;background:#111319;border:1px solid var(--line);border-radius:15px;padding:9px;min-height:62px}.cm-river-item{display:flex;justify-content:center}.cm-river .cm-tile{margin-left:0}.cm-meld-board{display:grid;gap:7px;margin-top:9px}.cm-meld-row{background:#101217;border:1px solid var(--line);border-radius:13px;padding:8px}.cm-meld-name{font-size:12px;color:var(--muted);margin-bottom:5px}.cm-melds{display:flex;gap:10px;overflow-x:auto}.cm-meld-group{display:flex}.cm-meld-group .cm-tile{margin-left:-7px}.cm-meld-group .cm-tile:first-child{margin-left:0}\n.draw-wrap{margin-top:12px}.canvas-shell{position:relative;background:#f7f4ed;border-radius:16px;overflow:hidden;box-shadow:inset 0 0 0 1px #c8c3b7}.draw-canvas{display:block;width:100%;aspect-ratio:4/3;touch-action:none;background:#fff}.canvas-empty{position:absolute;inset:0;display:grid;place-items:center;color:#9a9a9a;font-size:13px;pointer-events:none}.draw-tools{display:flex;gap:7px;align-items:center;overflow-x:auto;padding:10px 0 2px;scrollbar-width:none}.draw-tools::-webkit-scrollbar{display:none}.color-dot{width:35px;height:35px;min-height:35px;padding:0;border-radius:50%;border:3px solid transparent;flex:none}.color-dot.active{border-color:var(--gold)}.tool-btn{min-width:48px;padding:8px 10px;min-height:40px}.word-choices{display:grid;grid-template-columns:1fr;gap:9px;margin-top:12px}.word-choice{background:#101217;color:var(--text);border:1px solid var(--line);text-align:left}.word-choice small{display:block;color:var(--muted);font-weight:500;margin-top:3px}.guess-row{display:flex;gap:8px;margin-top:10px}.guess-row input{flex:1}.guess-feed{display:flex;gap:6px;overflow-x:auto;padding:9px 0 1px;scrollbar-width:none}.guess-chip{white-space:nowrap;background:#101217;border:1px solid var(--line);border-radius:999px;padding:6px 9px;font-size:12px;color:var(--muted)}.guess-chip.correct{color:var(--green);border-color:rgba(113,199,151,.55)}.timer{font-variant-numeric:tabular-nums;color:var(--gold);font-weight:900}\n.bottom{position:fixed;left:0;right:0;bottom:0;background:rgba(12,13,17,.93);backdrop-filter:blur(14px);border-top:1px solid rgba(255,255,255,.08);padding:9px max(12px,env(safe-area-inset-right)) calc(9px + env(safe-area-inset-bottom)) max(12px,env(safe-area-inset-left));z-index:20}.bottom-inner{max-width:760px;margin:auto;display:flex;gap:9px}.bottom button{flex:1}.modal{position:fixed;inset:0;background:rgba(0,0,0,.67);display:flex;align-items:flex-end;justify-content:center;padding:12px;z-index:50}.sheet{width:min(100%,760px);max-height:82dvh;overflow:auto;background:#17191f;border:1px solid var(--line);border-radius:24px;padding:17px;box-shadow:var(--shadow)}.sheet-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:13px}.sheet h2{font-size:19px;margin:0}.rule{font-size:14px;color:var(--muted);line-height:1.75}.rule b{color:var(--text)}.setting-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.toggle{display:flex;gap:8px;align-items:center;background:#101217;border:1px solid var(--line);border-radius:14px;padding:12px}.toggle input{width:20px;height:20px;min-height:0}.toast{position:fixed;left:50%;bottom:88px;transform:translateX(-50%);background:#050608;color:white;padding:10px 14px;border-radius:999px;font-size:13px;opacity:0;pointer-events:none;transition:.2s;z-index:80;max-width:86%;text-align:center}.toast.show{opacity:1}\n@media(max-width:520px){.mode-grid{grid-template-columns:1fr 1fr}.mode{min-height:92px}.play-card{width:59px;height:86px}.actions.three,.actions.four{grid-template-columns:1fr 1fr}.setting-grid{grid-template-columns:1fr}.ddz-card{margin-left:-24px}}\n</style>\n</head>\n<body>\n<div class="app">\n  <div class="top"><div class="brand">局域网游戏厅</div><div class="top-actions"><div class="net" id="net"></div><button class="icon-btn" id="helpBtn">?</button><button class="icon-btn hidden" id="settingsBtn">⚙</button></div></div>\n\n  <section class="card" id="joinCard">\n    <div class="title">加入房间</div><div class="muted" style="margin:5px 0 12px">连接同一热点，支持 2～4 人。</div>\n    <input id="nameInput" maxlength="10" placeholder="你的昵称"><button class="full" id="joinBtn" style="margin-top:10px">进入</button>\n  </section>\n\n  <section class="card hidden" id="lobbyCard">\n    <div class="row"><div class="grow"><div class="title">选择玩法</div><div class="muted" id="lobbyHint"></div></div><button class="secondary" id="readyBtn">准备</button></div>\n    <div class="mode-grid" style="margin-top:13px">\n      <div class="mode" id="modeCards"><div class="mode-emoji">🂠</div><div><div class="mode-name">骗子牌</div><div class="mode-desc">暗出与质疑</div></div></div>\n      <div class="mode" id="modeDice"><div class="mode-emoji">🎲</div><div><div class="mode-name">大话骰</div><div class="mode-desc">叫骰与开你</div></div></div>\n      <div class="mode draw-mode" id="modeDraw"><div class="mode-emoji">🎨</div><div><div class="mode-name">你画我猜</div><div class="mode-desc">中文词条 · 轮流作画</div></div></div>\n      <div class="mode" id="modeDdz"><div class="mode-emoji">🃏</div><div><div class="mode-name">斗地主</div><div class="mode-desc">1～3 人 · 自动补机器人</div></div></div>\n      <div class="mode" id="modeChuanma"><div class="mode-emoji">🀄</div><div><div class="mode-name">四川麻将</div><div class="mode-desc">换三张 · 定缺 · 血战</div></div></div>\n    </div>\n    <div class="muted" style="margin:14px 0 7px">玩家</div><div class="players" id="playersLobby"></div>\n    <button class="full hidden" id="startBtn" style="margin-top:13px">开始</button>\n  </section>\n\n  <section class="card hidden" id="gameCard">\n    <div class="players" id="playersGame"></div>\n\n    <div id="cardsGame" class="hidden">\n      <div class="stage"><div class="stage-kicker">本轮目标</div><div class="stage-main" id="targetRank">Q</div><div class="stage-sub" id="cardsTurnText"></div></div>\n      <div class="notice" id="lastPlayText">还没人出牌</div>\n      <div class="muted" style="margin-top:14px">你的牌</div><div class="hand" id="myCards"></div><div class="selection-hint" id="selectionHint">选择 1～3 张</div>\n      <div class="actions" id="cardsActions"><button class="green" id="playCardsBtn">盖牌</button><button class="red" id="challengeCardsBtn">质疑上一手</button></div>\n      <div class="reveal hidden" id="cardsReveal"><div class="muted" style="text-align:center">上一手翻开</div><div class="reveal-cards" id="revealedCards"></div><div class="result" id="cardsResult"></div><button class="full blue hidden" id="cardsNextBtn" style="margin-top:12px">下一轮</button></div>\n    </div>\n\n    <div id="diceGame" class="hidden">\n      <div class="stage"><div class="stage-kicker">当前叫法</div><div class="stage-main" id="diceBid">尚未叫骰</div><div class="stage-sub" id="diceTurnText"></div></div>\n      <div class="dice" id="myDice"></div>\n      <div id="diceControls">\n        <div class="notice" id="diceRuleNotice">叫骰表示“至少”有这么多。开你：实际少于叫数才成功；抓准：实际必须刚好相等。</div>\n        <div class="muted" style="margin-top:12px">数量</div>\n        <div class="counter"><button class="secondary" id="qtyMinus">−</button><strong id="qtyValue">1</strong><button class="secondary" id="qtyPlus">＋</button></div>\n        <div class="faces" id="faces"></div>\n        <div class="actions three"><button class="green" id="bidBtn">叫骰</button><button class="red" id="challengeDiceBtn">开你</button><button class="secondary" id="exactBtn">抓准</button></div>\n      </div>\n      <div class="reveal hidden" id="diceReveal">\n        <div class="result" id="diceResult"></div>\n        <div class="dice-reveal-list" id="diceRevealHands"></div>\n        <button class="full blue hidden" id="diceNextBtn" style="margin-top:12px">下一轮</button>\n      </div>\n    </div>\n\n    <div id="ddzGame" class="hidden">\n      <div class="stage">\n        <div class="stage-kicker" id="ddzKicker">叫地主</div>\n        <div class="stage-main" id="ddzMain">等待叫分</div>\n        <div class="stage-sub" id="ddzSub"></div>\n      </div>\n      <div class="ddz-small-row hidden" id="ddzBottom"></div>\n      <div class="notice ddz-trick" id="ddzLastPlay">尚未出牌</div>\n\n      <div class="muted" style="margin-top:13px">你的手牌</div>\n      <div class="ddz-hand" id="ddzHand"></div>\n      <div class="selection-hint" id="ddzSelection">点牌选择</div>\n\n      <div id="ddzBidPanel" class="hidden">\n        <div class="actions four">\n          <button class="secondary" data-ddz-bid="0">不叫</button>\n          <button data-ddz-bid="1">1 分</button>\n          <button data-ddz-bid="2">2 分</button>\n          <button data-ddz-bid="3">3 分</button>\n        </div>\n      </div>\n\n      <div id="ddzPlayPanel" class="hidden">\n        <div class="actions three">\n          <button class="green" id="ddzPlayBtn">出牌</button>\n          <button class="secondary" id="ddzPassBtn">不出</button>\n          <button class="secondary" id="ddzHintBtn">提示</button>\n        </div>\n      </div>\n    </div>\n\n\n    <div id="chuanmaGame" class="hidden">\n      <div class="stage">\n        <div class="stage-kicker" id="cmKicker">四川麻将</div>\n        <div class="stage-main" id="cmMain">等待开始</div>\n        <div class="stage-sub" id="cmSub"></div>\n      </div>\n      <div class="notice" id="cmNotice"></div>\n\n      <div class="cm-meld-board" id="cmMeldBoard"></div>\n      <div class="muted" style="margin-top:12px">牌河</div>\n      <div class="cm-river" id="cmRiver"></div>\n\n      <div class="muted" style="margin-top:12px">你的手牌</div>\n      <div class="cm-hand" id="cmHand"></div>\n      <div class="selection-hint" id="cmSelection">点牌选择</div>\n\n      <div id="cmExchangePanel" class="hidden">\n        <button class="full green" id="cmExchangeBtn">确认换三张</button>\n      </div>\n      <div id="cmDingquePanel" class="hidden">\n        <div class="actions three">\n          <button data-cm-missing="W">缺万</button>\n          <button data-cm-missing="T">缺筒</button>\n          <button data-cm-missing="B">缺条</button>\n        </div>\n      </div>\n      <div id="cmPlayPanel" class="hidden">\n        <div class="actions three">\n          <button class="red" id="cmHuBtn">胡</button>\n          <button class="secondary" id="cmGangBtn">杠</button>\n          <button class="green" id="cmDiscardBtn">出牌</button>\n        </div>\n      </div>\n      <div id="cmResponsePanel" class="hidden">\n        <div class="actions four">\n          <button class="red" data-cm-response="hu">胡</button>\n          <button data-cm-response="gang">杠</button>\n          <button data-cm-response="peng">碰</button>\n          <button class="secondary" data-cm-response="pass">过</button>\n        </div>\n      </div>\n    </div>\n    <div id="drawGame" class="hidden">\n      <div class="stage">\n        <div class="stage-kicker" id="drawKicker">准备作画</div>\n        <div class="stage-main" id="drawMain">等待</div>\n        <div class="stage-sub"><span id="drawSub"></span> <span class="timer" id="drawTimer"></span></div>\n      </div>\n\n      <div id="wordChoicePanel" class="hidden">\n        <div class="notice">选择一个你愿意画的中文题目</div>\n        <div class="word-choices" id="wordChoices"></div>\n      </div>\n\n      <div class="draw-wrap hidden" id="canvasPanel">\n        <div class="canvas-shell"><canvas id="drawCanvas" class="draw-canvas" width="800" height="600"></canvas><div class="canvas-empty" id="canvasEmpty">画布还空着</div></div>\n        <div class="draw-tools hidden" id="drawTools">\n          <button class="color-dot active" data-color="#111111" style="background:#111111"></button>\n          <button class="color-dot" data-color="#e05555" style="background:#e05555"></button>\n          <button class="color-dot" data-color="#3478d4" style="background:#3478d4"></button>\n          <button class="color-dot" data-color="#35a36f" style="background:#35a36f"></button>\n          <button class="color-dot" data-color="#f0b72f" style="background:#f0b72f"></button>\n          <button class="secondary tool-btn" id="widthBtn">中</button>\n          <button class="secondary tool-btn" id="eraserBtn">橡皮</button>\n          <button class="secondary tool-btn" id="undoBtn">撤销</button>\n          <button class="secondary tool-btn" id="clearBtn">清空</button>\n        </div>\n        <div class="guess-row hidden" id="guessRow"><input id="guessInput" maxlength="20" placeholder="输入中文答案"><button class="green" id="guessBtn">猜</button></div>\n        <div class="guess-feed" id="guessFeed"></div>\n      </div>\n\n      <div class="reveal hidden" id="drawReveal">\n        <div class="result" id="drawResult"></div>\n        <button class="full blue hidden" id="drawNextBtn" style="margin-top:12px">下一题</button>\n      </div>\n    </div>\n  </section>\n\n  <section class="card hidden" id="winnerCard"><div class="stage"><div class="stage-kicker">本局冠军</div><div class="stage-main" id="winnerName"></div></div><button class="full hidden" id="backLobbyBtn">回到大厅</button></section>\n</div>\n\n<div class="bottom hidden" id="bottomBar"><div class="bottom-inner"><button class="secondary" id="refreshBtn">刷新</button><button class="red hidden" id="endGameBtn">结束游戏</button><button class="secondary" id="leaveBtn">离开</button></div></div>\n\n<div class="modal hidden" id="helpModal"><div class="sheet"><div class="sheet-head"><h2>怎么玩</h2><button class="icon-btn" data-close="helpModal">×</button></div><div class="rule">\n<b>骗子牌：</b>暗出 1～3 张，下一家继续或质疑。目标牌和 Joker 算真话。<br><br>\n<b>大话骰：</b>叫法表示全场“至少”有相应数量。开你只在实际数量少于叫数时成功；相等或更多都算上一家叫法成立。抓准则要求实际数量刚好相等。开启1点万能时，叫2～6点会把1点计入；叫1点只统计1点。<br><br>\n<b>你画我猜：</b>画家从 3 个中文题目中选一个；不能写字、数字或拼音。猜中越早得分越高，画家也会得分。每个人轮流作画。<br><br>\n<b>斗地主：</b>1～3 名真人，系统自动补足 3 家。每人 17 张，3 张底牌归地主；按 1～3 分轮流叫地主。地主先出，支持常见完整牌型。<br><br>\n<b>四川麻将：</b>2～4 人，使用万、筒、条共 108 张牌。先换三张同花色牌，再定缺；有缺门牌时必须优先打出。支持碰、明杠、暗杠、补杠、自摸与点炮，采用血战到底和简化番分。\n</div></div></div>\n\n<div class="modal hidden" id="settingsModal"><div class="sheet"><div class="sheet-head"><h2>房主设置</h2><button class="icon-btn" data-close="settingsModal">×</button></div><div class="setting-grid">\n<label><div class="muted">骗子牌酒量</div><select id="cardLives"><option>2</option><option selected>3</option><option>4</option><option>5</option></select></label>\n<label><div class="muted">大话骰初始骰子</div><select id="diceStart"><option>3</option><option>4</option><option selected>5</option><option>6</option></select></label>\n<label class="toggle"><input type="checkbox" id="onesWild" checked><span>1 点万能</span></label>\n<label class="toggle"><input type="checkbox" id="exactEnabled" checked><span>允许抓准</span></label>\n<label><div class="muted">每人作画次数</div><select id="drawRounds"><option>1</option><option selected>2</option><option>3</option></select></label>\n<label><div class="muted">每题时间</div><select id="drawTime"><option value="45">45 秒</option><option value="60">60 秒</option><option value="75" selected>75 秒</option><option value="90">90 秒</option></select></label>\n<label><div class="muted">你画我猜词库</div><select id="drawLibrary"><option value="random" selected>随机词库</option><option value="mixed">综合混合</option><option value="items">生活用品</option><option value="animals">动物植物</option><option value="food">食物饮品</option><option value="actions">动作职业</option><option value="places">地点交通</option><option value="campus">校园生活</option><option value="fun">趣味词条</option></select></label>\n<label><div class="muted">词条难度</div><select id="drawDifficulty"><option value="mixed" selected>混合</option><option value="easy">简单</option><option value="medium">普通</option><option value="hard">困难</option></select></label>\n</div></div></div>\n<div class="toast" id="toast"></div>\n\n<script>\n\nconst $=id=>document.getElementById(id),sleep=ms=>new Promise(r=>setTimeout(r,ms)),DIE=["","⚀","⚁","⚂","⚃","⚄","⚅"];\nlet token=localStorage.getItem("gh_token")||"",playerId=localStorage.getItem("gh_player_id")||"",seatKey=localStorage.getItem("gh_seat_key")||"";\nif(!seatKey){seatKey=(crypto.randomUUID?.()||("seat_"+Date.now()+"_"+Math.random().toString(36).slice(2)));localStorage.setItem("gh_seat_key",seatKey)}\nlet state=null,polling=false,busy=false,refreshing=false,joining=false,reconnecting=false,selectedCards=new Set(),selectedDdzCards=new Set(),selectedCmTiles=new Set(),bidQty=1,bidFace=2;\nlet drawColor="#111111",drawWidth=7,eraser=false,drawing=false,currentPoints=[],renderedStrokeSeq=-1,drawCanvasRevision=-1,lastPhase="",timerHandle=null,strokeQueue=[],strokeSending=false;\n\nfunction toast(msg){const t=$("toast");t.textContent=msg;t.classList.add("show");clearTimeout(window.__toast);window.__toast=setTimeout(()=>t.classList.remove("show"),1900)}\nfunction setNet(s){$("net").className="net "+s}\nfunction renderSafe(){try{render();return true}catch(e){console.error("界面渲染异常",e);const now=Date.now();if(!window.__lastRenderError||now-window.__lastRenderError>5000){toast("界面更新异常，请点击刷新");window.__lastRenderError=now}return false}}\nasync function api(path,opts={}){const c=new AbortController(),tm=setTimeout(()=>c.abort(),12000);try{const r=await fetch(path,{cache:"no-store",headers:{"Content-Type":"application/json"},signal:c.signal,...opts});const tx=await r.text();let d={};try{d=JSON.parse(tx)}catch{}if(!r.ok)throw new Error(d.error||tx||("HTTP "+r.status));return d}finally{clearTimeout(tm)}}\nfunction shell(){$("joinCard").classList.add("hidden");$("bottomBar").classList.remove("hidden");setNet("ok")}\nasync function join(){if(joining)return;joining=true;$("joinBtn").disabled=true;try{const name=$("nameInput").value.trim()||"玩家";localStorage.setItem("gh_name",name);const d=await api("/api/join",{method:"POST",body:JSON.stringify({name,token,playerId,seatKey})});if(d.ok===false)throw new Error(d.error);token=d.token;playerId=d.playerId;localStorage.setItem("gh_token",token);localStorage.setItem("gh_player_id",playerId);shell();poll()}catch(e){toast("加入失败："+e.message)}finally{joining=false;$("joinBtn").disabled=false}}\nasync function reconnect(){if(reconnecting)return false;reconnecting=true;try{const d=await api("/api/join",{method:"POST",body:JSON.stringify({name:localStorage.getItem("gh_name")||"玩家",token,playerId,seatKey})});if(!d.ok)return false;token=d.token;playerId=d.playerId;localStorage.setItem("gh_token",token);localStorage.setItem("gh_player_id",playerId);return true}catch(e){return false}finally{reconnecting=false}}\nasync function refresh(force=false){\n  if(!token||refreshing||(!force&&busy))return null;\n  refreshing=true;\n  try{\n    const drawArgs=`&drawSeq=${encodeURIComponent(renderedStrokeSeq)}&drawRevision=${encodeURIComponent(drawCanvasRevision)}`;\n    const d=await api(`/api/state?token=${encodeURIComponent(token)}${drawArgs}&_=${Date.now()}`);\n    state=d.state;setNet("ok");renderSafe();return d;\n  }catch(e){\n    setNet("wait");\n    if(await reconnect()){\n      try{const drawArgs=`&drawSeq=${encodeURIComponent(renderedStrokeSeq)}&drawRevision=${encodeURIComponent(drawCanvasRevision)}`;\n    const d=await api(`/api/state?token=${encodeURIComponent(token)}${drawArgs}&_=${Date.now()}`);state=d.state;setNet("ok");renderSafe();return d}catch(_){setNet("bad")}\n    }else setNet("bad");\n    return null;\n  }finally{refreshing=false}\n}\nasync function poll(){if(polling)return;polling=true;while(polling){await refresh();let ms=document.hidden?3000:1500;if(state?.mode==="draw"&&state?.phase==="draw_play")ms=document.hidden?2600:1000;await sleep(ms)}}\nasync function action(type,extra={}){\n  if(busy&&type!=="draw_stroke")return null;\n  const lock=type!=="draw_stroke",requestId=(crypto.randomUUID?.()||("req_"+Date.now()+"_"+Math.random()));\n  if(lock)busy=true;\n  try{\n    while(refreshing)await sleep(40);\n    let lastError=null;\n    for(let attempt=0;attempt<3;attempt++){\n      try{\n        const d=await api("/api/action",{method:"POST",body:JSON.stringify({token,type,requestId,drawSeq:renderedStrokeSeq,drawRevision:drawCanvasRevision,...extra})});\n        if(d.state){state=d.state;renderSafe()}\n        if(!d.ok)toast(d.error||"状态已更新");\n        return d;\n      }catch(e){\n        lastError=e;\n        if(attempt<2)await sleep(280*(attempt+1));\n      }\n    }\n    if(type!=="draw_stroke"){\n      await refresh(true);\n      toast("连接有波动，已同步最新状态");\n    }\n    return null;\n  }finally{if(lock)busy=false}\n}\nfunction me(){return state?.players.find(p=>p.id===playerId)}\nfunction esc(s){return String(s).replace(/[&<>"\']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",\'"\':"&quot;","\'":"&#39;"}[c]))}\nfunction clearLocalSeat(){["gh_token","gh_player_id","gh_seat_key"].forEach(k=>localStorage.removeItem(k))}\nasync function manualRefresh(){while(refreshing)await sleep(40);const d=await refresh(true);toast(d?"已刷新最新状态":"刷新失败，请检查连接")}\nfunction endCurrentGame(){if(state?.isHost&&state.phase!=="lobby"&&confirm("结束当前游戏并回到大厅？所有真人玩家将保持准备状态。"))action("reset")}\nasync function leaveRoom(){if(!state)return;if(state.phase!=="lobby"){if(confirm("牌局进行中暂离会保留座位，重新打开本页即可恢复。现在暂离？"))location.replace("about:blank");return}if(!confirm("确定退出房间并释放座位？"))return;try{await api("/api/action",{method:"POST",body:JSON.stringify({token,type:"leave",requestId:(crypto.randomUUID?.()||Date.now()+"")})})}catch(e){}clearLocalSeat();location.reload()}\nfunction kickPlayer(id,name){if(confirm(`将 ${name} 移出房间？`))action("kick",{targetId:id})}\nfunction renameSelf(oldName){const name=prompt("修改昵称",oldName);if(name&&name.trim()&&name.trim()!==oldName){localStorage.setItem("gh_name",name.trim());action("rename",{name:name.trim()})}}\nfunction renderPlayers(el){el.innerHTML="";state.players.forEach(p=>{const d=document.createElement("div");const lobby=state.phase==="lobby";d.className="player"+(p.id===playerId?" me":"")+(state.turnPlayerId===p.id?" turn":"")+(p.out?" out":"")+(p.connected?"":" offline")+(lobby&&p.id===playerId?" self-edit":"");let meta=lobby?`${p.connected?"在线":"离线"} · ${p.ready?"已准备":"未准备"}`:(state.mode==="cards"?`🍷 ${p.life}`:state.mode==="dice"?`🎲 ${p.diceCount}`:state.mode==="draw"?`⭐ ${p.score}`:state.mode==="chuanma"?`${p.cmWon?"已胡 · ":""}${p.cmMissing?"缺"+({W:"万",T:"筒",B:"条"}[p.cmMissing])+" · ":""}${p.cmScore>=0?"+":""}${p.cmScore} · ${p.handCount}张`:`${p.role||"待定"} · ${p.handCount} 张`);if(!lobby&&!p.connected)meta+=" · 离线";d.innerHTML=`<div class="pname">${p.isBot?"🤖 ":""}${esc(p.name)}${p.id===state.hostPlayerId?" · 房主":""}</div><div class="pmeta">${meta}${lobby&&p.id===playerId?" · 点按改名":""}</div>`;if(lobby&&p.id===playerId)d.onclick=()=>renameSelf(p.name);if(lobby&&state.isHost&&p.id!==playerId&&!p.isBot){const k=document.createElement("button");k.className="seat-kick";k.textContent=p.connected?"移出房间":"清理离线座位";k.onclick=e=>{e.stopPropagation();kickPlayer(p.id,p.name)};d.appendChild(k)}el.appendChild(d)})}\nfunction renderLobby(){const lobby=state.phase==="lobby";$("lobbyCard").classList.toggle("hidden",!lobby);$("gameCard").classList.toggle("hidden",lobby||state.phase==="finished");$("winnerCard").classList.toggle("hidden",state.phase!=="finished");$("settingsBtn").classList.toggle("hidden",!state.isHost||!lobby);$("endGameBtn").classList.toggle("hidden",!state.isHost||lobby);if(!lobby)return;renderPlayers($("playersLobby"));$("readyBtn").textContent=me()?.ready?"取消准备":"准备";["Cards","Dice","Draw","Ddz","Chuanma"].forEach(x=>$("mode"+x).classList.toggle("active",state.mode===x.toLowerCase()));$("startBtn").classList.toggle("hidden",!state.isHost);$("startBtn").disabled=!state.canStart;const online=state.players.filter(p=>p.connected).length;$("lobbyHint").textContent=state.mode==="ddz"?`斗地主固定 3 人 · 在线 ${online}/${state.players.length}`:state.mode==="chuanma"?`川麻 2～4 名真人 · 不补机器人 · 在线 ${online}/${state.players.length}`:`2～4 人 · 在线 ${online}/${state.players.length}`;$("cardLives").value=state.settings.cardLives;$("diceStart").value=state.settings.diceStart;$("onesWild").checked=state.settings.onesWild;$("exactEnabled").checked=state.settings.exactEnabled;$("drawRounds").value=state.settings.drawRounds;$("drawTime").value=state.settings.drawTime;$("drawDifficulty").value=state.settings.drawDifficulty;$("drawLibrary").value=state.settings.drawLibrary||"random"}\nfunction renderCards(){if(state.mode!=="cards")return;const turn=state.players.find(p=>p.id===state.turnPlayerId);$("targetRank").textContent=state.card.targetRank;$("cardsTurnText").textContent=state.phase==="cards_reveal"?"本轮已结算":(turn?.id===playerId?"轮到你":"等待 "+(turn?.name||""));$("lastPlayText").textContent=state.card.lastPlay?`${state.card.lastPlay.playerName} 盖了 ${state.card.lastPlay.count} 张`:"还没人出牌";const hand=$("myCards");hand.innerHTML="";const valid=new Set((state.myCards||[]).map(c=>c.id));[...selectedCards].forEach(id=>{if(!valid.has(id))selectedCards.delete(id)});(state.myCards||[]).forEach(c=>{const d=document.createElement("div");d.className="play-card"+(c.rank==="JOKER"?" joker":"")+(selectedCards.has(c.id)?" selected":"");d.innerHTML=c.rank==="JOKER"?\'<div>JOKER</div><div class="big">🃏</div><div>万能</div>\':`<div>${c.rank}</div><div class="big">${c.rank}</div><div>${c.rank}</div>`;d.onclick=()=>{if(selectedCards.has(c.id))selectedCards.delete(c.id);else if(selectedCards.size<3)selectedCards.add(c.id);else toast("最多选择 3 张");renderCards()};hand.appendChild(d)});if(!(state.myCards||[]).length)hand.innerHTML=\'<div class="muted">你已没有手牌，只能质疑上一手</div>\';$("selectionHint").textContent=selectedCards.size?`已选 ${selectedCards.size} 张`:"选择 1～3 张";const myTurn=state.phase==="cards_play"&&state.turnPlayerId===playerId&&!me()?.out;$("playCardsBtn").disabled=!myTurn||selectedCards.size<1||selectedCards.size>3;$("challengeCardsBtn").disabled=!myTurn||!state.card.lastPlay;$("cardsActions").classList.toggle("hidden",state.phase!=="cards_play");const reveal=state.phase==="cards_reveal";$("cardsReveal").classList.toggle("hidden",!reveal);if(reveal){$("revealedCards").innerHTML="";(state.card.revealedCards||[]).forEach(rank=>{const d=document.createElement("div");d.className="mini-card"+(rank==="JOKER"?" joker":"");d.textContent=rank==="JOKER"?"🃏":rank;$("revealedCards").appendChild(d)});$("cardsResult").textContent=state.roundResult;$("cardsNextBtn").classList.toggle("hidden",!state.canAdvanceRound)}}\nfunction diceValid(){const b=state.dice.currentBid;if(!b)return bidQty>=1;return bidQty>b.quantity||(bidQty===b.quantity&&bidFace>b.face)}\nfunction normalizeDice(){const b=state.dice.currentBid;if(b&&!diceValid()){if(b.face<6){bidQty=b.quantity;bidFace=b.face+1}else{bidQty=b.quantity+1;bidFace=1}}}\nfunction renderDice(){\n  if(state.mode!=="dice")return;\n  const turn=state.players.find(p=>p.id===state.turnPlayerId),b=state.dice.currentBid;\n  const maxDice=state.players.filter(p=>!p.out).reduce((sum,p)=>sum+Number(p.diceCount||0),0);\n  bidQty=Math.max(1,Math.min(bidQty,Math.max(1,maxDice)));\n  $("diceBid").textContent=b?`至少 ${b.quantity} 个 ${DIE[b.face]}`:"尚未叫骰";\n  $("diceRuleNotice").textContent=state.settings.onesWild\n    ?"叫骰表示“至少”有这么多。叫2～6点时，1点也算万能点；开你只在实际数量更少时成功，抓准必须刚好相等。"\n    :"叫骰表示“至少”有这么多。当前1点不万能；开你只在实际数量更少时成功，抓准必须刚好相等。";\n  $("diceTurnText").textContent=state.phase==="dice_reveal"?"本轮已结算":(turn?.id===playerId?"轮到你":"等待 "+(turn?.name||""));\n  $("myDice").innerHTML="";\n  (state.myDice||[]).forEach(n=>{const d=document.createElement("div");d.className="die";d.textContent=DIE[n];$("myDice").appendChild(d)});\n  if(!(state.myDice||[]).length)$("myDice").innerHTML=\'<div class="muted">你已出局，正在观战</div>\';\n  normalizeDice();$("qtyValue").textContent=bidQty;$("faces").innerHTML="";\n  for(let n=1;n<=6;n++){const f=document.createElement("button");f.className="face"+(bidFace===n?" active":"");f.textContent=DIE[n];f.onclick=()=>{bidFace=n;renderDice()};$("faces").appendChild(f)}\n  const myTurn=state.phase==="dice_bidding"&&state.turnPlayerId===playerId&&!me()?.out;\n  $("diceControls").classList.toggle("hidden",state.phase!=="dice_bidding");\n  $("bidBtn").disabled=!myTurn||!diceValid();$("challengeDiceBtn").disabled=!myTurn||!b;$("exactBtn").disabled=!myTurn||!b||!state.settings.exactEnabled;\n  const reveal=state.phase==="dice_reveal";$("diceReveal").classList.toggle("hidden",!reveal);\n  if(reveal){\n    $("diceResult").textContent=state.roundResult;\n    const box=$("diceRevealHands");box.innerHTML="";\n    (state.dice.revealed||[]).forEach(row=>{\n      const line=document.createElement("div");line.className="dice-reveal-row";\n      const name=document.createElement("div");name.className="dice-reveal-name";name.textContent=row.playerName;\n      const dice=document.createElement("div");dice.className="dice-reveal-dice";\n      (row.dice||[]).forEach(n=>{const x=document.createElement("span");x.textContent=DIE[n];dice.appendChild(x)});\n      line.append(name,dice);box.appendChild(line);\n    });\n    $("diceNextBtn").classList.toggle("hidden",!state.canAdvanceRound);\n  }\n}\n\nconst SUIT_SYMBOL={S:"♠",H:"♥",D:"♦",C:"♣"};\nfunction ddzCardClass(c,mini=false){\n  let cls=mini?"ddz-mini":"ddz-card";\n  if(c.suit==="H"||c.suit==="D")cls+=" red-suit";\n  if(c.rank==="BJ")cls+=" joker-black";\n  if(c.rank==="RJ")cls+=" joker-red";\n  return cls;\n}\nfunction ddzCardLabel(c){if(c.rank==="BJ")return "小王";if(c.rank==="RJ")return "大王";return c.rank}\nfunction renderDdzCard(c,mini=false){\n  const el=document.createElement("div");el.className=ddzCardClass(c,mini);\n  if(mini){el.textContent=c.rank==="BJ"?"小王":c.rank==="RJ"?"大王":`${c.rank}${SUIT_SYMBOL[c.suit]||""}`;return el}\n  const suit=SUIT_SYMBOL[c.suit]||"★";\n  el.innerHTML=`<div class="rank">${ddzCardLabel(c)}</div><div class="suit">${c.rank==="BJ"?"♚":c.rank==="RJ"?"♛":suit}</div><div class="mini-rank">${c.rank==="BJ"||c.rank==="RJ"?"":suit}</div>`;\n  return el;\n}\nfunction renderDdz(){\n  if(state.mode!=="ddz")return;\n  const d=state.ddz,turn=state.players.find(p=>p.id===state.turnPlayerId);\n  const bidding=state.phase==="ddz_bidding",playing=state.phase==="ddz_play";\n  $("ddzKicker").textContent=bidding?"叫地主":"经典斗地主";\n  $("ddzMain").textContent=bidding?(d.highestBid?`当前 ${d.highestBid} 分`:"等待叫分"):(d.landlordName?`${d.landlordName} · 地主 · ${d.baseBid} 分`:"");\n  const turnText=turn?.id===playerId?(bidding?"轮到你叫分":"轮到你出牌"):(d.botThinking?`${turn?.name||"机器人"} 思考中…`:`等待 ${turn?.name||""}`);\n  $("ddzSub").textContent=bidding?turnText:`${turnText} · ${d.baseBid}分 × ${d.multiplier}倍`;\n  $("ddzBottom").classList.toggle("hidden",!d.bottomCards?.length);\n  $("ddzBottom").innerHTML="";\n  (d.bottomCards||[]).forEach(c=>$("ddzBottom").appendChild(renderDdzCard(c,true)));\n\n  const last=d.lastPlay;\n  const bidText=(d.bidHistory||[]).map(x=>`${esc(x.playerName)}：${x.score?x.score+" 分":"不叫"}`).join("\u3000");\n  $("ddzLastPlay").innerHTML=last\n    ?`${esc(last.playerName)}：${esc(last.comboLabel)}<div class="ddz-small-row" id="ddzLastCards"></div>`\n    :(bidding?(bidText||"每人只能叫一次，分数必须高于当前叫分"):(d.message||"新一轮，请自由出牌"));\n  if(last){\n    const row=$("ddzLastCards");\n    (last.cards||[]).forEach(c=>row.appendChild(renderDdzCard(c,true)));\n  }\n\n  const hand=$("ddzHand");hand.innerHTML="";\n  const valid=new Set((state.myDdzCards||[]).map(c=>c.id));\n  [...selectedDdzCards].forEach(id=>{if(!valid.has(id))selectedDdzCards.delete(id)});\n  if(state.turnPlayerId!==playerId&&!bidding)selectedDdzCards.clear();\n  (state.myDdzCards||[]).forEach((c,index)=>{\n    const el=renderDdzCard(c,false);\n    el.style.zIndex=String(index+1);\n    el.classList.toggle("selected",selectedDdzCards.has(c.id));\n    el.onclick=()=>{\n      if(!playing||state.turnPlayerId!==playerId)return;\n      if(selectedDdzCards.has(c.id))selectedDdzCards.delete(c.id);else selectedDdzCards.add(c.id);\n      renderDdz();\n    };\n    hand.appendChild(el);\n  });\n  $("ddzSelection").textContent=selectedDdzCards.size?`已选 ${selectedDdzCards.size} 张`:(playing?"点牌选择，或使用“提示”":"先看牌，再决定叫分");\n\n  $("ddzBidPanel").classList.toggle("hidden",!bidding);\n  document.querySelectorAll("[data-ddz-bid]").forEach(btn=>{\n    const score=Number(btn.dataset.ddzBid);\n    btn.disabled=!bidding||state.turnPlayerId!==playerId||(score>0&&score<=d.highestBid);\n  });\n  $("ddzPlayPanel").classList.toggle("hidden",!playing);\n  const myTurn=playing&&state.turnPlayerId===playerId;\n  $("ddzPlayBtn").disabled=!myTurn||selectedDdzCards.size===0;\n  $("ddzPassBtn").disabled=!myTurn||!last;\n  $("ddzHintBtn").disabled=!myTurn;\n}\nconst CM_SUIT_LABEL={W:"万",T:"筒",B:"条"};\nfunction cmTileClass(tile,mini=false){return (mini?"cm-tile cm-mini":"cm-tile")+` suit-${tile.suit}`}\nfunction renderCmTile(tile,mini=false){const el=document.createElement("div");el.className=cmTileClass(tile,mini);el.innerHTML=`<strong>${tile.rank}</strong><span>${CM_SUIT_LABEL[tile.suit]}</span>`;return el}\nfunction cmSelectionValidExchange(){if(selectedCmTiles.size!==3)return false;const tiles=(state.chuanma.myHand||[]).filter(t=>selectedCmTiles.has(t.id));return tiles.length===3&&new Set(tiles.map(t=>t.suit)).size===1}\nfunction selectedCmTile(){const id=[...selectedCmTiles][0];return (state?.chuanma?.myHand||[]).find(t=>t.id===id)}\nfunction renderChuanma(){\n  if(state.mode!=="chuanma")return;\n  const cm=state.chuanma,phase=state.phase,turn=state.players.find(p=>p.id===state.turnPlayerId),mePlayer=me();\n  const phaseNames={cm_exchange:"换三张",cm_dingque:"定缺",cm_play:"血战到底",cm_response:"等待响应"};\n  $("cmKicker").textContent=phaseNames[phase]||"四川麻将";\n  $("cmMain").textContent=phase==="cm_exchange"?cm.exchangeDirection:phase==="cm_dingque"?"万 · 筒 · 条":(turn?.id===playerId?"轮到你":turn?`等待 ${turn.name}`:"等待其他玩家");\n  $("cmSub").textContent=`牌墙 ${cm.wallCount} 张${cm.myMissing?` · 你缺${CM_SUIT_LABEL[cm.myMissing]}`:""}`;\n  $("cmNotice").textContent=cm.message||"";\n\n  const meldBoard=$("cmMeldBoard");meldBoard.innerHTML="";\n  state.players.forEach(p=>{\n    const row=document.createElement("div");row.className="cm-meld-row";\n    const title=document.createElement("div");title.className="cm-meld-name";title.textContent=`${p.name}${p.cmWon?" · 已胡":""}${p.cmMissing?` · 缺${CM_SUIT_LABEL[p.cmMissing]}`:""} · ${p.cmScore>=0?"+":""}${p.cmScore}`;row.appendChild(title);\n    const tiles=document.createElement("div");tiles.className="cm-melds";\n    (p.cmMelds||[]).forEach(m=>{const group=document.createElement("div");group.className="cm-meld-group";const count=m.type==="gang"?4:3;for(let i=0;i<count;i++)group.appendChild(renderCmTile({suit:m.suit,rank:m.rank},true));tiles.appendChild(group)});\n    row.appendChild(tiles);meldBoard.appendChild(row);\n  });\n\n  const river=$("cmRiver");river.innerHTML="";\n  (cm.discardPile||[]).forEach(item=>{const wrap=document.createElement("div");wrap.className="cm-river-item";wrap.title=item.playerName;wrap.appendChild(renderCmTile(item.tile,true));river.appendChild(wrap)});\n\n  const valid=new Set((cm.myHand||[]).map(t=>t.id));[...selectedCmTiles].forEach(id=>{if(!valid.has(id))selectedCmTiles.delete(id)});\n  if(phase!=="cm_exchange"&&!(phase==="cm_play"&&state.turnPlayerId===playerId))selectedCmTiles.clear();\n  const hand=$("cmHand");hand.innerHTML="";\n  (cm.myHand||[]).forEach((tile,index)=>{\n    const el=renderCmTile(tile,false);el.style.zIndex=String(index+1);el.classList.toggle("selected",selectedCmTiles.has(tile.id));\n    if(tile.id===cm.myDrawnId)el.classList.add("drawn");\n    if(cm.myMissing&&tile.suit===cm.myMissing)el.classList.add("missing-suit");\n    el.onclick=()=>{\n      if(phase==="cm_exchange"){\n        if(cm.exchangeSubmitted)return;\n        if(selectedCmTiles.has(tile.id))selectedCmTiles.delete(tile.id);else if(selectedCmTiles.size<3)selectedCmTiles.add(tile.id);else toast("换三张最多选择 3 张");\n      }else if(phase==="cm_play"&&state.turnPlayerId===playerId&&cm.canDiscard){\n        selectedCmTiles.clear();selectedCmTiles.add(tile.id);\n      }\n      renderChuanma();\n    };hand.appendChild(el);\n  });\n  if(cm.myWon)hand.innerHTML=\'<div class="muted">你已经胡牌，正在观看血战继续</div>\';\n\n  $("cmExchangePanel").classList.toggle("hidden",phase!=="cm_exchange");\n  $("cmDingquePanel").classList.toggle("hidden",phase!=="cm_dingque");\n  $("cmPlayPanel").classList.toggle("hidden",phase!=="cm_play"||state.turnPlayerId!==playerId||cm.myWon);\n  $("cmResponsePanel").classList.toggle("hidden",phase!=="cm_response"||!cm.responseOptions?.length||cm.responded);\n  $("cmExchangeBtn").disabled=cm.exchangeSubmitted||!cmSelectionValidExchange();\n  $("cmExchangeBtn").textContent=cm.exchangeSubmitted?"已选好，等待其他人":"确认换三张";\n  document.querySelectorAll("[data-cm-missing]").forEach(btn=>btn.disabled=cm.dingqueSubmitted);\n  document.querySelectorAll("[data-cm-response]").forEach(btn=>btn.disabled=!(cm.responseOptions||[]).includes(btn.dataset.cmResponse));\n  $("cmHuBtn").disabled=!cm.canHu;\n  $("cmGangBtn").disabled=!(cm.gangOptions||[]).length;\n  $("cmDiscardBtn").disabled=!cm.canDiscard||selectedCmTiles.size!==1;\n  if(phase==="cm_exchange")$("cmSelection").textContent=cm.exchangeSubmitted?"已提交，不能再修改":selectedCmTiles.size?`已选 ${selectedCmTiles.size}/3 张（必须同花色）`:"请选择三张同花色的牌";\n  else if(phase==="cm_dingque")$("cmSelection").textContent=cm.dingqueSubmitted?"已完成定缺，等待其他人":"选择一个你准备优先打空的花色";\n  else if(phase==="cm_response")$("cmSelection").textContent=cm.responded?"已响应，等待其他玩家":"请选择碰、杠、胡或过";\n  else $("cmSelection").textContent=selectedCmTiles.size?"已选 1 张":"定缺牌尚未打完时，必须优先打缺门";\n}\n\n$("cmExchangeBtn").onclick=()=>action("cm_exchange",{tileIds:[...selectedCmTiles]}).then(d=>{if(d?.ok)selectedCmTiles.clear()});\ndocument.querySelectorAll("[data-cm-missing]").forEach(btn=>btn.onclick=()=>action("cm_dingque",{suit:btn.dataset.cmMissing}));\ndocument.querySelectorAll("[data-cm-response]").forEach(btn=>btn.onclick=()=>action("cm_respond",{choice:btn.dataset.cmResponse}));\n$("cmDiscardBtn").onclick=async()=>{const tile=selectedCmTile();if(!tile)return;const d=await action("cm_discard",{tileId:tile.id});if(d?.ok)selectedCmTiles.clear()};\n$("cmHuBtn").onclick=()=>action("cm_self_hu");\n$("cmGangBtn").onclick=()=>{const options=state.chuanma.gangOptions||[];let option=null;const tile=selectedCmTile();if(tile)option=options.find(x=>x.suit===tile.suit&&x.rank===tile.rank);option=option||options[0];if(option)action("cm_gang",{suit:option.suit,rank:option.rank})};\nfunction canvas(){return $("drawCanvas")}\nfunction drawStroke(ctx,s){ctx.save();ctx.lineCap="round";ctx.lineJoin="round";ctx.strokeStyle=s.color;ctx.lineWidth=s.width;if(s.erase){ctx.globalCompositeOperation="destination-out";ctx.lineWidth=s.width*2}ctx.beginPath();s.points.forEach((p,i)=>{const x=p[0]*800,y=p[1]*600;i?ctx.lineTo(x,y):ctx.moveTo(x,y)});if(s.points.length===1)ctx.lineTo(s.points[0][0]*800+.1,s.points[0][1]*600+.1);ctx.stroke();ctx.restore()}\nfunction applyDrawCanvas(force=false){\n  if(state.mode!=="draw")return;\n  const d=state.draw,c=canvas(),ctx=c.getContext("2d");\n  const full=force||d.fullCanvas||drawCanvasRevision!==d.canvasRevision||renderedStrokeSeq>d.strokeSeq;\n  if(full){ctx.clearRect(0,0,c.width,c.height);(d.strokes||[]).forEach(s=>drawStroke(ctx,s))}else{(d.strokes||[]).forEach(s=>drawStroke(ctx,s))}\n  drawCanvasRevision=d.canvasRevision;renderedStrokeSeq=d.strokeSeq;\n  $("canvasEmpty").classList.toggle("hidden",d.strokeSeq>0||(d.strokes||[]).length>0);\n}\nfunction startTimer(){if(timerHandle)return;timerHandle=setInterval(()=>{if(!state||state.mode!=="draw")return;const r=Math.max(0,Math.ceil((state.draw.deadline||0)-Date.now()/1000));$("drawTimer").textContent=r?` · ${r}s`:""},250)}\nfunction renderDraw(){\n  if(state.mode!=="draw")return;\n  const d=state.draw,drawer=state.players.find(p=>p.id===d.drawerId),isDrawer=d.drawerId===playerId;\n  $("drawKicker").textContent=state.phase==="draw_choose"?(isDrawer?"选题":"画家正在选题"):state.phase==="draw_play"?(isDrawer?"你的题目":"正在作画"):"答案";\n  $("drawMain").textContent=state.phase==="draw_choose"?(isDrawer?"请选择":"请稍候"):state.phase==="draw_play"?(isDrawer?d.word:d.hint):(d.answer||"");\n  $("drawSub").textContent=state.phase==="draw_play"?(isDrawer?`${d.libraryLabel} · 不能写字、数字或拼音`:`${drawer?.name||""} 正在画 · ${d.libraryLabel}`):state.phase==="draw_reveal"?d.result:`第 ${d.turnIndex+1}/${d.totalTurns} 题 · ${d.libraryLabel||""}`;\n  $("wordChoicePanel").classList.toggle("hidden",!(state.phase==="draw_choose"&&isDrawer));$("wordChoices").innerHTML="";\n  (d.choices||[]).forEach((w,i)=>{const b=document.createElement("button");b.className="word-choice";b.innerHTML=`${esc(w.word)}<small>${esc(w.category)} · ${w.difficultyLabel} · ${w.libraryLabel}</small>`;b.onclick=()=>action("draw_choose",{index:i});$("wordChoices").appendChild(b)});\n  const showCanvas=["draw_play","draw_reveal"].includes(state.phase);$("canvasPanel").classList.toggle("hidden",!showCanvas);$("drawTools").classList.toggle("hidden",!(state.phase==="draw_play"&&isDrawer));\n  const guessed=(d.correctIds||[]).includes(playerId);$("guessRow").classList.toggle("hidden",!(state.phase==="draw_play"&&!isDrawer&&!guessed));$("guessFeed").innerHTML="";\n  (d.guesses||[]).slice(-8).forEach(g=>{const x=document.createElement("div");x.className="guess-chip"+(g.correct?" correct":"");x.textContent=g.correct?`${g.name} 猜对了`:`${g.name}：${g.text}`;$("guessFeed").appendChild(x)});\n  $("drawReveal").classList.toggle("hidden",state.phase!=="draw_reveal");$("drawResult").textContent=d.result||"";$("drawNextBtn").classList.toggle("hidden",!state.canAdvanceRound);\n  applyDrawCanvas(lastPhase!==state.phase);startTimer();lastPhase=state.phase;\n}\n\nasync function flushStrokeQueue(){\n  if(strokeSending)return;strokeSending=true;\n  try{\n    while(strokeQueue.length){\n      const payload=strokeQueue[0],requestId=(crypto.randomUUID?.()||("stroke_"+Date.now()+"_"+Math.random()));let done=false;\n      for(let attempt=0;attempt<3&&!done;attempt++){\n        try{\n          const d=await api("/api/action",{method:"POST",body:JSON.stringify({token,type:"draw_stroke",requestId,...payload})});\n          if(d.ok){renderedStrokeSeq=Math.max(renderedStrokeSeq,Number(d.strokeSeq||renderedStrokeSeq));drawCanvasRevision=Number(d.canvasRevision??drawCanvasRevision);done=true}else if(d.error){toast(d.error);done=true}\n        }catch(e){if(attempt<2)await sleep(180*(attempt+1))}\n      }\n      strokeQueue.shift();\n      if(!done){setNet("wait");await refresh(true)}\n    }\n  }finally{strokeSending=false}\n}\nfunction queueStroke(payload){strokeQueue.push(payload);if(strokeQueue.length>12)strokeQueue=strokeQueue.slice(-12);flushStrokeQueue()}\nfunction renderGame(){\n  if(["lobby","finished"].includes(state.phase))return;\n  renderPlayers($("playersGame"));\n  $("cardsGame").classList.toggle("hidden",state.mode!=="cards");\n  $("diceGame").classList.toggle("hidden",state.mode!=="dice");\n  $("drawGame").classList.toggle("hidden",state.mode!=="draw");\n  $("ddzGame").classList.toggle("hidden",state.mode!=="ddz");\n  $("chuanmaGame").classList.toggle("hidden",state.mode!=="chuanma");\n  if(state.mode==="cards")renderCards();else if(state.mode==="dice")renderDice();else if(state.mode==="draw")renderDraw();else if(state.mode==="ddz")renderDdz();else renderChuanma();\n}\nfunction render(){renderLobby();renderGame();if(state.phase==="finished"){$("winnerName").textContent=state.winnerName;$("backLobbyBtn").classList.toggle("hidden",!state.isHost)}}\nfunction updateSettings(){action("settings",{cardLives:Number($("cardLives").value),diceStart:Number($("diceStart").value),onesWild:$("onesWild").checked,exactEnabled:$("exactEnabled").checked,drawRounds:Number($("drawRounds").value),drawTime:Number($("drawTime").value),drawDifficulty:$("drawDifficulty").value,drawLibrary:$("drawLibrary").value})}\nfunction pointerPos(e){const r=canvas().getBoundingClientRect();return[(e.clientX-r.left)/r.width,(e.clientY-r.top)/r.height]}\nfunction beginDraw(e){if(state?.mode!=="draw"||state.phase!=="draw_play"||state.draw.drawerId!==playerId)return;e.preventDefault();drawing=true;currentPoints=[pointerPos(e)];canvas().setPointerCapture?.(e.pointerId)}\nfunction moveDraw(e){if(!drawing)return;e.preventDefault();const p=pointerPos(e),prev=currentPoints[currentPoints.length-1];if(prev&&Math.abs(p[0]-prev[0])+Math.abs(p[1]-prev[1])<0.002)return;currentPoints.push(p);drawStroke(canvas().getContext("2d"),{color:eraser?"#ffffff":drawColor,width:drawWidth,erase:eraser,points:[prev,p]})}\nfunction endDraw(e){if(!drawing)return;drawing=false;if(currentPoints.length){const step=Math.max(1,Math.ceil(currentPoints.length/110)),pts=currentPoints.filter((_,i)=>i%step===0).slice(0,120);if(pts[pts.length-1]!==currentPoints[currentPoints.length-1])pts.push(currentPoints[currentPoints.length-1]);queueStroke({color:drawColor,width:drawWidth,erase:eraser,points:pts})}currentPoints=[]}\n\n$("joinBtn").onclick=join;$("readyBtn").onclick=()=>action("toggle_ready");$("startBtn").onclick=()=>action("start");\n$("modeCards").onclick=()=>state?.isHost&&action("set_mode",{mode:"cards"});$("modeDice").onclick=()=>state?.isHost&&action("set_mode",{mode:"dice"});$("modeDraw").onclick=()=>state?.isHost&&action("set_mode",{mode:"draw"});$("modeDdz").onclick=()=>state?.isHost&&action("set_mode",{mode:"ddz"});$("modeChuanma").onclick=()=>state?.isHost&&action("set_mode",{mode:"chuanma"});\n$("playCardsBtn").onclick=()=>{const ids=[...selectedCards];selectedCards.clear();action("cards_play",{cardIds:ids})};$("challengeCardsBtn").onclick=()=>action("cards_challenge");$("cardsNextBtn").onclick=()=>action("next_round");\n$("qtyMinus").onclick=()=>{bidQty=Math.max(1,bidQty-1);renderDice()};$("qtyPlus").onclick=()=>{const maxDice=state?.players?.filter(p=>!p.out).reduce((sum,p)=>sum+Number(p.diceCount||0),0)||1;bidQty=Math.min(maxDice,bidQty+1);renderDice()};$("bidBtn").onclick=()=>action("dice_bid",{quantity:bidQty,face:bidFace});$("challengeDiceBtn").onclick=()=>action("dice_challenge");$("exactBtn").onclick=()=>action("dice_exact");$("diceNextBtn").onclick=()=>action("next_round");\nasync function waitForStrokeQueue(){while(strokeSending||strokeQueue.length)await sleep(30)}\n$("drawNextBtn").onclick=()=>action("next_round");$("guessBtn").onclick=()=>{const v=$("guessInput").value.trim();if(v){$("guessInput").value="";action("draw_guess",{guess:v})}};$("guessInput").onkeydown=e=>{if(e.key==="Enter")$("guessBtn").click()};$("undoBtn").onclick=async()=>{await waitForStrokeQueue();const d=await action("draw_undo");if(d?.ok){drawCanvasRevision=-1;await refresh(true)}};$("clearBtn").onclick=async()=>{if(!confirm("清空画布？"))return;await waitForStrokeQueue();const d=await action("draw_clear");if(d?.ok){drawCanvasRevision=-1;await refresh(true)}};$("eraserBtn").onclick=()=>{eraser=!eraser;$("eraserBtn").classList.toggle("blue",eraser)};$("widthBtn").onclick=()=>{drawWidth=drawWidth===4?7:drawWidth===7?12:4;$("widthBtn").textContent=drawWidth===4?"细":drawWidth===7?"中":"粗"};document.querySelectorAll(".color-dot").forEach(b=>b.onclick=()=>{drawColor=b.dataset.color;eraser=false;document.querySelectorAll(".color-dot").forEach(x=>x.classList.toggle("active",x===b));$("eraserBtn").classList.remove("blue")});canvas().addEventListener("pointerdown",beginDraw);canvas().addEventListener("pointermove",moveDraw);canvas().addEventListener("pointerup",endDraw);canvas().addEventListener("pointercancel",endDraw);\ndocument.querySelectorAll("[data-ddz-bid]").forEach(b=>b.onclick=()=>action("ddz_bid",{score:Number(b.dataset.ddzBid)}));\n$("ddzPlayBtn").onclick=async()=>{const ids=[...selectedDdzCards];const d=await action("ddz_play",{cardIds:ids});if(d?.ok){selectedDdzCards.clear();renderDdz()}};$("ddzPassBtn").onclick=async()=>{const d=await action("ddz_pass");if(d?.ok){selectedDdzCards.clear();renderDdz()}};$("ddzHintBtn").onclick=async()=>{const d=await action("ddz_hint");if(d?.ok&&d.hintCards?.length){selectedDdzCards=new Set(d.hintCards);renderDdz()}else if(d?.ok)toast(d.message||"没有能压过上一手的牌")};\n$("backLobbyBtn").onclick=()=>action("reset");$("refreshBtn").onclick=manualRefresh;$("endGameBtn").onclick=endCurrentGame;$("leaveBtn").onclick=leaveRoom;$("helpBtn").onclick=()=>$("helpModal").classList.remove("hidden");$("settingsBtn").onclick=()=>$("settingsModal").classList.remove("hidden");document.querySelectorAll("[data-close]").forEach(b=>b.onclick=()=>$(b.dataset.close).classList.add("hidden"));["cardLives","diceStart","onesWild","exactEnabled","drawRounds","drawTime","drawDifficulty","drawLibrary"].forEach(id=>$(id).onchange=updateSettings);$("nameInput").value=localStorage.getItem("gh_name")||"";$("nameInput").oninput=()=>localStorage.setItem("gh_name",$("nameInput").value);document.addEventListener("visibilitychange",()=>{if(!document.hidden)refresh()});if(token){shell();poll()}\n</script>\n</body>\n</html>'

DIFFICULTY_LABEL = {'easy': '简单', 'medium': '普通', 'hard': '困难'}
LIBRARY_LABEL = {'random': '随机词库', 'mixed': '综合混合', 'items': '生活用品', 'animals': '动物植物', 'food': '食物饮品', 'actions': '动作职业', 'places': '地点交通', 'campus': '校园生活', 'fun': '趣味词条'}
DRAW_RANDOM_LIBRARIES = ['items', 'animals', 'food', 'actions', 'places', 'campus', 'fun']
WORD_BANK = [{'word': '雨伞', 'category': '日常物品', 'difficulty': 'easy', 'aliases': ['伞'], 'library': 'items'},
 {'word': '牙刷', 'category': '日常物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '杯子', 'category': '日常物品', 'difficulty': 'easy', 'aliases': ['水杯'], 'library': 'items'},
 {'word': '钥匙', 'category': '日常物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '剪刀', 'category': '日常物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '闹钟', 'category': '日常物品', 'difficulty': 'easy', 'aliases': ['钟'], 'library': 'items'},
 {'word': '眼镜', 'category': '日常物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '帽子', 'category': '日常物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '拖鞋', 'category': '日常物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '书包', 'category': '日常物品', 'difficulty': 'easy', 'aliases': ['背包'], 'library': 'items'},
 {'word': '手电筒', 'category': '日常物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '风扇', 'category': '日常物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '台灯', 'category': '日常物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '镜子', 'category': '日常物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '梳子', 'category': '日常物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '衣架', 'category': '日常物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '扫把', 'category': '日常物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '枕头', 'category': '日常物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '被子', 'category': '日常物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '行李箱', 'category': '日常物品', 'difficulty': 'easy', 'aliases': ['旅行箱'], 'library': 'items'},
 {'word': '猫', 'category': '动物', 'difficulty': 'easy', 'aliases': ['小猫'], 'library': 'animals'},
 {'word': '狗', 'category': '动物', 'difficulty': 'easy', 'aliases': ['小狗'], 'library': 'animals'},
 {'word': '兔子', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '熊猫', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '长颈鹿', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '大象', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '狮子', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '老虎', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '猴子', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '企鹅', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '海豚', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '乌龟', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '章鱼', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '螃蟹', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '蝴蝶', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '蜗牛', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '蜜蜂', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '鸭子', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '公鸡', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '金鱼', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '苹果', 'category': '食物', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '香蕉', 'category': '食物', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '西瓜', 'category': '食物', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '草莓', 'category': '食物', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '葡萄', 'category': '食物', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '汉堡', 'category': '食物', 'difficulty': 'easy', 'aliases': ['汉堡包'], 'library': 'food'},
 {'word': '披萨', 'category': '食物', 'difficulty': 'easy', 'aliases': ['比萨'], 'library': 'food'},
 {'word': '冰淇淋', 'category': '食物', 'difficulty': 'easy', 'aliases': ['冰激凌', '雪糕'], 'library': 'food'},
 {'word': '蛋糕', 'category': '食物', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '面包', 'category': '食物', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '火锅', 'category': '食物', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '饺子', 'category': '食物', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '面条', 'category': '食物', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '荷包蛋', 'category': '食物', 'difficulty': 'easy', 'aliases': ['煎蛋'], 'library': 'food'},
 {'word': '棒棒糖', 'category': '食物', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '自行车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': ['单车'], 'library': 'places'},
 {'word': '摩托车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '公交车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': ['公共汽车'], 'library': 'places'},
 {'word': '出租车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': ['的士'], 'library': 'places'},
 {'word': '火车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '飞机', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '轮船', 'category': '交通工具', 'difficulty': 'easy', 'aliases': ['船'], 'library': 'places'},
 {'word': '救护车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '消防车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '滑板', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '太阳', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '月亮', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '彩虹', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '雪人', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '火山', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '闪电', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '云朵', 'category': '自然', 'difficulty': 'easy', 'aliases': ['云'], 'library': 'animals'},
 {'word': '大树', 'category': '自然', 'difficulty': 'easy', 'aliases': ['树'], 'library': 'animals'},
 {'word': '花朵', 'category': '自然', 'difficulty': 'easy', 'aliases': ['花'], 'library': 'animals'},
 {'word': '仙人掌', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '踢足球', 'category': '动作', 'difficulty': 'easy', 'aliases': ['踢球'], 'library': 'actions'},
 {'word': '打篮球', 'category': '动作', 'difficulty': 'easy', 'aliases': ['打球'], 'library': 'actions'},
 {'word': '跳绳', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '游泳', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '跑步', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '睡觉', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '刷牙', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '洗头', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '拍照', 'category': '动作', 'difficulty': 'easy', 'aliases': ['照相'], 'library': 'actions'},
 {'word': '钓鱼', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '吃饭', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '喝水', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '唱歌', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '跳舞', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '哭泣', 'category': '动作', 'difficulty': 'easy', 'aliases': ['哭'], 'library': 'actions'},
 {'word': '医生', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '老师', 'category': '职业', 'difficulty': 'easy', 'aliases': ['教师'], 'library': 'actions'},
 {'word': '厨师', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '警察', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '消防员', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '宇航员', 'category': '职业', 'difficulty': 'easy', 'aliases': ['航天员'], 'library': 'actions'},
 {'word': '快递员', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '画家', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '司机', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '农民', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '充电宝', 'category': '数码物品', 'difficulty': 'medium', 'aliases': ['移动电源'], 'library': 'items'},
 {'word': '遥控器', 'category': '数码物品', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '耳机', 'category': '数码物品', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '相机', 'category': '数码物品', 'difficulty': 'medium', 'aliases': ['照相机'], 'library': 'items'},
 {'word': '打印机', 'category': '数码物品', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '吸尘器', 'category': '家用电器', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '电饭煲', 'category': '家用电器', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '洗衣机', 'category': '家用电器', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '冰箱', 'category': '家用电器', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '微波炉', 'category': '家用电器', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '灭火器', 'category': '公共设施', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '红绿灯', 'category': '公共设施', 'difficulty': 'medium', 'aliases': ['交通灯'], 'library': 'items'},
 {'word': '斑马线', 'category': '公共设施', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '自动扶梯', 'category': '公共设施', 'difficulty': 'medium', 'aliases': ['扶梯'], 'library': 'items'},
 {'word': '电梯', 'category': '公共设施', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '望远镜', 'category': '工具', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '放大镜', 'category': '工具', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '指南针', 'category': '工具', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '锤子', 'category': '工具', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '扳手', 'category': '工具', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '袋鼠', 'category': '动物', 'difficulty': 'medium', 'aliases': [], 'library': 'animals'},
 {'word': '孔雀', 'category': '动物', 'difficulty': 'medium', 'aliases': [], 'library': 'animals'},
 {'word': '啄木鸟', 'category': '动物', 'difficulty': 'medium', 'aliases': [], 'library': 'animals'},
 {'word': '猫头鹰', 'category': '动物', 'difficulty': 'medium', 'aliases': [], 'library': 'animals'},
 {'word': '骆驼', 'category': '动物', 'difficulty': 'medium', 'aliases': [], 'library': 'animals'},
 {'word': '刺猬', 'category': '动物', 'difficulty': 'medium', 'aliases': [], 'library': 'animals'},
 {'word': '松鼠', 'category': '动物', 'difficulty': 'medium', 'aliases': [], 'library': 'animals'},
 {'word': '鳄鱼', 'category': '动物', 'difficulty': 'medium', 'aliases': [], 'library': 'animals'},
 {'word': '鲨鱼', 'category': '动物', 'difficulty': 'medium', 'aliases': [], 'library': 'animals'},
 {'word': '水母', 'category': '动物', 'difficulty': 'medium', 'aliases': [], 'library': 'animals'},
 {'word': '海马', 'category': '动物', 'difficulty': 'medium', 'aliases': [], 'library': 'animals'},
 {'word': '龙虾', 'category': '动物', 'difficulty': 'medium', 'aliases': [], 'library': 'animals'},
 {'word': '鹦鹉', 'category': '动物', 'difficulty': 'medium', 'aliases': [], 'library': 'animals'},
 {'word': '火烈鸟', 'category': '动物', 'difficulty': 'medium', 'aliases': [], 'library': 'animals'},
 {'word': '变色龙', 'category': '动物', 'difficulty': 'medium', 'aliases': [], 'library': 'animals'},
 {'word': '糖葫芦', 'category': '食物', 'difficulty': 'medium', 'aliases': ['冰糖葫芦'], 'library': 'food'},
 {'word': '爆米花', 'category': '食物', 'difficulty': 'medium', 'aliases': [], 'library': 'food'},
 {'word': '棉花糖', 'category': '食物', 'difficulty': 'medium', 'aliases': [], 'library': 'food'},
 {'word': '煎饼果子', 'category': '食物', 'difficulty': 'medium', 'aliases': [], 'library': 'food'},
 {'word': '粽子', 'category': '食物', 'difficulty': 'medium', 'aliases': [], 'library': 'food'},
 {'word': '月饼', 'category': '食物', 'difficulty': 'medium', 'aliases': [], 'library': 'food'},
 {'word': '烤串', 'category': '食物', 'difficulty': 'medium', 'aliases': ['烧烤'], 'library': 'food'},
 {'word': '寿司', 'category': '食物', 'difficulty': 'medium', 'aliases': [], 'library': 'food'},
 {'word': '泡面', 'category': '食物', 'difficulty': 'medium', 'aliases': ['方便面'], 'library': 'food'},
 {'word': '奶茶', 'category': '食物', 'difficulty': 'medium', 'aliases': [], 'library': 'food'},
 {'word': '挖掘机', 'category': '交通工具', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '热气球', 'category': '交通工具', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '缆车', 'category': '交通工具', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '地铁', 'category': '交通工具', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '直升机', 'category': '交通工具', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '潜水艇', 'category': '交通工具', 'difficulty': 'medium', 'aliases': ['潜艇'], 'library': 'places'},
 {'word': '帆船', 'category': '交通工具', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '拖拉机', 'category': '交通工具', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '婴儿车', 'category': '交通工具', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '独轮车', 'category': '交通工具', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '打喷嚏', 'category': '动作', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '打哈欠', 'category': '动作', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '拔河', 'category': '动作', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '放风筝', 'category': '动作', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '堆雪人', 'category': '动作', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '吹蜡烛', 'category': '动作', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '系鞋带', 'category': '动作', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '挤牙膏', 'category': '动作', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '撑雨伞', 'category': '动作', 'difficulty': 'medium', 'aliases': ['打伞'], 'library': 'actions'},
 {'word': '遛狗', 'category': '动作', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '梦游', 'category': '动作', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '迷路', 'category': '动作', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '摔跤', 'category': '动作', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '爬树', 'category': '动作', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '打鼓', 'category': '动作', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '机场', 'category': '地点场景', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '火车站', 'category': '地点场景', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '游乐园', 'category': '地点场景', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '动物园', 'category': '地点场景', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '电影院', 'category': '地点场景', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '菜市场', 'category': '地点场景', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '图书馆', 'category': '地点场景', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '健身房', 'category': '地点场景', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '理发店', 'category': '地点场景', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '加油站', 'category': '地点场景', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '婚礼', 'category': '事件场景', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '生日派对', 'category': '事件场景', 'difficulty': 'medium', 'aliases': ['生日会'], 'library': 'places'},
 {'word': '运动会', 'category': '事件场景', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '毕业典礼', 'category': '事件场景', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '露营', 'category': '事件场景', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '魔术师', 'category': '职业人物', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '摄影师', 'category': '职业人物', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '理发师', 'category': '职业人物', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '潜水员', 'category': '职业人物', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '裁判', 'category': '职业人物', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '牙医', 'category': '职业人物', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '木匠', 'category': '职业人物', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '渔夫', 'category': '职业人物', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '服务员', 'category': '职业人物', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '保安', 'category': '职业人物', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '过山车', 'category': '娱乐运动', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '滑雪', 'category': '娱乐运动', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '冲浪', 'category': '娱乐运动', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '射箭', 'category': '娱乐运动', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '打保龄球', 'category': '娱乐运动', 'difficulty': 'medium', 'aliases': ['保龄球'], 'library': 'actions'},
 {'word': '乒乓球', 'category': '娱乐运动', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '羽毛球', 'category': '娱乐运动', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '跳高', 'category': '娱乐运动', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '举重', 'category': '娱乐运动', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '划船', 'category': '娱乐运动', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '戴墨镜的猫', 'category': '趣味组合', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '会飞的猪', 'category': '趣味组合', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '撑伞的企鹅', 'category': '趣味组合', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '骑自行车的熊猫', 'category': '趣味组合', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '吃西瓜的大象', 'category': '趣味组合', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '掩耳盗铃', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '守株待兔', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '画蛇添足', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '刻舟求剑', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '井底之蛙', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '亡羊补牢', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '狐假虎威', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '鹤立鸡群', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '鸡飞狗跳', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '对牛弹琴', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '杯弓蛇影', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '滥竽充数', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '拔苗助长', 'category': '成语', 'difficulty': 'hard', 'aliases': ['揠苗助长'], 'library': 'fun'},
 {'word': '盲人摸象', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '三心二意', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '火上浇油', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '雪中送炭', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '一箭双雕', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '狼吞虎咽', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '东张西望', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '七上八下', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '手舞足蹈', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '目瞪口呆', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '捧腹大笑', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '泪流满面', 'category': '成语', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '月球漫步', 'category': '想象场景', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '海底城市', 'category': '想象场景', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '天空中的城堡', 'category': '想象场景', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '机器人遛狗', 'category': '想象场景', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '鱼在天上飞', 'category': '想象场景', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '猫开咖啡店', 'category': '想象场景', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '恐龙坐地铁', 'category': '想象场景', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '企鹅卖冰淇淋', 'category': '想象场景', 'difficulty': 'hard', 'aliases': ['企鹅卖冰激凌'], 'library': 'fun'},
 {'word': '外星人打篮球', 'category': '想象场景', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '会走路的房子', 'category': '想象场景', 'difficulty': 'hard', 'aliases': [], 'library': 'fun'},
 {'word': '惊喜派对', 'category': '事件场景', 'difficulty': 'hard', 'aliases': [], 'library': 'places'},
 {'word': '毛巾', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '肥皂', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '洗发水', 'category': '生活用品', 'difficulty': 'easy', 'aliases': ['洗发露'], 'library': 'items'},
 {'word': '沐浴露', 'category': '生活用品', 'difficulty': 'easy', 'aliases': ['沐浴液'], 'library': 'items'},
 {'word': '牙膏', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '脸盆', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '水桶', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '纸巾', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '卫生纸', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '口罩', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '手套', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '围巾', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '袜子', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '雨衣', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '皮带', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '钱包', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '硬币', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '零钱包', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '购物袋', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '垃圾袋', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '保温杯', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '饭盒', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '筷子', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '勺子', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '叉子', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '盘子', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '碗', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '菜刀', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '砧板', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '锅铲', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '平底锅', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '汤锅', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '水壶', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '开瓶器', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '削皮刀', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '漏勺', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '围裙', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '抹布', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '海绵', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '垃圾桶', 'category': '生活用品', 'difficulty': 'easy', 'aliases': ['废纸篓'], 'library': 'items'},
 {'word': '门铃', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '门把手', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '窗帘', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '地毯', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '床单', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '蚊帐', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '抱枕', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '凉席', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '暖水袋', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '指甲刀', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '创可贴', 'category': '生活用品', 'difficulty': 'easy', 'aliases': ['胶布'], 'library': 'items'},
 {'word': '体温计', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '药箱', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '手帕', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '发夹', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '皮筋', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '耳环', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '项链', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '戒指', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '手表', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '领带', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '纽扣', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '拉链', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '安全帽', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '头盔', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '救生圈', 'category': '生活用品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '沙发', 'category': '家具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '椅子', 'category': '家具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '桌子', 'category': '家具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '书架', 'category': '家具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '衣柜', 'category': '家具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '鞋柜', 'category': '家具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '床头柜', 'category': '家具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '茶几', 'category': '家具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '凳子', 'category': '家具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '摇椅', 'category': '家具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '折叠桌', 'category': '家具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '办公桌', 'category': '家具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '婴儿床', 'category': '家具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '屏风', 'category': '家具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '铅笔', 'category': '文具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '橡皮', 'category': '文具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '钢笔', 'category': '文具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '圆珠笔', 'category': '文具', 'difficulty': 'easy', 'aliases': ['原子笔'], 'library': 'items'},
 {'word': '尺子', 'category': '文具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '三角板', 'category': '文具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '圆规', 'category': '文具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '订书机', 'category': '文具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '回形针', 'category': '文具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '文件夹', 'category': '文具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '笔记本', 'category': '文具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '便签纸', 'category': '文具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '胶带', 'category': '文具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '胶水', 'category': '文具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '卷笔刀', 'category': '文具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '印章', 'category': '文具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '信封', 'category': '文具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '明信片', 'category': '文具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '日历', 'category': '文具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '计算器', 'category': '文具', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '手机', 'category': '数码物品', 'difficulty': 'easy', 'aliases': ['电话'], 'library': 'items'},
 {'word': '电脑', 'category': '数码物品', 'difficulty': 'easy', 'aliases': ['计算机'], 'library': 'items'},
 {'word': '平板电脑', 'category': '数码物品', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '键盘', 'category': '数码物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '鼠标', 'category': '数码物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '显示器', 'category': '数码物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '路由器', 'category': '数码物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '数据线', 'category': '数码物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '插线板', 'category': '数码物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': 'U盘', 'category': '数码物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '游戏手柄', 'category': '数码物品', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '麦克风', 'category': '数码物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '音响', 'category': '数码物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '投影仪', 'category': '数码物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '摄像头', 'category': '数码物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '电子书', 'category': '数码物品', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '智能音箱', 'category': '数码物品', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '空调', 'category': '家用电器', 'difficulty': 'easy', 'aliases': ['冷气'], 'library': 'items'},
 {'word': '电视机', 'category': '家用电器', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '烤箱', 'category': '家用电器', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '电磁炉', 'category': '家用电器', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '电吹风', 'category': '家用电器', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '电熨斗', 'category': '家用电器', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '加湿器', 'category': '家用电器', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '空气净化器', 'category': '家用电器', 'difficulty': 'medium', 'aliases': [], 'library': 'items'},
 {'word': '饮水机', 'category': '家用电器', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '热水器', 'category': '家用电器', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '电热毯', 'category': '家用电器', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '榨汁机', 'category': '家用电器', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '咖啡机', 'category': '家用电器', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '洗碗机', 'category': '家用电器', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '电蚊拍', 'category': '家用电器', 'difficulty': 'easy', 'aliases': [], 'library': 'items'},
 {'word': '斑马', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '犀牛', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '河马', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '狐狸', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '狼', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '棕熊', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '北极熊', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '考拉', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '树懒', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '浣熊', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '黄鼠狼', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '鼹鼠', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '豪猪', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '羚羊', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '梅花鹿', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '野猪', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '牦牛', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '山羊', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '绵羊', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '奶牛', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '水牛', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '驴', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '斑点狗', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '哈士奇', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '柯基', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '贵宾犬', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '暹罗猫', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '仓鼠', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '荷兰猪', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '龙猫', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '海豹', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '海狮', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '鲸鱼', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '虎鲸', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '剑鱼', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '飞鱼', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '河豚', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '鳗鱼', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '鲤鱼', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '鲫鱼', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '鲶鱼', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '青蛙', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '蝌蚪', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '壁虎', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '蜥蜴', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '眼镜蛇', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '蟒蛇', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '蚯蚓', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '蚂蚁', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '蚊子', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '苍蝇', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '甲虫', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '瓢虫', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '螳螂', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '萤火虫', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '毛毛虫', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '蜘蛛', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '蝎子', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '蜈蚣', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '鸽子', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '麻雀', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '燕子', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '天鹅', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '丹顶鹤', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '秃鹰', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '喜鹊', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '乌鸦', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '海鸥', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '鸵鸟', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '鹌鹑', 'category': '动物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '玫瑰', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '向日葵', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '荷花', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '菊花', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '郁金香', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '蒲公英', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '薰衣草', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '梅花', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '桃花', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '樱花', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '兰花', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '竹子', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '松树', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '柳树', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '椰子树', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '枫树', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '橡树', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '银杏', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '蘑菇', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '苔藓', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '含羞草', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '捕蝇草', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '四叶草', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '芦荟', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '薄荷', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '水稻', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '小麦', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '玉米', 'category': '植物', 'difficulty': 'easy', 'aliases': ['苞米'], 'library': 'animals'},
 {'word': '棉花', 'category': '植物', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '星星', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '流星', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '瀑布', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '河流', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '湖泊', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '大海', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '沙滩', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '岛屿', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '山峰', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '峡谷', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '沙漠', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '森林', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '草原', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '冰山', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '岩洞', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '泉水', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '露珠', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '龙卷风', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '台风', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '冰雹', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '雾', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '夕阳', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '日出', 'category': '自然', 'difficulty': 'easy', 'aliases': [], 'library': 'animals'},
 {'word': '橙子', 'category': '水果', 'difficulty': 'easy', 'aliases': ['橘橙'], 'library': 'food'},
 {'word': '橘子', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '柠檬', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '梨', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '桃子', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '樱桃', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '菠萝', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '芒果', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '荔枝', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '龙眼', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '榴莲', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '猕猴桃', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '火龙果', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '山竹', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '石榴', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '柚子', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '椰子', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '木瓜', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '哈密瓜', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '蓝莓', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '杨梅', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '柿子', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '甘蔗', 'category': '水果', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '白菜', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '菠菜', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '生菜', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '芹菜', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '香菜', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '西红柿', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': ['番茄'], 'library': 'food'},
 {'word': '黄瓜', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '茄子', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '土豆', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': ['马铃薯'], 'library': 'food'},
 {'word': '红薯', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': ['地瓜'], 'library': 'food'},
 {'word': '南瓜', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '冬瓜', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '萝卜', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '胡萝卜', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '西兰花', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '菜花', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '洋葱', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '大蒜', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '辣椒', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '青椒', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '豆角', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '莲藕', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '竹笋', 'category': '蔬菜', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '米饭', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '炒饭', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '馒头', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '包子', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': ['肉包'], 'library': 'food'},
 {'word': '烧麦', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '馄饨', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': ['云吞'], 'library': 'food'},
 {'word': '米线', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': ['米粉'], 'library': 'food'},
 {'word': '凉皮', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '肉夹馍', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '油条', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '豆浆', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '小笼包', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '春卷', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '锅贴', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '年糕', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '汤圆', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '凉面', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '炒面', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '意大利面', 'category': '主食小吃', 'difficulty': 'medium', 'aliases': [], 'library': 'food'},
 {'word': '三明治', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '薯条', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '鸡翅', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '烤鸭', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '炸鸡', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '牛排', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '烤鱼', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '麻辣烫', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '螺蛳粉', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '酸辣粉', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '臭豆腐', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '章鱼烧', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '蛋挞', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '曲奇', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '饼干', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '巧克力', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '布丁', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '果冻', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '甜甜圈', 'category': '主食小吃', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '矿泉水', 'category': '饮品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '果汁', 'category': '饮品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '橙汁', 'category': '饮品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '可乐', 'category': '饮品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '汽水', 'category': '饮品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '咖啡', 'category': '饮品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '绿茶', 'category': '饮品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '红茶', 'category': '饮品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '酸奶', 'category': '饮品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '牛奶', 'category': '饮品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '豆奶', 'category': '饮品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '柠檬茶', 'category': '饮品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '椰汁', 'category': '饮品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '热可可', 'category': '饮品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '冰沙', 'category': '饮品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '盐', 'category': '调味品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '白糖', 'category': '调味品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '酱油', 'category': '调味品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '醋', 'category': '调味品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '蜂蜜', 'category': '调味品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '番茄酱', 'category': '调味品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '辣椒酱', 'category': '调味品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '胡椒粉', 'category': '调味品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '芝麻油', 'category': '调味品', 'difficulty': 'easy', 'aliases': [], 'library': 'food'},
 {'word': '走路', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '散步', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '冲刺', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '蹲下', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '起跳', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '转圈', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '挥手', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '鼓掌', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '拥抱', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '握手', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '敬礼', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '眨眼', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '微笑', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '皱眉', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '发呆', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '思考', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '读书', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '写字', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '画画', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '做饭', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '洗碗', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '扫地', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '拖地', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '洗衣服', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '晾衣服', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '叠被子', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '穿鞋', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '脱帽', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '开门', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '关窗', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '开锁', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '打电话', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '发短信', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '敲键盘', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '玩手机', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '自拍', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '录像', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '吹口哨', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '弹吉他', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '弹钢琴', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '拉小提琴', 'category': '动作', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '吹笛子', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '敲锣', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '骑马', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '骑车', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '爬山', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '攀岩', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '滑冰', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '跳远', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '投篮', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '射门', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '发球', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '扣球', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '潜水', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '放烟花', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '包饺子', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '切西瓜', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '剥香蕉', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '挖土', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '浇花', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '喂鱼', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '遛鸟', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '抓蝴蝶', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '捉迷藏', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '荡秋千', 'category': '动作', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '坐跷跷板', 'category': '动作', 'difficulty': 'medium', 'aliases': [], 'library': 'actions'},
 {'word': '护士', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '律师', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '记者', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '演员', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '歌手', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '舞蹈家', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '运动员', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '程序员', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '工程师', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '科学家', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '邮递员', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '售货员', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '导游', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '飞行员', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '列车员', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '船长', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '园丁', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '裁缝', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '钟表匠', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '面包师', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '主持人', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '设计师', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '建筑师', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '翻译', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '作家', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '漫画家', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '兽医', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '药剂师', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '交警', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '清洁工', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '电工', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '修理工', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '焊工', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '矿工', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '牧民', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '猎人', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '花匠', 'category': '职业', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '开心', 'category': '情绪表情', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '生气', 'category': '情绪表情', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '害怕', 'category': '情绪表情', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '紧张', 'category': '情绪表情', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '惊讶', 'category': '情绪表情', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '害羞', 'category': '情绪表情', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '伤心', 'category': '情绪表情', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '委屈', 'category': '情绪表情', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '骄傲', 'category': '情绪表情', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '困倦', 'category': '情绪表情', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '发愁', 'category': '情绪表情', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '羡慕', 'category': '情绪表情', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '疑惑', 'category': '情绪表情', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '尴尬', 'category': '情绪表情', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '兴奋', 'category': '情绪表情', 'difficulty': 'easy', 'aliases': [], 'library': 'actions'},
 {'word': '轿车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '卡车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '货车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '校车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '警车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '垃圾车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '洒水车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '压路机', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '推土机', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '叉车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '吊车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '房车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '赛车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '越野车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '三轮车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '轮椅', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '雪橇', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '游艇', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '皮划艇', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '橡皮艇', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '渡轮', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '邮轮', 'category': '交通工具', 'difficulty': 'easy', 'aliases': ['游轮'], 'library': 'places'},
 {'word': '高铁', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '有轨电车', 'category': '交通工具', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '索道', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '电动车', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '共享单车', 'category': '交通工具', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '降落伞', 'category': '交通工具', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '航天飞机', 'category': '交通工具', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '学校', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '教室', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '食堂', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '宿舍', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '医院', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '银行', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '邮局', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '超市', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '商场', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '餐厅', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '咖啡馆', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '面包店', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '药店', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '花店', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '书店', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '文具店', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '警察局', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '消防站', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '体育馆', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '游泳馆', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '博物馆', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '美术馆', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '科技馆', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '水族馆', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '植物园', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '公园', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '广场', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '停车场', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '公交站', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '地铁站', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '港口', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '码头', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '灯塔', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '海滩', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '山顶', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '农场', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '果园', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '工厂', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '建筑工地', 'category': '地点', 'difficulty': 'medium', 'aliases': [], 'library': 'places'},
 {'word': '电视台', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '录音棚', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '法庭', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '婚纱店', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '酒店', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '民宿', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '厨房', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '浴室', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '阳台', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '客厅', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '卧室', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '地下室', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '屋顶', 'category': '地点', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '路灯', 'category': '设施', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '公交牌', 'category': '设施', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '收费站', 'category': '设施', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '电话亭', 'category': '设施', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '邮筒', 'category': '设施', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '喷泉', 'category': '设施', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '长椅', 'category': '设施', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '垃圾箱', 'category': '设施', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '售货机', 'category': '设施', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '旋转门', 'category': '设施', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '天桥', 'category': '设施', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '隧道', 'category': '设施', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '高架桥', 'category': '设施', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '铁轨', 'category': '设施', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '跑道', 'category': '设施', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '站台', 'category': '设施', 'difficulty': 'easy', 'aliases': [], 'library': 'places'},
 {'word': '黑板', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '粉笔', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '讲台', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '课桌', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '校服', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '校徽', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '红领巾', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '毕业帽', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '学生证', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '饭卡', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '借书证', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '成绩单', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '试卷', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '答题卡', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '草稿纸', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '课程表', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '值日表', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '奖状', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '奖杯', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '实验服', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '护目镜', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '试管', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '烧杯', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '量筒', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '显微镜', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '天平', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '地球仪', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '算盘', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '粉笔擦', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '扩音器', 'category': '校园物品', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '学生', 'category': '校园人物', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '班长', 'category': '校园人物', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '同桌', 'category': '校园人物', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '室友', 'category': '校园人物', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '校长', 'category': '校园人物', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '教授', 'category': '校园人物', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '辅导员', 'category': '校园人物', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '班主任', 'category': '校园人物', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '研究生', 'category': '校园人物', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '本科生', 'category': '校园人物', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '留学生', 'category': '校园人物', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '学霸', 'category': '校园人物', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '体育老师', 'category': '校园人物', 'difficulty': 'medium', 'aliases': [], 'library': 'campus'},
 {'word': '音乐老师', 'category': '校园人物', 'difficulty': 'medium', 'aliases': [], 'library': 'campus'},
 {'word': '门卫', 'category': '校园人物', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '语文', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '数学', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '英语', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '物理', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '化学', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '生物', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '历史', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '地理', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '音乐', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '美术', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '体育', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '考试', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '作业', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '作文', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '背诵', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '复习', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '预习', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '阅读', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '听写', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '默写', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '实验', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '论文', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '答辩', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '毕业', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '开学', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '放假', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '迟到', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '早退', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '请假', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '补考', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '奖学金', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '图书证', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '自习', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '选课', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '社团', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '校庆', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '辩论赛', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '演讲', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '军训', 'category': '学习词汇', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '实验室', 'category': '校园地点', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '自习室', 'category': '校园地点', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '阅览室', 'category': '校园地点', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '报告厅', 'category': '校园地点', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '礼堂', 'category': '校园地点', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '操场', 'category': '校园地点', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '篮球场', 'category': '校园地点', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '足球场', 'category': '校园地点', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '校医院', 'category': '校园地点', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '打印店', 'category': '校园地点', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '快递站', 'category': '校园地点', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '宿管室', 'category': '校园地点', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '教学楼', 'category': '校园地点', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '办公楼', 'category': '校园地点', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '钟楼', 'category': '校园地点', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '校门', 'category': '校园地点', 'difficulty': 'easy', 'aliases': [], 'library': 'campus'},
 {'word': '一心一意', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '五花八门', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '九牛一毛', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '百发百中', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '画龙点睛', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '鱼目混珠', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '虎头蛇尾', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '鸟语花香', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '龙飞凤舞', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '马到成功', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '猴年马月', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '狗急跳墙', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '猫哭老鼠', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '如鱼得水', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '顺手牵羊', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '呆若木鸡', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '胆小如鼠', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '力大如牛', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '汗流浃背', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '大吃一惊', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '眉开眼笑', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '垂头丧气', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '怒发冲冠', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '抓耳挠腮', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '一瘸一拐', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '蹑手蹑脚', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '左顾右盼', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '手忙脚乱', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '昂首挺胸', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '摇头晃脑', 'category': '成语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '熊猫骑自行车', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '猫咪打雨伞', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '小狗戴墨镜', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '兔子开汽车', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '猴子拍照片', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '乌龟坐火箭', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '章鱼打鼓', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '老虎吃火锅', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '长颈鹿喝奶茶', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '大象放风筝', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '狐狸看电视', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '河马跳芭蕾', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '外星人踢足球', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '机器人做饭', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '鲨鱼刷牙', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '狮子理发', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '青蛙开会', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '蜗牛送快递', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '北极熊冲浪', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '松鼠打篮球', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '螃蟹弹钢琴', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '鸭子滑雪', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '猪在天上飞', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '鱼骑自行车', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '猫开面包店', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '狗当宇航员', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '兔子变魔术', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'},
 {'word': '熊猫吃西瓜', 'category': '趣味短语', 'difficulty': 'medium', 'aliases': [], 'library': 'fun'}]

def fresh_draw():
    return {
        "drawerId": None,
        "turnIndex": 0,
        "totalTurns": 0,
        "choices": [],
        "word": "",
        "aliases": [],
        "category": "",
        "difficulty": "",
        "activeLibrary": "items",
        "deadline": 0.0,
        "chooseDeadline": 0.0,
        "strokes": [],
        "strokeSeq": 0,
        "canvasRevision": 0,
        "guesses": [],
        "correctIds": [],
        "usedWords": [],
        "answer": "",
        "result": "",
    }

DDZ_RANK_VALUE = {
    "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
    "10": 10, "J": 11, "Q": 12, "K": 13, "A": 14, "2": 15,
    "BJ": 16, "RJ": 17,
}
DDZ_VALUE_RANK = {value: rank for rank, value in DDZ_RANK_VALUE.items()}
DDZ_COMBO_LABELS = {
    "single": "单张", "pair": "对子", "triple": "三张",
    "triple_single": "三带一", "triple_pair": "三带二",
    "straight": "顺子", "pair_straight": "连对",
    "plane": "飞机", "plane_single": "飞机带单",
    "plane_pair": "飞机带对", "four_two_single": "四带二",
    "four_two_pair": "四带两对", "bomb": "炸弹", "rocket": "王炸",
}

def fresh_ddz():
    return {
        "bottom": [],
        "highestBid": 0,
        "highestBidder": None,
        "bidCount": 0,
        "bidHistory": [],
        "landlordId": None,
        "lastPlay": None,
        "trickLeaderId": None,
        "passCount": 0,
        "baseBid": 0,
        "multiplier": 1,
        "bombCount": 0,
        "landlordPlayCount": 0,
        "farmerPlayCount": 0,
        "message": "",
        "botDueAt": 0.0,
        "botActionCount": 0,
    }

def ddz_deck():
    cards = []
    for suit in ("S", "H", "C", "D"):
        for rank in ("3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2"):
            cards.append({
                "id": "d_" + secrets.token_hex(5),
                "rank": rank,
                "suit": suit,
                "value": DDZ_RANK_VALUE[rank],
            })
    cards.append({"id": "d_" + secrets.token_hex(5), "rank": "BJ", "suit": "J", "value": 16})
    cards.append({"id": "d_" + secrets.token_hex(5), "rank": "RJ", "suit": "J", "value": 17})
    random.SystemRandom().shuffle(cards)
    return cards

def sort_ddz_hand(cards):
    suit_order = {"S": 0, "H": 1, "C": 2, "D": 3, "J": 4}
    cards.sort(key=lambda c: (c["value"], suit_order.get(c["suit"], 9)))

def ddz_consecutive(values):
    values = sorted(values)
    return bool(values) and values[-1] <= 14 and all(b == a + 1 for a, b in zip(values, values[1:]))

def classify_ddz(cards):
    if not cards:
        return None
    values = [int(card["value"]) for card in cards]
    counts = Counter(values)
    n = len(values)
    unique = sorted(counts)
    count_values = sorted(counts.values())

    def result(kind, main, chain=1):
        return {
            "type": kind,
            "main": int(main),
            "size": n,
            "chain": int(chain),
            "label": DDZ_COMBO_LABELS[kind],
        }

    if n == 2 and set(values) == {16, 17}:
        return result("rocket", 17)
    if n == 4 and len(counts) == 1:
        return result("bomb", unique[0])
    if n == 1:
        return result("single", values[0])
    if n == 2 and len(counts) == 1:
        return result("pair", unique[0])
    if n == 3 and len(counts) == 1:
        return result("triple", unique[0])
    if n == 4 and count_values == [1, 3]:
        return result("triple_single", next(v for v, c in counts.items() if c == 3))
    if n == 5 and count_values == [2, 3]:
        return result("triple_pair", next(v for v, c in counts.items() if c == 3))

    if n >= 5 and len(counts) == n and ddz_consecutive(unique):
        return result("straight", unique[-1], len(unique))
    if n >= 6 and n % 2 == 0 and all(c == 2 for c in counts.values()) and len(unique) >= 3 and ddz_consecutive(unique):
        return result("pair_straight", unique[-1], len(unique))
    if n >= 6 and n % 3 == 0 and all(c == 3 for c in counts.values()) and len(unique) >= 2 and ddz_consecutive(unique):
        return result("plane", unique[-1], len(unique))

    if n >= 8 and n % 4 == 0:
        chain = n // 4
        triple_values = sorted(v for v, c in counts.items() if c == 3 and v <= 14)
        for start in range(0, len(triple_values) - chain + 1):
            body = triple_values[start:start + chain]
            if len(body) == chain and ddz_consecutive(body):
                remaining = n - 3 * chain
                if remaining == chain:
                    return result("plane_single", body[-1], chain)

    if n >= 10 and n % 5 == 0:
        chain = n // 5
        triple_values = sorted(v for v, c in counts.items() if c == 3 and v <= 14)
        for start in range(0, len(triple_values) - chain + 1):
            body = triple_values[start:start + chain]
            if len(body) != chain or not ddz_consecutive(body):
                continue
            rest = {v: c for v, c in counts.items() if v not in body}
            if len(rest) == chain and all(c == 2 for c in rest.values()):
                return result("plane_pair", body[-1], chain)

    if n == 6 and 4 in counts.values():
        return result("four_two_single", next(v for v, c in counts.items() if c == 4))
    if n == 8 and 4 in counts.values():
        bomb_value = next(v for v, c in counts.items() if c == 4)
        rest = [c for v, c in counts.items() if v != bomb_value]
        if len(rest) == 2 and all(c == 2 for c in rest):
            return result("four_two_pair", bomb_value)
    return None

def ddz_beats(candidate, previous):
    if not candidate:
        return False
    if not previous:
        return True
    if candidate["type"] == "rocket":
        return previous["type"] != "rocket"
    if previous["type"] == "rocket":
        return False
    if candidate["type"] == "bomb":
        if previous["type"] != "bomb":
            return True
        return candidate["main"] > previous["main"]
    if previous["type"] == "bomb":
        return False
    return (
        candidate["type"] == previous["type"]
        and candidate["size"] == previous["size"]
        and candidate.get("chain", 1) == previous.get("chain", 1)
        and candidate["main"] > previous["main"]
    )

def ddz_groups(hand):
    groups = {}
    for card in sorted(hand, key=lambda c: (c["value"], c["suit"])):
        groups.setdefault(card["value"], []).append(card)
    return groups

def ddz_run_candidates(groups, chain, copies):
    results = []
    values = sorted(v for v, cards in groups.items() if v <= 14 and len(cards) >= copies)
    for start in range(3, 15 - chain + 1):
        seq = list(range(start, start + chain))
        if all(v in values for v in seq):
            cards = []
            for v in seq:
                cards.extend(groups[v][:copies])
            results.append(cards)
    return results

def ddz_hint_options(hand, previous):
    groups = ddz_groups(hand)
    options = []
    seen = set()

    def add(cards):
        if not cards:
            return
        combo = classify_ddz(cards)
        if not combo or not ddz_beats(combo, previous):
            return
        key = tuple(sorted(card["id"] for card in cards))
        if key not in seen:
            seen.add(key)
            options.append(cards)

    if not previous:
        add(hand)
        for value in sorted(groups):
            add(groups[value][:1])
        for value in sorted(groups):
            if len(groups[value]) >= 2:
                add(groups[value][:2])
        for value in sorted(groups):
            if len(groups[value]) >= 3:
                add(groups[value][:3])
        for chain in range(5, 13):
            candidates = ddz_run_candidates(groups, chain, 1)
            if candidates:
                add(candidates[0])
                break
        for chain in range(3, 7):
            candidates = ddz_run_candidates(groups, chain, 2)
            if candidates:
                add(candidates[0])
                break
        for value in sorted(groups):
            if len(groups[value]) == 4:
                add(groups[value][:4])
        if 16 in groups and 17 in groups:
            add(groups[16][:1] + groups[17][:1])
        return options[:24]

    kind = previous["type"]
    main = previous["main"]
    chain = previous.get("chain", 1)

    if kind == "single":
        for v in sorted(groups):
            if v > main:
                add(groups[v][:1])
    elif kind == "pair":
        for v in sorted(groups):
            if v > main and len(groups[v]) >= 2:
                add(groups[v][:2])
    elif kind == "triple":
        for v in sorted(groups):
            if v > main and len(groups[v]) >= 3:
                add(groups[v][:3])
    elif kind in ("triple_single", "triple_pair"):
        for v in sorted(groups):
            if v <= main or len(groups[v]) < 3:
                continue
            if kind == "triple_single":
                wing = next((cards[0] for w, cards in sorted(groups.items()) if w != v and cards), None)
                if wing:
                    add(groups[v][:3] + [wing])
            else:
                wing = next((cards[:2] for w, cards in sorted(groups.items()) if w != v and len(cards) >= 2), None)
                if wing:
                    add(groups[v][:3] + wing)
    elif kind == "straight":
        for cards in ddz_run_candidates(groups, chain, 1):
            if max(c["value"] for c in cards) > main:
                add(cards)
    elif kind == "pair_straight":
        for cards in ddz_run_candidates(groups, chain, 2):
            if max(c["value"] for c in cards) > main:
                add(cards)
    elif kind in ("plane", "plane_single", "plane_pair"):
        for body in ddz_run_candidates(groups, chain, 3):
            body_values = {c["value"] for c in body}
            if max(body_values) <= main:
                continue
            remaining = [c for c in hand if c["value"] not in body_values]
            if kind == "plane":
                add(body)
            elif kind == "plane_single" and len(remaining) >= chain:
                add(body + remaining[:chain])
            elif kind == "plane_pair":
                pair_cards = []
                for v, cards in sorted(ddz_groups(remaining).items()):
                    if len(cards) >= 2:
                        pair_cards.extend(cards[:2])
                        if len(pair_cards) == chain * 2:
                            break
                if len(pair_cards) == chain * 2:
                    add(body + pair_cards)
    elif kind == "four_two_single":
        for v in sorted(groups):
            if v > main and len(groups[v]) == 4:
                remaining = [c for c in hand if c["value"] != v]
                if len(remaining) >= 2:
                    add(groups[v][:4] + remaining[:2])
    elif kind == "four_two_pair":
        for v in sorted(groups):
            if v > main and len(groups[v]) == 4:
                pairs = []
                for w, cards in sorted(groups.items()):
                    if w != v and len(cards) >= 2:
                        pairs.extend(cards[:2])
                        if len(pairs) == 4:
                            break
                if len(pairs) == 4:
                    add(groups[v][:4] + pairs)
    elif kind == "bomb":
        for v in sorted(groups):
            if v > main and len(groups[v]) == 4:
                add(groups[v][:4])

    if kind not in ("bomb", "rocket"):
        for v in sorted(groups):
            if len(groups[v]) == 4:
                add(groups[v][:4])
    if kind != "rocket" and 16 in groups and 17 in groups:
        add(groups[16][:1] + groups[17][:1])
    return options[:32]

def ddz_lead_options(hand):
    """Generate practical lead candidates, preferring combinations that shed cards."""
    groups = ddz_groups(hand)
    options = []
    seen = set()

    def add(cards):
        if not cards:
            return
        combo = classify_ddz(cards)
        if not combo:
            return
        key = tuple(sorted(card["id"] for card in cards))
        if key not in seen:
            seen.add(key)
            options.append(cards)

    # If the whole hand is one legal combination, always include it first.
    add(list(hand))
    # Long structures first: planes, pair runs, straights.
    for chain in range(6, 1, -1):
        for body in ddz_run_candidates(groups, chain, 3):
            add(body)
    for chain in range(6, 2, -1):
        for run in ddz_run_candidates(groups, chain, 2):
            add(run)
    for chain in range(12, 4, -1):
        for run in ddz_run_candidates(groups, chain, 1):
            add(run)
    # Triples with attachments, then triples/pairs/singles.
    for value in sorted(groups):
        if len(groups[value]) >= 3:
            remaining = [c for c in hand if c["value"] != value]
            pair = next((cards[:2] for _, cards in sorted(ddz_groups(remaining).items()) if len(cards) >= 2), None)
            if pair:
                add(groups[value][:3] + pair)
            if remaining:
                add(groups[value][:3] + [remaining[0]])
            add(groups[value][:3])
    for value in sorted(groups):
        if len(groups[value]) >= 2:
            add(groups[value][:2])
    for value in sorted(groups):
        add(groups[value][:1])
    # Bombs and rocket last.
    for value in sorted(groups):
        if len(groups[value]) == 4:
            add(groups[value][:4])
    if 16 in groups and 17 in groups:
        add(groups[16][:1] + groups[17][:1])
    return options

def ddz_combo_cost(cards):
    combo = classify_ddz(cards) or {"type": "invalid", "main": 99}
    type_penalty = {
        "plane_pair": 0, "plane_single": 1, "plane": 2,
        "pair_straight": 3, "straight": 4,
        "triple_pair": 5, "triple_single": 6, "triple": 7,
        "pair": 8, "single": 9, "four_two_pair": 10,
        "four_two_single": 11, "bomb": 40, "rocket": 60,
    }.get(combo["type"], 20)
    high_penalty = sum(max(0, card["value"] - 12) for card in cards)
    # More cards shed is good, except bombs/rocket which remain expensive.
    shed_bonus = len(cards) * 2 if combo["type"] not in ("bomb", "rocket") else 0
    return type_penalty * 100 + combo.get("main", 99) * 3 + high_penalty * 4 - shed_bonus

def ddz_hand_strength(hand):
    groups = ddz_groups(hand)
    score = 0
    if 16 in groups:
        score += 3
    if 17 in groups:
        score += 4
    if 16 in groups and 17 in groups:
        score += 5
    score += len(groups.get(15, [])) * 2.5
    score += len(groups.get(14, [])) * 1.2
    score += sum(6 for cards in groups.values() if len(cards) == 4)
    score += sum(2.2 for cards in groups.values() if len(cards) == 3)
    # Reward long runs because the hand is easier to shed.
    score += max((len(run) for run in ddz_run_candidates(groups, 5, 1)), default=0) * 0.25
    return score

def schedule_ddz_bot(delay=0.85):
    ddz = STATE.get("ddz", {})
    current = player_by_id(STATE.get("turnPlayerId"))
    if STATE.get("mode") == "ddz" and STATE.get("phase") in ("ddz_bidding", "ddz_play") and current and current.get("isBot"):
        ddz["botDueAt"] = time.time() + delay
    else:
        ddz["botDueAt"] = 0.0

def apply_ddz_bid(player, score):
    ddz = STATE["ddz"]
    score = int(score)
    if score not in (0, 1, 2, 3):
        return {"error": "叫分无效"}, 400
    if score and score <= ddz["highestBid"]:
        return {"error": "叫分必须高于当前最高分"}, 409
    ddz["bidHistory"].append({"playerId": player["id"], "playerName": player["name"], "score": score})
    ddz["bidCount"] += 1
    if score > ddz["highestBid"]:
        ddz["highestBid"] = score
        ddz["highestBidder"] = player["id"]
    if score == 3:
        finalize_ddz_landlord()
        return {}, 200
    if ddz["bidCount"] >= 3:
        if not ddz["highestBidder"]:
            deal_ddz("无人叫地主，已重新发牌")
        else:
            finalize_ddz_landlord()
        return {}, 200
    STATE["turnPlayerId"] = next_seat_id(player["id"])
    ddz["message"] = f"{player['name']} " + (f"叫 {score} 分" if score else "不叫")
    bump()
    schedule_ddz_bot()
    return {}, 200

def apply_ddz_play(player, selected):
    combo = classify_ddz(selected)
    if not combo:
        return {"error": "这组牌不是合法斗地主牌型"}, 409
    ddz = STATE["ddz"]
    previous = ddz["lastPlay"]["combo"] if ddz["lastPlay"] else None
    if not ddz_beats(combo, previous):
        return {"error": "这手牌压不过上一手"}, 409
    selected_ids = {card["id"] for card in selected}
    player["ddzHand"] = [card for card in player["ddzHand"] if card["id"] not in selected_ids]
    ddz["lastPlay"] = {
        "playerId": player["id"], "playerName": player["name"],
        "cards": selected, "combo": combo,
    }
    ddz["trickLeaderId"] = player["id"]
    ddz["passCount"] = 0
    ddz["message"] = f"{player['name']} 出了 {combo['label']}"
    if combo["type"] in ("bomb", "rocket"):
        ddz["multiplier"] *= 2
        ddz["bombCount"] += 1
    if player["id"] == ddz["landlordId"]:
        ddz["landlordPlayCount"] += 1
    else:
        ddz["farmerPlayCount"] += 1
    player["ddzHintCursor"] = 0
    if not player["ddzHand"]:
        finish_ddz(player["id"])
        return {}, 200
    STATE["turnPlayerId"] = next_seat_id(player["id"])
    bump()
    schedule_ddz_bot()
    return {}, 200

def apply_ddz_pass(player):
    ddz = STATE["ddz"]
    if not ddz["lastPlay"]:
        return {"error": "你是本轮首家，必须出牌"}, 409
    ddz["passCount"] += 1
    ddz["message"] = f"{player['name']} 不出"
    player["ddzHintCursor"] = 0
    if ddz["passCount"] >= 2:
        STATE["turnPlayerId"] = ddz["trickLeaderId"]
        ddz["lastPlay"] = None
        ddz["passCount"] = 0
        ddz["message"] = "其余两家都不出，重新领出"
    else:
        STATE["turnPlayerId"] = next_seat_id(player["id"])
    bump()
    schedule_ddz_bot()
    return {}, 200

def choose_ddz_bot_bid(player):
    ddz = STATE["ddz"]
    strength = ddz_hand_strength(player["ddzHand"])
    target = 3 if strength >= 20 else 2 if strength >= 13 else 1 if strength >= 7 else 0
    if target <= ddz["highestBid"]:
        target = 0
    # Avoid endless redeals: the final bidder calls one with a merely playable hand.
    if ddz["bidCount"] == 2 and not ddz["highestBidder"] and target == 0:
        target = 1
    return target

def choose_ddz_bot_play(player):
    ddz = STATE["ddz"]
    previous_record = ddz.get("lastPlay")
    previous = previous_record["combo"] if previous_record else None
    hand = player["ddzHand"]
    whole = classify_ddz(hand)
    if whole and ddz_beats(whole, previous):
        return list(hand)

    options = ddz_hint_options(hand, previous) if previous else ddz_lead_options(hand)
    if not options:
        return None

    landlord_id = ddz.get("landlordId")
    is_landlord = player["id"] == landlord_id
    previous_player = player_by_id(previous_record["playerId"]) if previous_record else None
    opponents = [p for p in STATE["players"] if (p["id"] != player["id"] and ((is_landlord and p["id"] != landlord_id) or (not is_landlord and p["id"] == landlord_id)))]
    danger = any(len(p.get("ddzHand", [])) <= 2 for p in opponents)

    # Farmer coordination: normally do not overtake the other farmer.
    if not is_landlord and previous_player and previous_player["id"] != landlord_id:
        finishing = [cards for cards in options if len(cards) == len(hand)]
        if finishing:
            return min(finishing, key=ddz_combo_cost)
        return None

    non_bombs = [cards for cards in options if classify_ddz(cards)["type"] not in ("bomb", "rocket")]
    pool = options if danger or not non_bombs else non_bombs
    # When leading, prefer shedding more cards; when following, prefer cheapest valid response.
    if previous is None:
        return min(pool, key=lambda cards: (ddz_combo_cost(cards), -len(cards)))
    return min(pool, key=ddz_combo_cost)

def ddz_bot_step():
    if STATE.get("mode") != "ddz" or STATE.get("phase") not in ("ddz_bidding", "ddz_play"):
        return False
    player = player_by_id(STATE.get("turnPlayerId"))
    if not player or not player.get("isBot"):
        return False
    ddz = STATE["ddz"]
    if time.time() < float(ddz.get("botDueAt", 0.0)):
        return False
    ddz["botDueAt"] = 0.0
    ddz["botActionCount"] = int(ddz.get("botActionCount", 0)) + 1
    if STATE["phase"] == "ddz_bidding":
        apply_ddz_bid(player, choose_ddz_bot_bid(player))
    else:
        cards = choose_ddz_bot_play(player)
        if cards:
            apply_ddz_play(player, cards)
        else:
            apply_ddz_pass(player)
    return True

def next_seat_id(current_id):
    players = STATE["players"]
    if not players:
        return None
    ids = [p["id"] for p in players]
    try:
        index = ids.index(current_id)
    except ValueError:
        index = -1
    return ids[(index + 1) % len(ids)]

def deal_ddz(message=""):
    deck = ddz_deck()
    for player in STATE["players"]:
        player["ddzHand"] = []
        player["ddzHintCursor"] = 0
    for _ in range(17):
        for player in STATE["players"]:
            player["ddzHand"].append(deck.pop())
    for player in STATE["players"]:
        sort_ddz_hand(player["ddzHand"])
    STATE["ddz"] = fresh_ddz()
    STATE["ddz"]["bottom"] = deck
    STATE["ddz"]["message"] = message
    starter = random.SystemRandom().choice(STATE["players"])
    STATE["phase"] = "ddz_bidding"
    STATE["turnPlayerId"] = starter["id"]
    STATE["roundNo"] += 1
    bump()
    schedule_ddz_bot()

def finalize_ddz_landlord():
    ddz = STATE["ddz"]
    landlord = player_by_id(ddz["highestBidder"])
    if not landlord:
        deal_ddz("无人叫地主，已重新发牌")
        return
    landlord["ddzHand"].extend(ddz["bottom"])
    sort_ddz_hand(landlord["ddzHand"])
    ddz["landlordId"] = landlord["id"]
    ddz["baseBid"] = max(1, ddz["highestBid"])
    ddz["lastPlay"] = None
    ddz["trickLeaderId"] = landlord["id"]
    ddz["passCount"] = 0
    ddz["message"] = f"{landlord['name']} 成为地主"
    STATE["phase"] = "ddz_play"
    STATE["turnPlayerId"] = landlord["id"]
    bump()
    schedule_ddz_bot()

def finish_ddz(winner_id):
    ddz = STATE["ddz"]
    landlord_id = ddz["landlordId"]
    landlord_win = winner_id == landlord_id
    spring = False
    if landlord_win and ddz["farmerPlayCount"] == 0:
        spring = True
    elif not landlord_win and ddz["landlordPlayCount"] == 1:
        spring = True
    if spring:
        ddz["multiplier"] *= 2
    unit = max(1, ddz["baseBid"]) * ddz["multiplier"]
    landlord = player_by_id(landlord_id)
    farmers = [p for p in STATE["players"] if p["id"] != landlord_id]
    if landlord_win:
        landlord["ddzScore"] += 2 * unit
        for farmer in farmers:
            farmer["ddzScore"] -= unit
        result = f"地主 {landlord['name']} 获胜"
        STATE["winnerId"] = landlord_id
    else:
        landlord["ddzScore"] -= 2 * unit
        for farmer in farmers:
            farmer["ddzScore"] += unit
        result = "农民 " + "、".join(p["name"] for p in farmers) + " 获胜"
        STATE["winnerId"] = farmers[0]["id"]
    if spring:
        result += " · " + ("春天" if landlord_win else "反春天")
    result += f" · {ddz['baseBid']}分 × {ddz['multiplier']}倍 = {unit}分"
    STATE["roundResult"] = result
    STATE["phase"] = "finished"
    STATE["turnPlayerId"] = None
    bump()

def ddz_public(player_id):
    ddz = STATE["ddz"]
    landlord = player_by_id(ddz.get("landlordId"))
    last = ddz.get("lastPlay")
    return {
        "highestBid": ddz.get("highestBid", 0),
        "bidHistory": list(ddz.get("bidHistory", [])),
        "landlordId": ddz.get("landlordId"),
        "landlordName": landlord["name"] if landlord else "",
        "baseBid": ddz.get("baseBid", 0),
        "multiplier": ddz.get("multiplier", 1),
        "message": ddz.get("message", ""),
        "botThinking": bool((player_by_id(STATE.get("turnPlayerId")) or {}).get("isBot")) and STATE.get("phase") in ("ddz_bidding", "ddz_play"),
        "bottomCards": list(ddz.get("bottom", [])) if ddz.get("landlordId") else [],
        "lastPlay": {
            "playerId": last["playerId"],
            "playerName": last["playerName"],
            "cards": list(last["cards"]),
            "comboLabel": last["combo"]["label"],
        } if last else None,
    }

CM_SUITS = ("W", "T", "B")
CM_SUIT_LABEL = {"W": "万", "T": "筒", "B": "条"}


def fresh_chuanma():
    return {
        "wall": [],
        "dealerId": None,
        "exchangeDirection": "",
        "exchangeSelections": {},
        "dingqueSelections": {},
        "discardPile": [],
        "lastDiscard": None,
        "needsDiscard": False,
        "responseOptions": {},
        "responses": {},
        "responseDeadline": 0.0,
        "discarderId": None,
        "message": "",
        "winRecords": [],
    }


def cm_tile_key(tile):
    return (CM_SUITS.index(tile["suit"]), int(tile["rank"]))


def sort_cm_hand(cards):
    cards.sort(key=cm_tile_key)


def cm_deck():
    cards = []
    for suit in CM_SUITS:
        for rank in range(1, 10):
            for _ in range(4):
                cards.append({"id": "m_" + secrets.token_hex(5), "suit": suit, "rank": rank})
    random.SystemRandom().shuffle(cards)
    return cards


def cm_same(tile, other):
    return tile["suit"] == other["suit"] and int(tile["rank"]) == int(other["rank"])


def cm_counts(cards):
    counts = Counter()
    for tile in cards:
        counts[(tile["suit"], int(tile["rank"]))] += 1
    return counts


def cm_standard_win(cards):
    if len(cards) % 3 != 2:
        return False
    counts = cm_counts(cards)

    def consume_sets(local):
        remaining = [key for key, count in local.items() if count > 0]
        if not remaining:
            return True
        suit, rank = min(remaining, key=lambda item: (CM_SUITS.index(item[0]), item[1]))
        if local[(suit, rank)] >= 3:
            local[(suit, rank)] -= 3
            if consume_sets(local):
                return True
            local[(suit, rank)] += 3
        if rank <= 7 and local[(suit, rank + 1)] > 0 and local[(suit, rank + 2)] > 0:
            local[(suit, rank)] -= 1
            local[(suit, rank + 1)] -= 1
            local[(suit, rank + 2)] -= 1
            if consume_sets(local):
                return True
            local[(suit, rank)] += 1
            local[(suit, rank + 1)] += 1
            local[(suit, rank + 2)] += 1
        return False

    for key, count in list(counts.items()):
        if count >= 2:
            counts[key] -= 2
            if consume_sets(counts):
                return True
            counts[key] += 2
    return False


def cm_seven_pairs(cards):
    if len(cards) != 14:
        return False
    counts = cm_counts(cards)
    return sum(count // 2 for count in counts.values()) == 7


def cm_triplet_win(cards):
    if len(cards) % 3 != 2:
        return False
    counts = cm_counts(cards)
    for key, count in counts.items():
        if count >= 2:
            rest = counts.copy()
            rest[key] -= 2
            if all(value % 3 == 0 for value in rest.values()):
                return True
    return False


def cm_can_win(player, extra_tile=None):
    if player.get("cmWon"):
        return False
    cards = list(player.get("cmHand", []))
    if extra_tile is not None:
        cards.append(extra_tile)
    missing = player.get("cmMissing")
    if missing and any(tile["suit"] == missing for tile in cards):
        return False
    meld_count = len(player.get("cmMelds", []))
    if len(cards) + 3 * meld_count != 14:
        return False
    if meld_count == 0 and cm_seven_pairs(cards):
        return True
    return cm_standard_win(cards)


def cm_win_info(player, extra_tile=None, self_draw=False):
    cards = list(player.get("cmHand", []))
    if extra_tile is not None:
        cards.append(extra_tile)
    melds = player.get("cmMelds", [])
    labels = ["平胡"]
    fan = 0
    all_suits = {tile["suit"] for tile in cards}
    for meld in melds:
        all_suits.add(meld["suit"])
    if len(all_suits) == 1:
        fan += 2
        labels.append("清一色")
    if not melds and cm_seven_pairs(cards):
        fan += 2
        labels.append("七对")
    elif cm_triplet_win(cards) and all(meld.get("type") in ("peng", "gang") for meld in melds):
        fan += 1
        labels.append("对对胡")
    if self_draw:
        fan += 1
        labels.append("自摸")
    points = 2 ** min(fan, 5)
    return {"fan": fan, "points": points, "label": " · ".join(labels)}


def cm_active_players():
    return [player for player in STATE["players"] if not player.get("isBot") and not player.get("cmWon")]


def cm_next_active_id(current_id):
    players = [player for player in STATE["players"] if not player.get("isBot")]
    if not players:
        return None
    ids = [player["id"] for player in players]
    try:
        start = ids.index(current_id)
    except ValueError:
        start = -1
    for offset in range(1, len(players) + 1):
        player = players[(start + offset) % len(players)]
        if not player.get("cmWon"):
            return player["id"]
    return None


def cm_finish(reason):
    ranking = sorted(
        [player for player in STATE["players"] if not player.get("isBot")],
        key=lambda player: (player.get("cmScore", 0), player.get("cmWon", False)),
        reverse=True,
    )
    summary = "；".join(f"{player['name']} {player.get('cmScore', 0):+d}" for player in ranking)
    STATE["roundResult"] = f"{reason}。{summary}"
    STATE["winnerId"] = ranking[0]["id"] if ranking else None
    STATE["phase"] = "finished"
    STATE["turnPlayerId"] = None
    bump()


def cm_check_end():
    humans = [player for player in STATE["players"] if not player.get("isBot")]
    active = [player for player in humans if not player.get("cmWon")]
    if len(active) <= 1:
        cm_finish("血战结束")
        return True
    if not STATE["chuanma"]["wall"]:
        cm_finish("牌墙已摸完")
        return True
    return False


def cm_draw_for(player_id):
    if cm_check_end():
        return
    player = player_by_id(player_id)
    if not player or player.get("cmWon"):
        next_id = cm_next_active_id(player_id)
        if next_id:
            cm_draw_for(next_id)
        return
    wall = STATE["chuanma"]["wall"]
    if not wall:
        cm_finish("牌墙已摸完")
        return
    tile = wall.pop()
    player["cmHand"].append(tile)
    sort_cm_hand(player["cmHand"])
    player["cmDrawnId"] = tile["id"]
    STATE["phase"] = "cm_play"
    STATE["turnPlayerId"] = player_id
    STATE["chuanma"]["responseOptions"] = {}
    STATE["chuanma"]["responses"] = {}
    STATE["chuanma"]["responseDeadline"] = 0.0
    STATE["chuanma"]["needsDiscard"] = True
    STATE["chuanma"]["message"] = f"{player['name']} 已摸牌"
    bump()


def cm_exchange_target_map(players, direction):
    count = len(players)
    result = {}
    for index, player in enumerate(players):
        if count == 2:
            target_index = 1 - index
        elif direction == "逆时针":
            target_index = (index - 1) % count
        elif direction == "对家":
            target_index = (index + 2) % count
        else:
            target_index = (index + 1) % count
        result[player["id"]] = players[target_index]["id"]
    return result


def cm_finish_exchange():
    players = [player for player in STATE["players"] if not player.get("isBot")]
    selections = STATE["chuanma"]["exchangeSelections"]
    target_map = cm_exchange_target_map(players, STATE["chuanma"]["exchangeDirection"])
    packets = {}
    for player in players:
        selected_ids = set(selections[player["id"]])
        packet = [tile for tile in player["cmHand"] if tile["id"] in selected_ids]
        player["cmHand"] = [tile for tile in player["cmHand"] if tile["id"] not in selected_ids]
        packets[target_map[player["id"]]] = packet
    for player in players:
        player["cmHand"].extend(packets.get(player["id"], []))
        sort_cm_hand(player["cmHand"])
    STATE["phase"] = "cm_dingque"
    STATE["turnPlayerId"] = None
    STATE["chuanma"]["message"] = f"换三张完成（{STATE['chuanma']['exchangeDirection']}），请选择定缺"
    bump()


def start_chuanma():
    players = [player for player in STATE["players"] if not player.get("isBot")]
    wall = cm_deck()
    dealer_id = STATE["hostPlayerId"] if player_by_id(STATE["hostPlayerId"]) else players[0]["id"]
    for player in players:
        player["cmHand"] = []
        player["cmMelds"] = []
        player["cmMissing"] = None
        player["cmWon"] = False
        player["cmScore"] = 0
        player["cmDrawnId"] = None
        player["cmExchange"] = []
    for _ in range(13):
        for player in players:
            player["cmHand"].append(wall.pop())
    dealer = player_by_id(dealer_id)
    dealer["cmHand"].append(wall.pop())
    for player in players:
        sort_cm_hand(player["cmHand"])
    if len(players) == 4:
        direction = random.SystemRandom().choice(["顺时针", "逆时针", "对家"])
    elif len(players) == 3:
        direction = random.SystemRandom().choice(["顺时针", "逆时针"])
    else:
        direction = "互换"
    STATE["chuanma"] = fresh_chuanma()
    STATE["chuanma"].update({"wall": wall, "dealerId": dealer_id, "exchangeDirection": direction, "message": "请选择三张同花色的牌进行交换"})
    STATE["phase"] = "cm_exchange"
    STATE["turnPlayerId"] = None
    STATE["roundNo"] = 1
    bump()


def cm_begin_play():
    dealer_id = STATE["chuanma"]["dealerId"]
    STATE["phase"] = "cm_play"
    STATE["turnPlayerId"] = dealer_id
    STATE["chuanma"]["needsDiscard"] = True
    STATE["chuanma"]["message"] = f"{player_by_id(dealer_id)['name']} 先出牌"
    bump()


def cm_remove_last_discard():
    pile = STATE["chuanma"]["discardPile"]
    if pile and STATE["chuanma"]["lastDiscard"] and pile[-1].get("tile", {}).get("id") == STATE["chuanma"]["lastDiscard"]["tile"]["id"]:
        pile.pop()


def cm_offer_responses(discarder, tile):
    options = {}
    for player in cm_active_players():
        if player["id"] == discarder["id"]:
            continue
        actions = []
        if cm_can_win(player, tile):
            actions.append("hu")
        if tile["suit"] != player.get("cmMissing"):
            matching = sum(1 for own in player["cmHand"] if cm_same(own, tile))
            if matching >= 3:
                actions.append("gang")
            if matching >= 2:
                actions.append("peng")
        if actions:
            actions.append("pass")
            options[player["id"]] = actions
    STATE["chuanma"]["responseOptions"] = options
    STATE["chuanma"]["responses"] = {}
    if options:
        STATE["phase"] = "cm_response"
        STATE["turnPlayerId"] = None
        STATE["chuanma"]["responseDeadline"] = time.time() + 22
        STATE["chuanma"]["message"] = "等待其他玩家响应"
        bump()
    else:
        next_id = cm_next_active_id(discarder["id"])
        if next_id:
            cm_draw_for(next_id)


def cm_score_gang(player, kind, source_id=None):
    opponents = [item for item in cm_active_players() if item["id"] != player["id"]]
    if kind == "exposed" and source_id:
        source = player_by_id(source_id)
        if source and not source.get("cmWon"):
            source["cmScore"] -= 2
            player["cmScore"] += 2
    else:
        value = 2 if kind == "concealed" else 1
        for opponent in opponents:
            opponent["cmScore"] -= value
            player["cmScore"] += value


def cm_resolve_responses():
    cm = STATE["chuanma"]
    tile = cm["lastDiscard"]["tile"]
    discarder_id = cm["discarderId"]
    responses = cm["responses"]
    option_ids = list(cm["responseOptions"])
    hu_ids = [pid for pid in option_ids if responses.get(pid) == "hu"]
    if hu_ids:
        discarder = player_by_id(discarder_id)
        records = []
        for pid in hu_ids:
            winner = player_by_id(pid)
            if not winner or winner.get("cmWon"):
                continue
            info = cm_win_info(winner, tile, self_draw=False)
            winner["cmWon"] = True
            winner["cmScore"] += info["points"]
            if discarder:
                discarder["cmScore"] -= info["points"]
            records.append(f"{winner['name']} 荣和（{info['label']}，{info['points']}分）")
            cm["winRecords"].append({"winnerId": pid, "fromId": discarder_id, "label": info["label"], "points": info["points"]})
        cm["message"] = "；".join(records)
        cm["responseOptions"] = {}
        cm["responses"] = {}
        cm["responseDeadline"] = 0
        if cm_check_end():
            return
        next_id = cm_next_active_id(discarder_id)
        if next_id:
            cm_draw_for(next_id)
        return

    def seat_distance(pid):
        players = [p for p in STATE["players"] if not p.get("isBot")]
        ids = [p["id"] for p in players]
        return (ids.index(pid) - ids.index(discarder_id)) % len(ids)

    gang_ids = [pid for pid in option_ids if responses.get(pid) == "gang"]
    peng_ids = [pid for pid in option_ids if responses.get(pid) == "peng"]
    claimant_id = min(gang_ids, key=seat_distance) if gang_ids else (min(peng_ids, key=seat_distance) if peng_ids else None)
    action = "gang" if gang_ids else ("peng" if peng_ids else None)
    cm["responseOptions"] = {}
    cm["responses"] = {}
    cm["responseDeadline"] = 0
    if claimant_id and action:
        claimant = player_by_id(claimant_id)
        need = 3 if action == "gang" else 2
        removed = []
        rest = []
        for own in claimant["cmHand"]:
            if len(removed) < need and cm_same(own, tile):
                removed.append(own)
            else:
                rest.append(own)
        claimant["cmHand"] = rest
        claimant["cmMelds"].append({"type": action, "suit": tile["suit"], "rank": tile["rank"], "kind": "exposed", "fromId": discarder_id})
        cm_remove_last_discard()
        STATE["turnPlayerId"] = claimant_id
        claimant["cmDrawnId"] = None
        if action == "gang":
            cm_score_gang(claimant, "exposed", discarder_id)
            cm["message"] = f"{claimant['name']} 明杠"
            cm_draw_for(claimant_id)
        else:
            cm["needsDiscard"] = True
            STATE["phase"] = "cm_play"
            cm["message"] = f"{claimant['name']} 碰牌后请出牌"
            bump()
        return
    next_id = cm_next_active_id(discarder_id)
    if next_id:
        cm_draw_for(next_id)


def cm_self_gang_options(player):
    if STATE["mode"] != "chuanma" or STATE["phase"] != "cm_play" or STATE["turnPlayerId"] != player["id"]:
        return []
    counts = cm_counts(player.get("cmHand", []))
    options = []
    for (suit, rank), count in counts.items():
        if suit == player.get("cmMissing"):
            continue
        if count == 4:
            options.append({"suit": suit, "rank": rank, "kind": "concealed"})
        if count >= 1 and any(meld["type"] == "peng" and meld["suit"] == suit and int(meld["rank"]) == rank for meld in player.get("cmMelds", [])):
            options.append({"suit": suit, "rank": rank, "kind": "added"})
    return options


def chuanma_tick():
    if STATE.get("mode") != "chuanma":
        return
    if STATE.get("phase") == "cm_response" and STATE["chuanma"].get("responseDeadline") and time.time() >= STATE["chuanma"]["responseDeadline"]:
        for pid in STATE["chuanma"]["responseOptions"]:
            STATE["chuanma"]["responses"].setdefault(pid, "pass")
        cm_resolve_responses()


def chuanma_public(player_id):
    cm = STATE.get("chuanma", fresh_chuanma())
    player = player_by_id(player_id)
    response_options = list(cm.get("responseOptions", {}).get(player_id, []))
    can_discard = bool(
        player and STATE["phase"] == "cm_play" and STATE["turnPlayerId"] == player_id
        and cm.get("needsDiscard") and not player.get("cmWon")
    )
    can_hu = bool(can_discard and cm_can_win(player))
    return {
        "wallCount": len(cm.get("wall", [])),
        "dealerId": cm.get("dealerId"),
        "exchangeDirection": cm.get("exchangeDirection", ""),
        "exchangeSubmitted": bool(player_id in cm.get("exchangeSelections", {})),
        "dingqueSubmitted": bool(player and player.get("cmMissing")),
        "message": cm.get("message", ""),
        "needsDiscard": bool(cm.get("needsDiscard")),
        "myHand": list(player.get("cmHand", [])) if player else [],
        "myMissing": player.get("cmMissing") if player else None,
        "myWon": bool(player.get("cmWon")) if player else False,
        "myDrawnId": player.get("cmDrawnId") if player else None,
        "responseOptions": response_options,
        "responded": player_id in cm.get("responses", {}),
        "canDiscard": can_discard,
        "canHu": can_hu,
        "gangOptions": cm_self_gang_options(player) if player else [],
        "lastDiscard": cm.get("lastDiscard"),
        "discardPile": list(cm.get("discardPile", [])[-72:]),
        "winRecords": list(cm.get("winRecords", [])),
    }

def fresh_state():
    return {
        "version": 1,
        "phase": "lobby",
        "mode": "cards",
        "hostPlayerId": None,
        "players": [],
        "settings": {
            "cardLives": 3,
            "diceStart": 5,
            "onesWild": True,
            "exactEnabled": True,
            "drawRounds": 2,
            "drawTime": 75,
            "drawDifficulty": "mixed",
            "drawLibrary": "random",
        },
        "turnPlayerId": None,
        "roundNo": 0,
        "roundLoserId": None,
        "roundResult": "",
        "winnerId": None,
        "card": {"targetRank": "Q", "lastPlay": None, "revealedCards": []},
        "dice": {"currentBid": None, "lastCount": None},
        "draw": fresh_draw(),
        "ddz": fresh_ddz(),
        "chuanma": fresh_chuanma(),
    }

def migrate(state):
    base = fresh_state()
    if not isinstance(state, dict):
        return base
    for key, value in base.items():
        state.setdefault(key, value)
    for key, value in base["settings"].items():
        state.setdefault("settings", {}).setdefault(key, value)
    state.setdefault("card", base["card"])
    state.setdefault("dice", base["dice"])
    state.setdefault("draw", base["draw"])
    state.setdefault("ddz", base["ddz"])
    state.setdefault("chuanma", base["chuanma"])
    for key, value in fresh_draw().items():
        state["draw"].setdefault(key, value)
    for key, value in fresh_ddz().items():
        state["ddz"].setdefault(key, value)
    for key, value in fresh_chuanma().items():
        state["chuanma"].setdefault(key, value)
    for player in state.get("players", []):
        player.setdefault("seatKey", "")
        player.setdefault("connected", True)
        player.setdefault("lastSeen", time.time())
        player.setdefault("ready", False)
        player.setdefault("life", state["settings"]["cardLives"])
        player.setdefault("hand", [])
        player.setdefault("diceCount", state["settings"]["diceStart"])
        player.setdefault("dice", [])
        player.setdefault("score", 0)
        player.setdefault("ddzHand", [])
        player.setdefault("ddzScore", 0)
        player.setdefault("ddzHintCursor", 0)
        player.setdefault("isBot", False)
        player.setdefault("cmHand", [])
        player.setdefault("cmMelds", [])
        player.setdefault("cmMissing", None)
        player.setdefault("cmWon", False)
        player.setdefault("cmScore", 0)
        player.setdefault("cmDrawnId", None)
        player.setdefault("cmExchange", [])
    return state

def load_saved():
    for path in (STATE_FILE, LEGACY_STATE_FILE):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            state = migrate(data.get("state"))
            tokens = data.get("tokens")
            if isinstance(tokens, dict):
                return state, tokens
        except Exception:
            pass
    return fresh_state(), {}

STATE, TOKENS = load_saved()
SAVE_EVENT = threading.Event()
SAVE_WRITE_LOCK = threading.Lock()
ACTION_CACHE = {}


def _snapshot_json():
    with LOCK:
        return json.dumps({"state": STATE, "tokens": TOKENS}, ensure_ascii=False)


def flush_state():
    try:
        with SAVE_WRITE_LOCK:
            # Snapshot inside the write lock. This prevents an older queued
            # snapshot from overwriting a newer explicit room reset.
            payload = _snapshot_json()
            temp = STATE_FILE.with_suffix(".tmp")
            temp.write_text(payload, encoding="utf-8")
            temp.replace(STATE_FILE)
    except Exception as exc:
        print("状态保存失败：", exc)


def _save_worker():
    while True:
        SAVE_EVENT.wait()
        # 合并短时间内的多次操作，避免安卓共享存储阻塞请求。
        time.sleep(0.18)
        SAVE_EVENT.clear()
        flush_state()


threading.Thread(target=_save_worker, name="game-state-writer", daemon=True).start()


def save_state():
    SAVE_EVENT.set()


def bump(persist=True):
    STATE["version"] += 1
    if persist:
        save_state()


def get_cached_action(player_id, request_id):
    if not request_id:
        return None
    now = time.time()
    for key, item in list(ACTION_CACHE.items()):
        if now - item[0] > ACTION_CACHE_TTL:
            ACTION_CACHE.pop(key, None)
    item = ACTION_CACHE.get((player_id, request_id))
    if not item:
        return None
    return dict(item[1]), int(item[2])


def remember_action(player_id, request_id, payload, rule_code):
    if not request_id:
        return
    if len(ACTION_CACHE) >= ACTION_CACHE_LIMIT:
        oldest = min(ACTION_CACHE, key=lambda key: ACTION_CACHE[key][0])
        ACTION_CACHE.pop(oldest, None)
    ACTION_CACHE[(player_id, request_id)] = (time.time(), dict(payload or {}), int(rule_code))

def player_by_id(player_id):
    return next((p for p in STATE["players"] if p["id"] == player_id), None)

def touch_player(player):
    if player:
        player["lastSeen"] = time.time()
        player["connected"] = True

def is_connected(player):
    if player.get("isBot"):
        return True
    return (time.time() - float(player.get("lastSeen", 0))) <= ONLINE_TIMEOUT

def remove_player(player_id):
    player = player_by_id(player_id)
    if not player:
        return None
    STATE["players"] = [p for p in STATE["players"] if p["id"] != player_id]
    for token, mapped_id in list(TOKENS.items()):
        if mapped_id == player_id:
            TOKENS.pop(token, None)
    if STATE.get("hostPlayerId") == player_id:
        STATE["hostPlayerId"] = STATE["players"][0]["id"] if STATE["players"] else None
    return player

def remove_ddz_bots():
    bot_ids = [p["id"] for p in STATE["players"] if p.get("isBot")]
    for bot_id in bot_ids:
        remove_player(bot_id)
    return len(bot_ids)

def add_ddz_bots():
    remove_ddz_bots()
    names = ["机器人小北", "机器人阿南"]
    index = 0
    while len(STATE["players"]) < 3:
        bot_id = "bot_" + secrets.token_hex(4)
        STATE["players"].append({
            "id": bot_id, "name": names[index] if index < len(names) else f"机器人{index + 1}",
            "ready": True, "connected": True, "lastSeen": time.time(), "seatKey": "", "isBot": True,
            "life": STATE["settings"]["cardLives"], "hand": [], "diceCount": STATE["settings"]["diceStart"],
            "dice": [], "score": 0, "ddzHand": [], "ddzScore": 0, "ddzHintCursor": 0,
        })
        index += 1

def prune_lobby_players():
    if STATE.get("phase") != "lobby":
        return []
    now = time.time()
    stale = [p["id"] for p in STATE["players"] if not p.get("isBot") and now - float(p.get("lastSeen", 0)) > ZOMBIE_TIMEOUT]
    if not stale:
        return []
    for player_id in stale:
        remove_player(player_id)
    bump()
    return stale

def is_out(player):
    if STATE["mode"] == "cards":
        return player["life"] <= 0
    if STATE["mode"] == "dice":
        return player["diceCount"] <= 0
    if STATE["mode"] in ("ddz", "chuanma"):
        return bool(player.get("cmWon")) if STATE["mode"] == "chuanma" else False
    return False

def alive_players():
    return [p for p in STATE["players"] if not is_out(p)]

def next_alive_id(current_id):
    players = STATE["players"]
    if not players:
        return None
    ids = [p["id"] for p in players]
    try:
        start = ids.index(current_id)
    except ValueError:
        start = -1
    for offset in range(1, len(players) + 1):
        player = players[(start + offset) % len(players)]
        if not is_out(player):
            return player["id"]
    return None
def create_card_deck():
    deck = []
    for rank in ("A", "Q", "K"):
        for _ in range(6):
            deck.append({"id": "c_" + secrets.token_hex(5), "rank": rank})
    for _ in range(2):
        deck.append({"id": "c_" + secrets.token_hex(5), "rank": "JOKER"})
    random.SystemRandom().shuffle(deck)
    return deck

def finish_game():
    if STATE["mode"] == "draw":
        if not STATE["players"]:
            return
        best = max(p["score"] for p in STATE["players"])
        winners = [p for p in STATE["players"] if p["score"] == best]
        STATE["winnerId"] = winners[0]["id"]
        STATE["roundResult"] = "、".join(p["name"] for p in winners) + f" 以 {best} 分获胜"
    else:
        alive = alive_players()
        if not alive:
            return
        STATE["winnerId"] = alive[0]["id"]
    STATE["phase"] = "finished"
    STATE["turnPlayerId"] = None
    bump()

def start_cards_round(starter_id=None):
    alive = alive_players()
    if len(alive) <= 1:
        finish_game()
        return
    deck = create_card_deck()
    for player in STATE["players"]:
        player["hand"] = []
    for _ in range(5):
        for player in alive:
            player["hand"].append(deck.pop())
    order = {"A": 0, "Q": 1, "K": 2, "JOKER": 3}
    for player in alive:
        player["hand"].sort(key=lambda card: order[card["rank"]])
    alive_ids = [p["id"] for p in alive]
    if starter_id not in alive_ids:
        starter_id = alive_ids[0]
    STATE["roundNo"] += 1
    STATE["phase"] = "cards_play"
    STATE["turnPlayerId"] = starter_id
    STATE["roundLoserId"] = None
    STATE["roundResult"] = ""
    STATE["card"] = {"targetRank": random.SystemRandom().choice(["A", "Q", "K"]), "lastPlay": None, "revealedCards": []}
    bump()

def finish_cards_round(loser_id, result, revealed_cards):
    loser = player_by_id(loser_id)
    if loser and loser["life"] > 0:
        loser["life"] -= 1
        if loser["life"] == 0:
            result += f"；{loser['name']} 已趴桌"
    STATE["phase"] = "cards_reveal"
    STATE["turnPlayerId"] = None
    STATE["roundLoserId"] = loser_id
    STATE["roundResult"] = result
    STATE["card"]["revealedCards"] = revealed_cards
    if len(alive_players()) <= 1:
        finish_game()
    else:
        bump()

def dice_count_detail(face):
    face = int(face)
    natural = 0
    wild = 0
    revealed = []
    for player in alive_players():
        dice = list(player.get("dice", []))
        natural += sum(1 for value in dice if value == face)
        if STATE["settings"]["onesWild"] and face != 1:
            wild += sum(1 for value in dice if value == 1)
        revealed.append({"playerId": player["id"], "playerName": player["name"], "dice": dice})
    return {
        "face": face,
        "natural": natural,
        "wild": wild,
        "total": natural + wild,
        "onesWild": bool(STATE["settings"]["onesWild"]),
        "revealed": revealed,
    }


def dice_total(face):
    return dice_count_detail(face)["total"]


def dice_public():
    bid = STATE["dice"].get("currentBid")
    reveal = STATE["phase"] in ("dice_reveal", "finished") and STATE.get("mode") == "dice"
    detail = STATE["dice"].get("lastCount") if reveal else None
    return {
        "currentBid": dict(bid) if bid else None,
        "countDetail": dict(detail) if detail else None,
        "revealed": list(detail.get("revealed", [])) if detail else [],
        "ruleText": "叫骰表示至少有这么多；开你只在实际数量少于叫数时成功；抓准要求刚好相等。",
    }


def start_dice_round(starter_id=None):
    alive = alive_players()
    if len(alive) <= 1:
        finish_game()
        return
    rng = random.SystemRandom()
    for player in STATE["players"]:
        player["dice"] = sorted(rng.randint(1, 6) for _ in range(player["diceCount"])) if player["diceCount"] > 0 else []
    alive_ids = [p["id"] for p in alive]
    if starter_id not in alive_ids:
        starter_id = alive_ids[0]
    STATE["roundNo"] += 1
    STATE["phase"] = "dice_bidding"
    STATE["turnPlayerId"] = starter_id
    STATE["roundLoserId"] = None
    STATE["roundResult"] = ""
    STATE["dice"] = {"currentBid": None, "lastCount": None}
    bump()


def finish_dice_round(loser_id, result, gain_id=None):
    loser = player_by_id(loser_id)
    if loser and loser["diceCount"] > 0:
        loser["diceCount"] -= 1
        if loser["diceCount"] == 0:
            result += f"；{loser['name']} 已出局"
    if gain_id:
        gainer = player_by_id(gain_id)
        if gainer and gainer["diceCount"] > 0:
            old = gainer["diceCount"]
            gainer["diceCount"] = min(STATE["settings"]["diceStart"], gainer["diceCount"] + 1)
            if gainer["diceCount"] > old:
                result += f"；{gainer['name']} 恢复 1 颗骰子"
    STATE["phase"] = "dice_reveal"
    STATE["turnPlayerId"] = None
    STATE["roundLoserId"] = loser_id
    STATE["roundResult"] = result
    if len(alive_players()) <= 1:
        finish_game()
    else:
        bump()
def normalize_guess(value):
    return re.sub(r"[\s\W_]+", "", str(value), flags=re.UNICODE).lower()


def draw_library_pool():
    selected = str(STATE["settings"].get("drawLibrary", "random"))
    if selected not in LIBRARY_LABEL:
        selected = "random"
    if selected == "random":
        selected = random.SystemRandom().choice(DRAW_RANDOM_LIBRARIES)
    if selected == "mixed":
        return list(WORD_BANK), "mixed"
    return [word for word in WORD_BANK if word.get("library") == selected], selected


def word_candidates():
    pool, active_library = draw_library_pool()
    difficulty = STATE["settings"]["drawDifficulty"]
    if difficulty != "mixed":
        filtered = [word for word in pool if word["difficulty"] == difficulty]
        if len(filtered) >= 3:
            pool = filtered
    used = set(STATE["draw"].get("usedWords", []))
    available = [word for word in pool if word["word"] not in used]
    if len(available) < 3:
        STATE["draw"]["usedWords"] = []
        available = list(pool)
    if not available:
        available = [word for word in WORD_BANK if word.get("library") == "items"]
        active_library = "items"
    STATE["draw"]["activeLibrary"] = active_library
    return random.SystemRandom().sample(available, min(3, len(available)))


def start_draw_turn():
    draw = STATE["draw"]
    if draw["turnIndex"] >= draw["totalTurns"]:
        finish_game()
        return
    players = [player for player in STATE["players"] if not player.get("isBot")]
    if not players:
        finish_game()
        return
    drawer = players[draw["turnIndex"] % len(players)]
    choices = word_candidates()
    draw.update({
        "drawerId": drawer["id"],
        "choices": choices,
        "word": "",
        "aliases": [],
        "category": "",
        "difficulty": "",
        "chooseDeadline": time.time() + 25,
        "deadline": 0.0,
        "strokes": [],
        "strokeSeq": 0,
        "canvasRevision": int(draw.get("canvasRevision", 0)) + 1,
        "guesses": [],
        "correctIds": [],
        "answer": "",
        "result": "",
    })
    STATE["phase"] = "draw_choose"
    STATE["turnPlayerId"] = drawer["id"]
    STATE["roundNo"] = draw["turnIndex"] + 1
    bump()


def begin_draw_word(index):
    draw = STATE["draw"]
    if not draw["choices"]:
        draw["choices"] = word_candidates()
    index = max(0, min(int(index), len(draw["choices"]) - 1))
    choice = draw["choices"][index]
    draw["word"] = choice["word"]
    draw["aliases"] = list(choice.get("aliases", []))
    draw["category"] = choice["category"]
    draw["difficulty"] = choice["difficulty"]
    draw["activeLibrary"] = choice.get("library", draw.get("activeLibrary", "items"))
    draw["usedWords"].append(choice["word"])
    draw["choices"] = []
    draw["deadline"] = time.time() + STATE["settings"]["drawTime"]
    draw["chooseDeadline"] = 0.0
    STATE["phase"] = "draw_play"
    bump()


def end_draw_turn(reason):
    draw = STATE["draw"]
    answer = draw["word"]
    draw["answer"] = answer
    guessed = len(draw["correctIds"])
    total_guessers = max(1, len([p for p in STATE["players"] if not p.get("isBot")]) - 1)
    if reason == "all":
        result = f"全员猜中，答案是“{answer}”"
    elif guessed:
        result = f"{guessed}/{total_guessers} 人猜中，答案是“{answer}”"
    else:
        result = f"无人猜中，答案是“{answer}”"
    draw["result"] = result
    draw["deadline"] = 0.0
    STATE["roundResult"] = result
    STATE["phase"] = "draw_reveal"
    STATE["turnPlayerId"] = None
    bump()


def update_timers():
    if STATE.get("mode") == "ddz":
        ddz_bot_step()
        return
    if STATE.get("mode") == "chuanma":
        chuanma_tick()
        return
    if STATE["mode"] != "draw":
        return
    now = time.time()
    if STATE["phase"] == "draw_choose" and STATE["draw"]["chooseDeadline"] and now >= STATE["draw"]["chooseDeadline"]:
        begin_draw_word(0)
    elif STATE["phase"] == "draw_play" and STATE["draw"]["deadline"] and now >= STATE["draw"]["deadline"]:
        end_draw_turn("timeout")


def draw_public(player_id, since_seq=-1, client_revision=-1):
    draw = STATE["draw"]
    is_drawer = player_id == draw["drawerId"]
    show_answer = STATE["phase"] in ("draw_reveal", "finished")
    choices = []
    if STATE["phase"] == "draw_choose" and is_drawer:
        choices = [
            {
                "word": word["word"],
                "category": word["category"],
                "difficultyLabel": DIFFICULTY_LABEL[word["difficulty"]],
                "libraryLabel": LIBRARY_LABEL.get(word.get("library", "items"), "中文词库"),
            }
            for word in draw["choices"]
        ]
    word = draw["word"] if is_drawer or show_answer else ""
    hint = ""
    if draw["word"] and not is_drawer:
        count = len(re.sub(r"[\s，。！？、,.!?]", "", draw["word"]))
        hint = f"{draw['category']} · {count} 个字"

    revision = int(draw.get("canvasRevision", 0))
    seq = int(draw.get("strokeSeq", 0))
    full_canvas = client_revision != revision or since_seq < 0 or since_seq > seq
    if full_canvas:
        strokes = list(draw["strokes"])
    else:
        strokes = [stroke for stroke in draw["strokes"] if int(stroke.get("seq", 0)) > since_seq]

    return {
        "drawerId": draw["drawerId"],
        "turnIndex": draw["turnIndex"],
        "totalTurns": draw["totalTurns"],
        "choices": choices,
        "word": word,
        "hint": hint,
        "libraryLabel": LIBRARY_LABEL.get(draw.get("activeLibrary", "items"), "中文词库"),
        "deadline": draw["deadline"] or draw["chooseDeadline"],
        "strokes": strokes,
        "strokeSeq": seq,
        "canvasRevision": revision,
        "fullCanvas": full_canvas,
        "guesses": list(draw["guesses"][-12:]),
        "correctIds": list(draw["correctIds"]),
        "answer": draw["answer"] if show_answer else "",
        "result": draw["result"],
    }

def public_state(player_id, draw_since=-1, draw_revision=-1):
    update_timers()
    me = player_by_id(player_id)
    winner = player_by_id(STATE["winnerId"]) if STATE["winnerId"] else None
    can_advance = STATE["phase"] in ("cards_reveal", "dice_reveal", "draw_reveal") and (
        player_id == STATE["hostPlayerId"] or player_id == STATE["roundLoserId"] or player_id == STATE["draw"]["drawerId"]
    )
    max_players = 3 if STATE["mode"] == "ddz" else 4
    min_players = 1 if STATE["mode"] == "ddz" else 2
    last_play = STATE["card"]["lastPlay"]
    return {
        "version": STATE["version"],
        "phase": STATE["phase"],
        "mode": STATE["mode"],
        "hostPlayerId": STATE["hostPlayerId"],
        "isHost": player_id == STATE["hostPlayerId"],
        "settings": dict(STATE["settings"]),
        "players": [
            {
                "id": p["id"], "name": p["name"], "ready": p["ready"], "connected": is_connected(p),
                "life": p["life"], "diceCount": p["diceCount"], "score": p["score"], "out": is_out(p),
                "handCount": (len(p.get("ddzHand", [])) if STATE["mode"] == "ddz" else len(p.get("cmHand", []))),
                "role": ("地主" if STATE["ddz"].get("landlordId") == p["id"] else ("农民" if STATE["ddz"].get("landlordId") else "待定")),
                "ddzScore": p.get("ddzScore", 0),
                "isBot": bool(p.get("isBot")),
                "cmMissing": p.get("cmMissing"),
                "cmWon": bool(p.get("cmWon")),
                "cmScore": int(p.get("cmScore", 0)),
                "cmMelds": list(p.get("cmMelds", [])),
            } for p in STATE["players"]
        ],
        "canStart": (
            player_id == STATE["hostPlayerId"] and STATE["phase"] == "lobby"
            and min_players <= len([p for p in STATE["players"] if not p.get("isBot")]) <= max_players
            and all(p["ready"] and is_connected(p) for p in STATE["players"] if not p.get("isBot"))
        ),
        "turnPlayerId": STATE["turnPlayerId"],
        "roundNo": STATE["roundNo"],
        "roundResult": STATE["roundResult"],
        "canAdvanceRound": can_advance,
        "winnerName": (STATE["roundResult"] if STATE["mode"] in ("draw", "ddz", "chuanma") and STATE["phase"] == "finished" else (winner["name"] if winner else "")),
        "myCards": list(me["hand"]) if me and STATE["mode"] == "cards" else [],
        "myDice": list(me["dice"]) if me and STATE["mode"] == "dice" else [],
        "myDdzCards": list(me.get("ddzHand", [])) if me and STATE["mode"] == "ddz" else [],
        "card": {
            "targetRank": STATE["card"]["targetRank"],
            "lastPlay": {"playerId": last_play["playerId"], "playerName": last_play["playerName"], "count": len(last_play["cards"])} if last_play else None,
            "revealedCards": list(STATE["card"].get("revealedCards", [])),
        },
        "dice": dice_public(),
        "draw": draw_public(player_id, draw_since, draw_revision),
        "ddz": ddz_public(player_id),
        "chuanma": chuanma_public(player_id),
    }

class ReliableThreadingHTTPServer(ThreadingHTTPServer):
    request_queue_size = 32
    daemon_threads = True
    allow_reuse_address = True
    block_on_close = False


class Handler(BaseHTTPRequestHandler):
    server_version = "GameHallLAN/6.2"
    protocol_version = "HTTP/1.0"

    def log_message(self, fmt, *args):
        if self.path.startswith("/api/state"):
            return
        print(f"[{self.address_string()}] {fmt % args}")

    def reply(self, body, code=200, content_type="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            raw = body.encode("utf-8")
        else:
            raw = body
        try:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        return json.loads((self.rfile.read(length) if length else b"{}").decode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.reply(HTML_PAGE, 200, "text/html; charset=utf-8")
            return
        if parsed.path == "/favicon.ico":
            self.reply(b"", 204, "image/x-icon")
            return
        if parsed.path == "/api/state":
            query = parse_qs(parsed.query)
            token = query.get("token", [""])[0]
            try:
                draw_since = int(query.get("drawSeq", ["-1"])[0])
                draw_revision = int(query.get("drawRevision", ["-1"])[0])
            except Exception:
                draw_since, draw_revision = -1, -1
            with LOCK:
                player_id = TOKENS.get(token)
                caller = player_by_id(player_id) if player_id else None
                valid = bool(caller)
                if caller:
                    touch_player(caller)
                    prune_lobby_players()
                response = {"state": public_state(player_id, draw_since, draw_revision)} if valid and player_by_id(player_id) else {"error": "身份失效"}
            self.reply(response, 200 if valid else 401)
            return
        self.reply({"error": "not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        try:
            data = self.read_json()
        except Exception:
            self.reply({"error": "请求格式错误"}, 400)
            return
        if parsed.path == "/api/join":
            self.join_player(data)
            return
        if parsed.path != "/api/action":
            self.reply({"error": "not found"}, 404)
            return
        token = str(data.get("token", ""))
        action = str(data.get("type", ""))
        request_id = str(data.get("requestId", ""))[:96]
        with LOCK:
            update_timers()
            player_id = TOKENS.get(token)
            player = player_by_id(player_id) if player_id else None
            if not player:
                response = {"ok": False, "error": "身份失效，正在尝试恢复"}
            else:
                touch_player(player)
                cached = get_cached_action(player_id, request_id)
                if cached is None:
                    payload, rule_code = self.handle_action(player, action, data)
                    remember_action(player_id, request_id, payload, rule_code)
                else:
                    payload, rule_code = cached
                lightweight = action == "draw_stroke" and rule_code == 200
                response = {
                    "ok": rule_code == 200,
                    "requestId": request_id,
                    "replayed": cached is not None,
                }
                if not lightweight:
                    try:
                        action_draw_seq = int(data.get("drawSeq", -1))
                        action_draw_revision = int(data.get("drawRevision", -1))
                    except Exception:
                        action_draw_seq, action_draw_revision = -1, -1
                    response["state"] = public_state(player_id, action_draw_seq, action_draw_revision)
                if rule_code == 200 and payload:
                    response.update(payload)
                if rule_code != 200:
                    response["error"] = payload.get("error", "当前不能这样操作")
        self.reply(response, 200)

    def join_player(self, data):
        name = str(data.get("name", "玩家")).strip()[:10] or "玩家"
        old_token = str(data.get("token", ""))
        requested_id = str(data.get("playerId", ""))
        seat_key = str(data.get("seatKey", "")).strip()
        with LOCK:
            found = player_by_id(TOKENS.get(old_token)) if old_token in TOKENS else None
            if not found and seat_key:
                found = next((p for p in STATE["players"] if p.get("seatKey") == seat_key), None)
            if not found and requested_id:
                candidate = player_by_id(requested_id)
                if candidate and candidate["name"] == name:
                    found = candidate
            if found:
                token = secrets.token_urlsafe(18)
                TOKENS[token] = found["id"]
                touch_player(found)
                found["seatKey"] = seat_key or found.get("seatKey", "")
                prune_lobby_players()
                save_state()
                response = {"ok": True, "token": token, "playerId": found["id"], "reconnected": True}
            elif STATE["phase"] != "lobby":
                response = {"ok": False, "error": "游戏已经开始，未找到原座位"}
            else:
                prune_lobby_players()
                max_players = 4
                if len(STATE["players"]) >= max_players:
                    response = {"ok": False, "error": "座位已满"}
                else:
                    player_id = "p_" + secrets.token_hex(4)
                    token = secrets.token_urlsafe(18)
                    STATE["players"].append({
                        "id": player_id, "name": name, "ready": False, "connected": True, "lastSeen": time.time(), "seatKey": seat_key,
                        "life": STATE["settings"]["cardLives"], "hand": [], "diceCount": STATE["settings"]["diceStart"],
                        "dice": [], "score": 0, "ddzHand": [], "ddzScore": 0, "ddzHintCursor": 0, "isBot": False,
                        "cmHand": [], "cmMelds": [], "cmMissing": None, "cmWon": False, "cmScore": 0, "cmDrawnId": None, "cmExchange": [],
                    })
                    TOKENS[token] = player_id
                    if STATE["hostPlayerId"] is None:
                        STATE["hostPlayerId"] = player_id
                    bump()
                    response = {"ok": True, "token": token, "playerId": player_id, "reconnected": False}
        self.reply(response, 200)

    def handle_action(self, player, action, data):
        player_id = player["id"]

        if action == "rename":
            if STATE["phase"] != "lobby":
                return {"error": "只能在大厅修改昵称"}, 409
            name = str(data.get("name", "")).strip()[:10]
            if not name:
                return {"error": "昵称不能为空"}, 400
            player["name"] = name
            bump()
            return {}, 200

        if action == "leave":
            if STATE["phase"] != "lobby":
                return {"error": "游戏进行中会保留座位，请先返回大厅"}, 409
            remove_player(player_id)
            bump()
            return {}, 200

        if action == "kick":
            if player_id != STATE["hostPlayerId"]:
                return {"error": "只有房主能移除座位"}, 403
            if STATE["phase"] != "lobby":
                return {"error": "只能在大厅移除座位"}, 409
            target_id = str(data.get("targetId", ""))
            if not target_id or target_id == player_id:
                return {"error": "不能移除自己的房主座位"}, 400
            target = remove_player(target_id)
            if not target:
                return {"error": "该座位已经不存在"}, 409
            bump()
            return {}, 200

        if action == "toggle_ready":
            if STATE["phase"] != "lobby":
                return {"error": "游戏已经开始"}, 409
            player["ready"] = not player["ready"]; bump(); return {}, 200

        if action == "set_mode":
            if player_id != STATE["hostPlayerId"]:
                return {"error": "只有房主能选择玩法"}, 403
            if STATE["phase"] != "lobby":
                return {"error": "只能在大厅切换玩法"}, 409
            mode = str(data.get("mode", ""))
            if mode not in ("cards", "dice", "draw", "ddz", "chuanma"):
                return {"error": "未知玩法"}, 400
            remove_ddz_bots()
            STATE["mode"] = mode
            for item in STATE["players"]:
                item["ready"] = False
            bump(); return {}, 200

        if action == "settings":
            if player_id != STATE["hostPlayerId"]:
                return {"error": "只有房主能修改设置"}, 403
            if STATE["phase"] != "lobby":
                return {"error": "只能在大厅修改设置"}, 409
            try:
                card_lives = max(2, min(5, int(data.get("cardLives", 3))))
                dice_start = max(3, min(6, int(data.get("diceStart", 5))))
                draw_rounds = max(1, min(3, int(data.get("drawRounds", 2))))
                draw_time = max(30, min(120, int(data.get("drawTime", 75))))
            except Exception:
                return {"error": "设置值无效"}, 400
            difficulty = str(data.get("drawDifficulty", "mixed"))
            if difficulty not in ("mixed", "easy", "medium", "hard"):
                difficulty = "mixed"
            draw_library = str(data.get("drawLibrary", "random"))
            if draw_library not in LIBRARY_LABEL:
                draw_library = "random"
            STATE["settings"].update({
                "cardLives": card_lives, "diceStart": dice_start, "onesWild": bool(data.get("onesWild", True)),
                "exactEnabled": bool(data.get("exactEnabled", True)), "drawRounds": draw_rounds,
                "drawTime": draw_time, "drawDifficulty": difficulty, "drawLibrary": draw_library,
            })
            for item in STATE["players"]:
                item["life"] = card_lives; item["diceCount"] = dice_start
            bump(); return {}, 200

        if action == "start":
            if player_id != STATE["hostPlayerId"]:
                return {"error": "只有房主能开始"}, 403
            if STATE["phase"] != "lobby":
                return {"error": "游戏已经开始"}, 409
            humans = [item for item in STATE["players"] if not item.get("isBot")]
            min_players = 1 if STATE["mode"] == "ddz" else 2
            max_players = 3 if STATE["mode"] == "ddz" else 4
            if not (min_players <= len(humans) <= max_players):
                return {"error": ("斗地主支持 1～3 名真人，空位自动补机器人" if STATE["mode"] == "ddz" else "川麻支持 2～4 名真人，不补机器人" if STATE["mode"] == "chuanma" else "当前玩法支持 2～4 人")}, 409
            if not all(is_connected(item) for item in humans):
                return {"error": "房间里有离线座位，请等待重连或由房主移除"}, 409
            if not all(item["ready"] for item in humans):
                return {"error": "还有人没准备"}, 409
            if STATE["mode"] == "ddz":
                add_ddz_bots()
            STATE["roundNo"] = 0; STATE["winnerId"] = None; STATE["roundResult"] = ""
            for item in STATE["players"]:
                item["life"] = STATE["settings"]["cardLives"]; item["diceCount"] = STATE["settings"]["diceStart"]
                item["hand"] = []; item["dice"] = []; item["score"] = 0
                item["ddzHand"] = []; item["ddzScore"] = 0; item["ddzHintCursor"] = 0
                item["cmHand"] = []; item["cmMelds"] = []; item["cmMissing"] = None; item["cmWon"] = False; item["cmScore"] = 0; item["cmDrawnId"] = None; item["cmExchange"] = []
            if STATE["mode"] == "cards":
                start_cards_round(player_id)
            elif STATE["mode"] == "dice":
                start_dice_round(player_id)
            elif STATE["mode"] == "draw":
                STATE["draw"] = fresh_draw()
                STATE["draw"]["totalTurns"] = len([p for p in STATE["players"] if not p.get("isBot")]) * STATE["settings"]["drawRounds"]
                start_draw_turn()
            elif STATE["mode"] == "chuanma":
                start_chuanma()
            else:
                STATE["ddz"] = fresh_ddz()
                deal_ddz()
            return {}, 200

        if action == "cards_play":
            if STATE["phase"] != "cards_play" or STATE["mode"] != "cards":
                return {"error": "当前不能盖牌"}, 409
            if STATE["turnPlayerId"] != player_id:
                return {"error": "还没轮到你"}, 409
            card_ids = data.get("cardIds", [])
            if not isinstance(card_ids, list) or not 1 <= len(card_ids) <= 3 or len(set(card_ids)) != len(card_ids):
                return {"error": "请选择 1～3 张牌"}, 400
            selected_set = set(card_ids)
            selected = [card for card in player["hand"] if card["id"] in selected_set]
            if len(selected) != len(card_ids):
                return {"error": "所选牌已变化，请重选"}, 409
            player["hand"] = [card for card in player["hand"] if card["id"] not in selected_set]
            STATE["card"]["lastPlay"] = {"playerId": player_id, "playerName": player["name"], "cards": selected}
            STATE["turnPlayerId"] = next_alive_id(player_id); bump(); return {}, 200

        if action == "cards_challenge":
            if STATE["phase"] != "cards_play" or STATE["mode"] != "cards":
                return {"error": "当前不能质疑"}, 409
            if STATE["turnPlayerId"] != player_id:
                return {"error": "还没轮到你"}, 409
            last_play = STATE["card"]["lastPlay"]
            if not last_play:
                return {"error": "还没人出牌"}, 409
            target = STATE["card"]["targetRank"]; ranks = [card["rank"] for card in last_play["cards"]]
            truthful = all(rank in (target, "JOKER") for rank in ranks); previous = player_by_id(last_play["playerId"])
            if truthful:
                loser_id = player_id; result = f"{player['name']} 质疑失败，{previous['name']} 没有撒谎"
            else:
                loser_id = previous["id"]; result = f"{previous['name']} 被抓到撒谎"
            finish_cards_round(loser_id, result, ranks); return {}, 200

        if action == "dice_bid":
            if STATE["phase"] != "dice_bidding" or STATE["mode"] != "dice":
                return {"error": "当前不能叫骰"}, 409
            if STATE["turnPlayerId"] != player_id:
                return {"error": "还没轮到你"}, 409
            try:
                quantity, face = int(data.get("quantity")), int(data.get("face"))
            except Exception:
                return {"error": "叫法无效"}, 400
            total_dice = sum(p["diceCount"] for p in alive_players())
            if quantity < 1 or quantity > total_dice or face not in range(1, 7):
                return {"error": f"叫骰数量应在 1～{total_dice} 之间"}, 400
            old = STATE["dice"]["currentBid"]
            if old and not (quantity > old["quantity"] or (quantity == old["quantity"] and face > old["face"])):
                return {"error": "必须增加数量，或在数量相同时提高点数"}, 409
            STATE["dice"]["currentBid"] = {
                "quantity": quantity, "face": face, "playerId": player_id, "playerName": player["name"]
            }
            STATE["turnPlayerId"] = next_alive_id(player_id)
            bump()
            return {}, 200

        if action == "dice_challenge":
            if STATE["phase"] != "dice_bidding" or STATE["mode"] != "dice":
                return {"error": "当前不能开骰"}, 409
            if STATE["turnPlayerId"] != player_id:
                return {"error": "还没轮到你"}, 409
            bid = STATE["dice"]["currentBid"]
            if not bid:
                return {"error": "还没人叫骰"}, 409
            detail = dice_count_detail(bid["face"])
            STATE["dice"]["lastCount"] = detail
            actual = detail["total"]
            bidder = player_by_id(bid["playerId"])
            breakdown = f"本点 {detail['natural']} 个"
            if detail["wild"]:
                breakdown += f" + 万能1点 {detail['wild']} 个"
            claim = f"至少 {bid['quantity']} 个"
            if actual >= bid["quantity"]:
                loser_id = player_id
                result = f"上一家叫的是{claim}，实际 {actual} 个（{breakdown}），叫法成立；{player['name']} 质疑失败"
            else:
                loser_id = bidder["id"]
                result = f"上一家叫的是{claim}，实际仅 {actual} 个（{breakdown}）；{bidder['name']} 吹大了"
            finish_dice_round(loser_id, result)
            return {}, 200

        if action == "dice_exact":
            if not STATE["settings"]["exactEnabled"]:
                return {"error": "本局未开启抓准"}, 409
            if STATE["phase"] != "dice_bidding" or STATE["mode"] != "dice" or STATE["turnPlayerId"] != player_id:
                return {"error": "当前不能抓准"}, 409
            bid = STATE["dice"]["currentBid"]
            if not bid:
                return {"error": "还没人叫骰"}, 409
            detail = dice_count_detail(bid["face"])
            STATE["dice"]["lastCount"] = detail
            actual = detail["total"]
            breakdown = f"本点 {detail['natural']} 个"
            if detail["wild"]:
                breakdown += f" + 万能1点 {detail['wild']} 个"
            if actual == bid["quantity"]:
                old = player["diceCount"]
                player["diceCount"] = min(STATE["settings"]["diceStart"], player["diceCount"] + 1)
                result = f"正好 {actual} 个（{breakdown}），{player['name']} 抓准成功"
                if player["diceCount"] > old:
                    result += "，恢复 1 颗骰子"
                STATE["phase"] = "dice_reveal"
                STATE["turnPlayerId"] = None
                STATE["roundLoserId"] = player_id
                STATE["roundResult"] = result
                bump()
            else:
                finish_dice_round(player_id, f"叫数是 {bid['quantity']}，实际 {actual} 个（{breakdown}），{player['name']} 抓准失败")
            return {}, 200

        if action == "ddz_bid":
            if STATE["mode"] != "ddz" or STATE["phase"] != "ddz_bidding":
                return {"error": "当前不能叫地主"}, 409
            if STATE["turnPlayerId"] != player_id:
                return {"error": "还没轮到你"}, 409
            try:
                score = int(data.get("score", 0))
            except Exception:
                return {"error": "叫分无效"}, 400
            return apply_ddz_bid(player, score)

        if action == "ddz_hint":
            if STATE["mode"] != "ddz" or STATE["phase"] != "ddz_play" or STATE["turnPlayerId"] != player_id:
                return {"error": "当前不能提示"}, 409
            previous = STATE["ddz"]["lastPlay"]["combo"] if STATE["ddz"]["lastPlay"] else None
            options = ddz_hint_options(player["ddzHand"], previous)
            if not options:
                return {"hintCards": [], "message": "没有能压过上一手的牌"}, 200
            index = player.get("ddzHintCursor", 0) % len(options)
            player["ddzHintCursor"] = index + 1
            return {"hintCards": [card["id"] for card in options[index]]}, 200

        if action == "ddz_play":
            if STATE["mode"] != "ddz" or STATE["phase"] != "ddz_play":
                return {"error": "当前不能出牌"}, 409
            if STATE["turnPlayerId"] != player_id:
                return {"error": "还没轮到你"}, 409
            card_ids = data.get("cardIds", [])
            if not isinstance(card_ids, list) or not card_ids or len(set(card_ids)) != len(card_ids):
                return {"error": "请选择要出的牌"}, 400
            selected_ids = set(card_ids)
            selected = [card for card in player["ddzHand"] if card["id"] in selected_ids]
            if len(selected) != len(card_ids):
                return {"error": "所选牌已经变化，请重新选择"}, 409
            return apply_ddz_play(player, selected)

        if action == "ddz_pass":
            if STATE["mode"] != "ddz" or STATE["phase"] != "ddz_play":
                return {"error": "当前不能不出"}, 409
            if STATE["turnPlayerId"] != player_id:
                return {"error": "还没轮到你"}, 409
            return apply_ddz_pass(player)

        if action == "cm_exchange":
            if STATE["mode"] != "chuanma" or STATE["phase"] != "cm_exchange":
                return {"error": "当前不能换三张"}, 409
            tile_ids = data.get("tileIds", [])
            if not isinstance(tile_ids, list) or len(tile_ids) != 3 or len(set(tile_ids)) != 3:
                return {"error": "请选择三张牌"}, 400
            selected_set = set(tile_ids)
            selected = [tile for tile in player.get("cmHand", []) if tile["id"] in selected_set]
            if len(selected) != 3 or len({tile["suit"] for tile in selected}) != 1:
                return {"error": "换三张必须选择三张同花色的牌"}, 409
            STATE["chuanma"]["exchangeSelections"][player_id] = tile_ids
            player["cmExchange"] = list(tile_ids)
            humans = [item for item in STATE["players"] if not item.get("isBot")]
            if len(STATE["chuanma"]["exchangeSelections"]) >= len(humans):
                cm_finish_exchange()
            else:
                STATE["chuanma"]["message"] = f"{len(STATE['chuanma']['exchangeSelections'])}/{len(humans)} 人已选好换三张"
                bump()
            return {}, 200

        if action == "cm_dingque":
            if STATE["mode"] != "chuanma" or STATE["phase"] != "cm_dingque":
                return {"error": "当前不能定缺"}, 409
            suit = str(data.get("suit", ""))
            if suit not in CM_SUITS:
                return {"error": "请选择万、筒或条"}, 400
            player["cmMissing"] = suit
            STATE["chuanma"]["dingqueSelections"][player_id] = suit
            humans = [item for item in STATE["players"] if not item.get("isBot")]
            if len(STATE["chuanma"]["dingqueSelections"]) >= len(humans):
                cm_begin_play()
            else:
                STATE["chuanma"]["message"] = f"{len(STATE['chuanma']['dingqueSelections'])}/{len(humans)} 人已完成定缺"
                bump()
            return {}, 200

        if action == "cm_discard":
            if STATE["mode"] != "chuanma" or STATE["phase"] != "cm_play" or STATE["turnPlayerId"] != player_id:
                return {"error": "还没轮到你出牌"}, 409
            if not STATE["chuanma"].get("needsDiscard"):
                return {"error": "当前不需要出牌"}, 409
            tile_id = str(data.get("tileId", ""))
            tile = next((item for item in player.get("cmHand", []) if item["id"] == tile_id), None)
            if not tile:
                return {"error": "所选牌已经变化"}, 409
            missing = player.get("cmMissing")
            if missing and any(item["suit"] == missing for item in player["cmHand"]) and tile["suit"] != missing:
                return {"error": f"定缺为{CM_SUIT_LABEL[missing]}，请先打完缺门牌"}, 409
            player["cmHand"] = [item for item in player["cmHand"] if item["id"] != tile_id]
            player["cmDrawnId"] = None
            discard = {"playerId": player_id, "playerName": player["name"], "tile": tile}
            STATE["chuanma"]["discardPile"].append(discard)
            STATE["chuanma"]["lastDiscard"] = discard
            STATE["chuanma"]["discarderId"] = player_id
            STATE["chuanma"]["needsDiscard"] = False
            STATE["chuanma"]["message"] = f"{player['name']} 打出 {tile['rank']}{CM_SUIT_LABEL[tile['suit']]}"
            cm_offer_responses(player, tile)
            return {}, 200

        if action == "cm_respond":
            if STATE["mode"] != "chuanma" or STATE["phase"] != "cm_response":
                return {"error": "当前不需要响应"}, 409
            choice = str(data.get("choice", ""))
            allowed = STATE["chuanma"].get("responseOptions", {}).get(player_id, [])
            if choice not in allowed:
                return {"error": "该操作当前不可用"}, 409
            STATE["chuanma"]["responses"][player_id] = choice
            if all(pid in STATE["chuanma"]["responses"] for pid in STATE["chuanma"]["responseOptions"]):
                cm_resolve_responses()
            else:
                bump(False)
            return {}, 200

        if action == "cm_self_hu":
            if STATE["mode"] != "chuanma" or STATE["phase"] != "cm_play" or STATE["turnPlayerId"] != player_id:
                return {"error": "当前不能胡牌"}, 409
            if not cm_can_win(player):
                return {"error": "当前手牌不能胡"}, 409
            info = cm_win_info(player, self_draw=True)
            opponents = [item for item in cm_active_players() if item["id"] != player_id]
            for opponent in opponents:
                opponent["cmScore"] -= info["points"]
                player["cmScore"] += info["points"]
            player["cmWon"] = True
            STATE["chuanma"]["winRecords"].append({"winnerId": player_id, "fromId": None, "label": info["label"], "points": info["points"]})
            STATE["chuanma"]["message"] = f"{player['name']} 自摸（{info['label']}，每家{info['points']}分）"
            STATE["chuanma"]["needsDiscard"] = False
            if cm_check_end():
                return {}, 200
            next_id = cm_next_active_id(player_id)
            if next_id:
                cm_draw_for(next_id)
            return {}, 200

        if action == "cm_gang":
            if STATE["mode"] != "chuanma" or STATE["phase"] != "cm_play" or STATE["turnPlayerId"] != player_id:
                return {"error": "当前不能杠"}, 409
            suit = str(data.get("suit", ""))
            try:
                rank = int(data.get("rank", 0))
            except Exception:
                rank = 0
            option = next((item for item in cm_self_gang_options(player) if item["suit"] == suit and item["rank"] == rank), None)
            if not option:
                return {"error": "所选牌不能杠"}, 409
            if option["kind"] == "concealed":
                removed = 0
                rest = []
                for tile in player["cmHand"]:
                    if tile["suit"] == suit and int(tile["rank"]) == rank and removed < 4:
                        removed += 1
                    else:
                        rest.append(tile)
                player["cmHand"] = rest
                player["cmMelds"].append({"type": "gang", "suit": suit, "rank": rank, "kind": "concealed", "fromId": None})
                cm_score_gang(player, "concealed")
                STATE["chuanma"]["message"] = f"{player['name']} 暗杠"
            else:
                removed = False
                rest = []
                for tile in player["cmHand"]:
                    if not removed and tile["suit"] == suit and int(tile["rank"]) == rank:
                        removed = True
                    else:
                        rest.append(tile)
                player["cmHand"] = rest
                meld = next(item for item in player["cmMelds"] if item["type"] == "peng" and item["suit"] == suit and int(item["rank"]) == rank)
                meld["type"] = "gang"; meld["kind"] = "added"
                cm_score_gang(player, "added")
                STATE["chuanma"]["message"] = f"{player['name']} 补杠"
            player["cmDrawnId"] = None
            STATE["chuanma"]["needsDiscard"] = False
            cm_draw_for(player_id)
            return {}, 200

        if action == "draw_choose":
            if STATE["mode"] != "draw" or STATE["phase"] != "draw_choose" or STATE["draw"]["drawerId"] != player_id:
                return {"error": "当前不能选题"}, 409
            try:
                index = int(data.get("index", 0))
            except Exception:
                index = 0
            begin_draw_word(index); return {}, 200

        if action == "draw_stroke":
            if STATE["mode"] != "draw" or STATE["phase"] != "draw_play" or STATE["draw"]["drawerId"] != player_id:
                return {"error": "当前不能作画"}, 409
            points = data.get("points", [])
            if not isinstance(points, list) or not points or len(points) > 120:
                return {"error": "笔画数据无效"}, 400
            clean = []
            last = None
            for point in points:
                if isinstance(point, list) and len(point) == 2:
                    try:
                        x = max(0.0, min(1.0, float(point[0])))
                        y = max(0.0, min(1.0, float(point[1])))
                        current = [round(x, 4), round(y, 4)]
                        if last is None or abs(current[0] - last[0]) + abs(current[1] - last[1]) >= 0.0025:
                            clean.append(current)
                            last = current
                    except Exception:
                        pass
            if not clean:
                return {"error": "笔画数据无效"}, 400
            color = str(data.get("color", "#111111"))
            if color not in ("#111111", "#e05555", "#3478d4", "#35a36f", "#f0b72f"):
                color = "#111111"
            width = max(2, min(16, int(data.get("width", 7))))
            STATE["draw"]["strokeSeq"] += 1
            stroke = {
                "seq": STATE["draw"]["strokeSeq"],
                "color": color,
                "width": width,
                "erase": bool(data.get("erase", False)),
                "points": clean,
            }
            STATE["draw"]["strokes"].append(stroke)
            if len(STATE["draw"]["strokes"]) > 260:
                STATE["draw"]["strokes"] = STATE["draw"]["strokes"][-260:]
                STATE["draw"]["canvasRevision"] += 1
            bump(False)
            return {"strokeSeq": STATE["draw"]["strokeSeq"], "canvasRevision": STATE["draw"]["canvasRevision"]}, 200

        if action == "draw_undo":
            if STATE["mode"] != "draw" or STATE["phase"] != "draw_play" or STATE["draw"]["drawerId"] != player_id:
                return {"error": "当前不能撤销"}, 409
            if STATE["draw"]["strokes"]:
                STATE["draw"]["strokes"].pop()
                STATE["draw"]["canvasRevision"] += 1
                bump(False)
            return {}, 200

        if action == "draw_clear":
            if STATE["mode"] != "draw" or STATE["phase"] != "draw_play" or STATE["draw"]["drawerId"] != player_id:
                return {"error": "当前不能清空"}, 409
            STATE["draw"]["strokes"] = []
            STATE["draw"]["strokeSeq"] = 0
            STATE["draw"]["canvasRevision"] += 1
            bump(False)
            return {}, 200

        if action == "draw_guess":
            if STATE["mode"] != "draw" or STATE["phase"] != "draw_play":
                return {"error": "当前不能猜题"}, 409
            if STATE["draw"]["drawerId"] == player_id:
                return {"error": "画家不能猜自己的题"}, 409
            if player_id in STATE["draw"]["correctIds"]:
                return {"error": "你已经猜对了"}, 409
            guess = str(data.get("guess", "")).strip()[:20]
            if not guess:
                return {"error": "请输入答案"}, 400
            targets = [STATE["draw"]["word"]] + list(STATE["draw"]["aliases"])
            correct = normalize_guess(guess) in {normalize_guess(item) for item in targets}
            STATE["draw"]["guesses"].append({"name": player["name"], "text": guess, "correct": correct})
            if len(STATE["draw"]["guesses"]) > 40:
                STATE["draw"]["guesses"] = STATE["draw"]["guesses"][-40:]
            if correct:
                STATE["draw"]["correctIds"].append(player_id)
                remaining = max(0, int(STATE["draw"]["deadline"] - time.time()))
                player["score"] += 100 + min(80, remaining)
                drawer = player_by_id(STATE["draw"]["drawerId"])
                if drawer:
                    drawer["score"] += 50
                humans = [item for item in STATE["players"] if not item.get("isBot")]
                if len(STATE["draw"]["correctIds"]) >= len(humans) - 1:
                    end_draw_turn("all")
                    return {}, 200
            bump(); return {}, 200

        if action == "next_round":
            if STATE["phase"] not in ("cards_reveal", "dice_reveal", "draw_reveal"):
                return {"error": "当前不能开始下一轮"}, 409
            if STATE["mode"] == "draw":
                if player_id not in (STATE["hostPlayerId"], STATE["draw"]["drawerId"]):
                    return {"error": "由房主或本题画家继续"}, 403
                STATE["draw"]["turnIndex"] += 1
                start_draw_turn()
                return {}, 200
            if player_id not in (STATE["hostPlayerId"], STATE["roundLoserId"]):
                return {"error": "由房主或本轮受罚者继续"}, 403
            starter = STATE["roundLoserId"]; starter_player = player_by_id(starter)
            if not starter_player or is_out(starter_player):
                starter = next_alive_id(starter)
            if STATE["mode"] == "cards": start_cards_round(starter)
            else: start_dice_round(starter)
            return {}, 200

        if action == "reset":
            if player_id != STATE["hostPlayerId"]:
                return {"error": "只有房主能返回大厅"}, 403
            remove_ddz_bots()
            STATE.update({"phase": "lobby", "turnPlayerId": None, "roundNo": 0, "roundLoserId": None, "roundResult": "", "winnerId": None})
            STATE["card"] = {"targetRank": "Q", "lastPlay": None, "revealedCards": []}
            STATE["dice"] = {"currentBid": None, "lastCount": None}; STATE["draw"] = fresh_draw(); STATE["ddz"] = fresh_ddz(); STATE["chuanma"] = fresh_chuanma()
            for item in STATE["players"]:
                item["life"] = STATE["settings"]["cardLives"]; item["hand"] = []
                item["diceCount"] = STATE["settings"]["diceStart"]; item["dice"] = []; item["score"] = 0
                item["ddzHand"] = []; item["ddzScore"] = 0; item["ddzHintCursor"] = 0
                item["cmHand"] = []; item["cmMelds"] = []; item["cmMissing"] = None; item["cmWon"] = False; item["cmScore"] = 0; item["cmDrawnId"] = None; item["cmExchange"] = []
            bump(); return {}, 200

        return {"error": "未知操作"}, 400

def local_ipv4_addresses():
    addresses = []
    if fcntl is None:
        return addresses
    try:
        for _, name in socket.if_nameindex():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                packed = struct.pack("256s", name[:15].encode("utf-8"))
                result = fcntl.ioctl(sock.fileno(), 0x8915, packed)
                ip = socket.inet_ntoa(result[20:24])
                if not ip.startswith("127.") and ip not in addresses:
                    addresses.append(ip)
            except OSError:
                pass
            finally:
                sock.close()
    except Exception:
        pass
    return addresses

if __name__ == "__main__":
    print("=" * 62)
    print("局域网游戏厅 v6.2（大话骰规则校验与正常词库版）已启动")
    print(f"房主本机打开：http://127.0.0.1:{PORT}")
    addresses = local_ipv4_addresses()
    for address in addresses:
        print(f"其他玩家打开：http://{address}:{PORT}")
    if not addresses:
        print("其他玩家请使用热点详情中的“网关地址:8000”")
    print("停止服务器：音量减 + C，或 Ctrl+C")
    print("=" * 62)
    server = ReliableThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        flush_state()
        print("\n服务器已停止")
