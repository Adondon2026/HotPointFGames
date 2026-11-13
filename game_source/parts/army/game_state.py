import copy
import random
import time
import uuid
from datetime import datetime
import rules
import topology


class GameState:
    def __init__(self, room_rules=None):
        self.room_rules = room_rules or {
            "victory_mode": "capture",
            "first_player": "host",
            "mountains": True,
            "allow_annotations": True,
        }
        self.phase = "setup"
        self.turn = 0
        self.winner = None
        self.draw = False
        self.message = "等待双方摆阵。"
        self.setups = {}
        self.board = {}
        self.ground_flags = {}  # node -> 原属玩家
        self.logs = []
        self.history = []
        self.pending_request = None
        self.last_move_trace = None
        self._piece_id = 0
        self.game_id = None
        self.game_started_at = None
        self.first_turn = None
        self.replay_nodes = []
        self.active_replay_ids = []
        self.branch_counts = {}
        self.initial_replay_frame = None
        self.actual_move_count = 0
        self.successful_undos = [0, 0]
        self.resignation_by = None
        self.commander_bombed = [False, False]
        self.mines_by_engineer = [0, 0]
        self.mines_by_bomb = [0, 0]
        self.capture_count = [0, 0]
        self.engineer_reveal_count = [0, 0]


    def _snapshot(self):
        return {
            "phase": self.phase,
            "turn": self.turn,
            "winner": self.winner,
            "draw": self.draw,
            "message": self.message,
            "board": copy.deepcopy(self.board),
            "ground_flags": copy.deepcopy(self.ground_flags),
            "logs": copy.deepcopy(self.logs),
            "last_move_trace": copy.deepcopy(self.last_move_trace),
        }

    def _restore(self, snap):
        self.phase = snap["phase"]
        self.turn = snap["turn"]
        self.winner = snap["winner"]
        self.draw = snap["draw"]
        self.message = snap["message"]
        self.board = copy.deepcopy(snap["board"])
        self.ground_flags = copy.deepcopy(snap["ground_flags"])
        self.logs = copy.deepcopy(snap["logs"])
        self.last_move_trace = copy.deepcopy(snap.get("last_move_trace"))

    def reset(self):
        self.phase = "setup"
        self.turn = 0
        self.winner = None
        self.draw = False
        self.message = "重新开始，请双方重新摆阵。"
        self.setups = {}
        self.board = {}
        self.ground_flags = {}
        self.logs = []
        self.history = []
        self.pending_request = None
        self.last_move_trace = None
        self._piece_id = 0
        self.game_id = None
        self.game_started_at = None
        self.first_turn = None
        self.replay_nodes = []
        self.active_replay_ids = []
        self.branch_counts = {}
        self.initial_replay_frame = None
        self.actual_move_count = 0
        self.successful_undos = [0, 0]
        self.resignation_by = None
        self.commander_bombed = [False, False]
        self.mines_by_engineer = [0, 0]
        self.mines_by_bomb = [0, 0]
        self.capture_count = [0, 0]
        self.engineer_reveal_count = [0, 0]

    def submit_setup(self, player, setup):
        if self.phase != "setup":
            return False, "当前不是摆阵阶段。"
        err = rules.validate_setup(player, setup)
        if err:
            return False, err
        self.setups[player] = copy.deepcopy(setup)
        self.message = f"玩家 {player + 1} 已准备。"
        if 0 in self.setups and 1 in self.setups:
            self._start()
        return True, ""

    def _start(self):
        self.board = {}
        self.last_move_trace = None
        for player in (0, 1):
            for item in self.setups[player]:
                node = (int(item["r"]), int(item["c"]))
                self.board[node] = {
                    "id": self._piece_id,
                    "owner": player,
                    "rank": str(item["rank"]),
                    "revealed_to": [],
                    "carrying_flag_owner": None,
                }
                self._piece_id += 1

        fp = self.room_rules.get("first_player", "host")
        if fp == "guest":
            self.turn = 1
        elif fp == "random":
            self.turn = random.randint(0, 1)
        else:
            self.turn = 0
        self.first_turn = self.turn
        self.game_id = uuid.uuid4().hex
        self.game_started_at = time.time()
        self.replay_nodes = []
        self.active_replay_ids = []
        self.branch_counts = {}
        self.initial_replay_frame = None
        self.actual_move_count = 0
        self.successful_undos = [0, 0]
        self.resignation_by = None
        self.commander_bombed = [False, False]
        self.mines_by_engineer = [0, 0]
        self.mines_by_bomb = [0, 0]
        self.capture_count = [0, 0]
        self.engineer_reveal_count = [0, 0]
        self.phase = "play"
        self.winner = None
        self.draw = False
        self.message = f"对局开始，玩家 {self.turn + 1} 先手。"

        # 复盘第0步：双方刚完成摆阵、还没有任何棋子移动的初始状态。
        # 此时 last_move_trace 为 None，所有规则公开信息也处于开局状态。
        self.initial_replay_frame = self._truth_frame()

    def _piece_name_for(self, piece, viewer):
        if piece["owner"] == viewer:
            return piece["rank"]
        if viewer in piece.get("revealed_to", []):
            return piece["rank"]
        return "暗棋"

    def _reveal_piece(self, piece, viewer):
        if viewer not in piece["revealed_to"]:
            piece["revealed_to"].append(viewer)

    def _reveal_flag(self, owner):
        for piece in self.board.values():
            if piece["owner"] == owner and piece["rank"] == "军旗":
                self._reveal_piece(piece, 1 - owner)

    def _check_commander_death(self, dead_piece):
        if dead_piece and dead_piece["rank"] == "司令":
            self._reveal_flag(dead_piece["owner"])

    def _add_log(self, entry):
        self.logs.append(entry)
        self.logs = self.logs[-20:]

    def _drop_carried_flag(self, piece, node):
        flag_owner = piece.get("carrying_flag_owner")
        if flag_owner is not None:
            self.ground_flags[node] = flag_owner
            piece["carrying_flag_owner"] = None

    def _capture_or_pick_flag(self, piece, node, flag_owner):
        mode = self.room_rules["victory_mode"]
        if mode == "capture":
            self.phase = "over"
            self.winner = piece["owner"]
            self.message = f"玩家 {piece['owner'] + 1} 攻占军旗，获得胜利！"
            return "WIN"

        if piece["rank"] == "炸弹":
            return "BOMB_CANNOT_CARRY"

        piece["carrying_flag_owner"] = flag_owner
        self.ground_flags.pop(node, None)
        return "CARRY"

    def move(self, player, src, dst):
        if self.phase != "play":
            return False, "当前不是对局阶段。"
        if self.pending_request:
            return False, "当前有待处理请求。"
        if player != self.turn:
            return False, "现在不是你的回合。"

        ok, err, reveal_engineer, actual_path = rules.movement_details(
            self.board, player, src, dst, self.room_rules.get("mountains", True)
        )
        if not ok:
            return False, err

        attacker = self.board[src]
        mode = self.room_rules["victory_mode"]

        # 自己掉落的军旗不可拾取，也不能踩在上面。
        if dst in self.ground_flags and self.ground_flags[dst] == player:
            return False, "己方掉落军旗不能背起，也不能占据其位置。"
        if (
            dst in self.ground_flags
            and self.ground_flags[dst] != player
            and mode == "return"
            and attacker["rank"] == "炸弹"
        ):
            return False, "炸弹不能背军旗。"

        # 悔棋快照保存“上一手”的轨迹；本手轨迹随后覆盖。
        self.history.append(self._snapshot())
        self.last_move_trace = {
            "player": player,
            "piece_id": attacker["id"],
            "path": [self._node_json(node) for node in actual_path],
        }

        if reveal_engineer:
            was_known = (1 - player) in attacker.get("revealed_to", [])
            self._reveal_piece(attacker, 1 - player)
            if not was_known:
                self.engineer_reveal_count[player] += 1

        attacker_name = attacker["rank"]
        target_piece = self.board.get(dst)
        event = {
            "type": "move",
            "player": player,
            "attacker_id": attacker["id"],
            "attacker_rank": attacker["rank"],
            "defender_id": target_piece["id"] if target_piece else None,
            "defender_rank": target_piece["rank"] if target_piece else None,
            "src": self._node_json(src),
            "dst": self._node_json(dst),
            "result": "move",
        }

        # v0.5 statistics: count actual interactions, including later-undone branches.
        if target_piece is not None:
            if attacker["rank"] == "炸弹" and target_piece["rank"] == "司令":
                self.commander_bombed[target_piece["owner"]] = True
            if target_piece["rank"] == "地雷" and attacker["rank"] in {"工兵", "炸弹"}:
                if attacker["rank"] == "工兵":
                    self.mines_by_engineer[player] += 1
                else:
                    self.mines_by_bomb[player] += 1
            if target_piece["owner"] != player:
                self.capture_count[player] += 1

        if target_piece is None:
            del self.board[src]
            self.board[dst] = attacker

            # 掉落军旗
            if dst in self.ground_flags and self.ground_flags[dst] != player:
                flag_owner = self.ground_flags[dst]
                res = self._capture_or_pick_flag(attacker, dst, flag_owner)
                event["result"] = "capture_flag" if res == "WIN" else "pick_flag"
            else:
                event["result"] = "move"

        else:
            defender = target_piece

            # 原始敌方军旗
            if defender["rank"] == "军旗":
                if mode == "return" and attacker["rank"] == "炸弹":
                    self.history.pop()
                    return False, "背回军旗模式下，炸弹不能夺取军旗。"

                del self.board[src]
                del self.board[dst]
                self.board[dst] = attacker
                res = self._capture_or_pick_flag(attacker, dst, defender["owner"])
                event["result"] = "capture_flag" if res == "WIN" else "pick_flag"

            else:
                result = rules.battle_result(attacker["rank"], defender["rank"])
                event["result"] = result.lower()

                if result == "ATTACKER":
                    self._check_commander_death(defender)
                    self._drop_carried_flag(defender, dst)
                    del self.board[src]
                    del self.board[dst]
                    self.board[dst] = attacker

                elif result == "DEFENDER":
                    self._check_commander_death(attacker)
                    self._drop_carried_flag(attacker, dst)
                    del self.board[src]

                elif result == "BOTH":
                    self._check_commander_death(attacker)
                    self._check_commander_death(defender)
                    # 两边携带旗都掉在战斗位置；理论上同一点只允许一面，
                    # 若同时出现，以攻击方携带旗最后写入；极端局面不影响基本玩法。
                    self._drop_carried_flag(defender, dst)
                    self._drop_carried_flag(attacker, dst)
                    del self.board[src]
                    del self.board[dst]

        self._add_log(event)

        # 背旗者到达己方任意大本营
        if self.phase == "play" and dst in self.board:
            survivor = self.board[dst]
            flag_owner = survivor.get("carrying_flag_owner")
            if (
                flag_owner is not None
                and flag_owner != survivor["owner"]
                and dst in topology.hq_for(survivor["owner"])
            ):
                self.phase = "over"
                self.winner = survivor["owner"]
                self.message = f"玩家 {self.winner + 1} 将敌方军旗背回大本营，获胜！"
                event["result"] = "return_flag"

        if self.phase == "play":
            self.turn = 1 - self.turn
            self._check_terminal()
            if self.phase == "play":
                self.message = f"玩家 {player + 1} 已行动。"

        self.actual_move_count += 1
        self._record_replay_frame(player, event)
        return True, ""

    def _check_terminal(self):
        for owner in (0, 1):
            pieces = [p for p in self.board.values() if p["owner"] == owner]
            if not pieces:
                self.phase = "over"
                self.winner = 1 - owner
                self.message = f"玩家 {owner + 1} 已被完全消灭。"
                return

        if not rules.has_any_move(
            self.board, self.turn,
            self.room_rules.get("mountains", True),
            self.ground_flags,
            self.room_rules["victory_mode"],
        ):
            self.phase = "over"
            self.winner = 1 - self.turn
            self.message = f"玩家 {self.turn + 1} 已无棋可走。"

    def resign(self, player):
        if self.phase != "play":
            return False, "当前不能认输。"
        self.phase = "over"
        self.winner = 1 - player
        self.resignation_by = player
        self.message = f"玩家 {player + 1} 认输。"
        return True, ""

    def request(self, player, kind):
        if self.phase != "play":
            return False, "当前不能发送请求。"
        if self.pending_request:
            return False, "已有待处理请求。"
        if kind not in {"draw", "undo"}:
            return False, "未知请求。"
        if kind == "undo" and not self.history:
            return False, "目前没有可以撤销的行动。"
        self.pending_request = {"type": kind, "from": player}
        return True, ""

    def respond(self, player, accept):
        req = self.pending_request
        if not req:
            return False, "没有待处理请求。"
        if req["from"] == player:
            return False, "不能响应自己的请求。"

        kind = req["type"]
        self.pending_request = None

        if not accept:
            self.message = "请求已被拒绝。"
            return True, ""

        if kind == "draw":
            self.phase = "over"
            self.winner = None
            self.draw = True
            self.message = "双方同意和棋。"
            return True, ""

        if kind == "undo":
            if not self.history:
                return False, "没有可恢复的历史。"
            requester = req["from"]
            if self.active_replay_ids:
                self.active_replay_ids.pop()
            self.successful_undos[requester] += 1
            snap = self.history.pop()
            self._restore(snap)
            self.pending_request = None
            self.message = "双方同意悔棋，已撤销最近一步。"
            return True, ""

        return False, "未知请求。"

    def _truth_frame(self):
        pieces = []
        for node, p in self.board.items():
            pieces.append({
                "node": self._node_json(node),
                "id": p["id"],
                "owner": p["owner"],
                "rank": p["rank"],
                "revealed_to": list(p.get("revealed_to", [])),
                "carrying_flag": p.get("carrying_flag_owner") is not None,
            })
        return {
            "pieces": pieces,
            "ground_flags": [
                {"node": self._node_json(node), "owner": owner}
                for node, owner in self.ground_flags.items()
            ],
            "turn": self.turn,
            "message": self.message,
            "last_move_trace": copy.deepcopy(self.last_move_trace),
            "room_rules": copy.deepcopy(self.room_rules),
        }

    def _record_replay_frame(self, player, event):
        logical_step = len(self.active_replay_ids) + 1
        branch_index = self.branch_counts.get(logical_step, 0) + 1
        self.branch_counts[logical_step] = branch_index
        node_id = len(self.replay_nodes)
        parent_id = self.active_replay_ids[-1] if self.active_replay_ids else None
        node = {
            "node_id": node_id,
            "parent_id": parent_id,
            "logical_step": logical_step,
            "branch_index": branch_index,
            "player": player,
            "event": copy.deepcopy(event),
            "frame": self._truth_frame(),
        }
        self.replay_nodes.append(node)
        self.active_replay_ids.append(node_id)

    def replay_export(self):
        counts = {}
        for n in self.replay_nodes:
            counts[n["logical_step"]] = counts.get(n["logical_step"], 0) + 1

        active = set(self.active_replay_ids)
        result = []

        # 第0步：初始摆阵状态。
        # node_id=-1 只用于复盘展示，不参与悔棋分支树。
        if self.initial_replay_frame is not None:
            result.append({
                "node_id": -1,
                "parent_id": None,
                "logical_step": 0,
                "branch_index": 0,
                "player": None,
                "event": None,
                "frame": copy.deepcopy(self.initial_replay_frame),
                "label": "0",
                "active_branch": True,
            })

        for n in self.replay_nodes:
            step = n["logical_step"]
            label = str(step) if counts.get(step, 0) == 1 else f"{step}-{n['branch_index']}"
            item = copy.deepcopy(n)
            item["label"] = label
            item["active_branch"] = n["node_id"] in active
            result.append(item)

        return result

    def final_summary_for(self, viewer):
        if self.phase != "over" or not self.game_id:
            return None
        duration = max(0.0, time.time() - (self.game_started_at or time.time()))
        if self.draw:
            winner = "none"
        elif self.winner == viewer:
            winner = "self"
        else:
            winner = "opponent"
        if self.resignation_by is None:
            resignation = "none"
        elif self.resignation_by == viewer:
            resignation = "self"
        else:
            resignation = "opponent"
        return {
            "game_id": self.game_id,
            "total_steps": len(self.active_replay_ids),
            "winner": winner,
            "draw": bool(self.draw),
            "resignation": resignation,
            "self_undo_count": self.successful_undos[viewer],
            "opponent_undo_count": self.successful_undos[1-viewer],
            "self_commander_attacked_by_enemy_bomb": self.commander_bombed[viewer],
            "enemy_commander_attacked_by_self_bomb": self.commander_bombed[1-viewer],
            "self_mines_destroyed_by_engineer_or_bomb": self.mines_by_engineer[viewer] + self.mines_by_bomb[viewer],
            "actual_move_count_including_undone": self.actual_move_count,
            "date_time": datetime.now().isoformat(timespec="seconds"),
            "game_duration_seconds": round(duration, 1),
            "victory_mode": self.room_rules.get("victory_mode"),
            "first_player": self.first_turn,
            "self_was_first": self.first_turn == viewer,
            "mountains_enabled": self.room_rules.get("mountains", True),
            "annotations_enabled": self.room_rules.get("allow_annotations", True),
            "self_capture_count": self.capture_count[viewer],
            "opponent_capture_count": self.capture_count[1-viewer],
            "self_engineer_mines_destroyed": self.mines_by_engineer[viewer],
            "self_bomb_mines_destroyed": self.mines_by_bomb[viewer],
            "self_engineer_reveal_count": self.engineer_reveal_count[viewer],
            "opponent_engineer_reveal_count": self.engineer_reveal_count[1-viewer],
        }

    def _node_json(self, node):
        if isinstance(node, tuple):
            return [node[0], node[1]]
        return node

    def _node_from_json(self, value):
        if isinstance(value, list):
            return (int(value[0]), int(value[1]))
        return value

    def _log_for(self, viewer, entry):
        if entry["type"] != "move":
            return ""

        # 根据当前公开状态查棋子；被消灭的棋可能已不存在，所以对方永不从日志泄密。
        def name(piece_id, owner, rank):
            if owner == viewer:
                return rank
            for p in self.board.values():
                if p["id"] == piece_id and viewer in p.get("revealed_to", []):
                    return p["rank"]
            return "暗棋"

        attacker_owner = entry["player"]
        a = name(entry["attacker_id"], attacker_owner, entry["attacker_rank"])
        src, dst = entry["src"], entry["dst"]
        result = entry["result"]

        if entry["defender_id"] is None:
            if result == "pick_flag":
                return f"{'我方' if attacker_owner == viewer else '敌方'}{a}夺取并背起军旗"
            if result in {"capture_flag", "return_flag"}:
                return f"{'我方' if attacker_owner == viewer else '敌方'}{a}完成军旗目标"
            return f"{'我方' if attacker_owner == viewer else '敌方'}{a}移动"

        defender_owner = 1 - attacker_owner
        d = name(entry["defender_id"], defender_owner, entry["defender_rank"])
        side_a = "我方" if attacker_owner == viewer else "敌方"
        side_d = "我方" if defender_owner == viewer else "敌方"

        mapping = {
            "attacker": "进攻方胜",
            "defender": "防守方胜",
            "both": "同归于尽",
            "capture_flag": "攻占军旗",
            "pick_flag": "背起军旗",
        }
        return f"{side_a}{a}攻击{side_d}{d}：{mapping.get(result, result)}"

    def view_for(self, player):
        pieces = []
        for node, p in self.board.items():
            rank = p["rank"] if p["owner"] == player or player in p.get("revealed_to", []) else "UNKNOWN"
            pieces.append({
                "node": self._node_json(node),
                "id": p["id"],
                "owner": p["owner"],
                "rank": rank,
                "carrying_flag": p.get("carrying_flag_owner") is not None,
            })

        flags = [
            {"node": self._node_json(node), "owner": owner}
            for node, owner in self.ground_flags.items()
        ]

        req = copy.deepcopy(self.pending_request)
        replay_full = self.replay_export() if self.phase == "over" else None
        final_summary = self.final_summary_for(player) if self.phase == "over" else None
        return {
            "phase": self.phase,
            "turn": self.turn,
            "winner": self.winner,
            "draw": self.draw,
            "message": self.message,
            "pieces": pieces,
            "ground_flags": flags,
            "ready": [0 in self.setups, 1 in self.setups],
            "room_rules": copy.deepcopy(self.room_rules),
            "pending_request": req,
            "logs": [self._log_for(player, e) for e in self.logs[-5:]],
            "last_move_trace": copy.deepcopy(self.last_move_trace),
            "replay_full": replay_full,
            "final_summary": final_summary,
        }
