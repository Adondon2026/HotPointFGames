from collections import Counter, deque
import topology

PIECE_COUNTS = {
    "司令": 1, "军长": 1, "师长": 2, "旅长": 2,
    "团长": 2, "营长": 2, "连长": 3, "排长": 3,
    "工兵": 3, "地雷": 3, "炸弹": 2, "军旗": 1,
}
PIECE_ORDER = list(PIECE_COUNTS.keys())

POWER = {
    "司令": 9, "军长": 8, "师长": 7, "旅长": 6,
    "团长": 5, "营长": 4, "连长": 3, "排长": 2, "工兵": 1,
}


def is_owner_area(owner, node):
    if not topology.is_station(node):
        return False
    r, _ = node
    return 0 <= r <= 5 if owner == 0 else 6 <= r <= 11


def is_deployable(owner, node):
    return is_owner_area(owner, node) and not topology.is_camp(node)


def is_rear_row(owner, node):
    if not topology.is_station(node):
        return False
    r, _ = node
    return r in ({0, 1} if owner == 0 else {10, 11})


def is_front_row(owner, node):
    if not topology.is_station(node):
        return False
    return node[0] == (5 if owner == 0 else 6)


def movable(rank):
    return rank not in {"地雷", "军旗"}


def validate_setup(owner, setup):
    if len(setup) != 25:
        return "必须摆放全部25枚棋子。"

    counts = Counter()
    occupied = set()

    for item in setup:
        try:
            node = (int(item["r"]), int(item["c"]))
            rank = str(item["rank"])
        except Exception:
            return "摆阵数据格式错误。"

        if rank not in PIECE_COUNTS:
            return f"未知棋子：{rank}"
        if not is_deployable(owner, node):
            return "棋子位于非法部署位置。"
        if node in occupied:
            return "同一位置不能摆两枚棋子。"

        occupied.add(node)
        counts[rank] += 1

        if rank == "军旗" and node not in topology.hq_for(owner):
            return "军旗必须放在大本营。"
        if rank == "地雷" and not is_rear_row(owner, node):
            return "地雷必须放在最后两排。"
        if rank == "炸弹" and is_front_row(owner, node):
            return "炸弹不能放在最前排。"

    for rank, count in PIECE_COUNTS.items():
        if counts[rank] != count:
            return f"{rank} 数量错误，应为 {count}。"

    return ""


def random_setup(owner, rng):
    free = [
        (r, c) for r in range(topology.ROWS) for c in range(topology.COLS)
        if is_deployable(owner, (r, c))
    ]
    result = []

    hqs = list(topology.hq_for(owner))
    rng.shuffle(hqs)
    flag = hqs[0]
    result.append({"r": flag[0], "c": flag[1], "rank": "军旗"})
    free.remove(flag)

    rear = [p for p in free if is_rear_row(owner, p)]
    rng.shuffle(rear)
    for p in rear[:3]:
        result.append({"r": p[0], "c": p[1], "rank": "地雷"})
        free.remove(p)

    bombs = [p for p in free if not is_front_row(owner, p)]
    rng.shuffle(bombs)
    for p in bombs[:2]:
        result.append({"r": p[0], "c": p[1], "rank": "炸弹"})
        free.remove(p)

    remaining = []
    for rank, count in PIECE_COUNTS.items():
        if rank in {"军旗", "地雷", "炸弹"}:
            continue
        remaining += [rank] * count
    rng.shuffle(remaining)
    rng.shuffle(free)

    for rank, p in zip(remaining, free):
        result.append({"r": p[0], "c": p[1], "rank": rank})
    return result


def battle_result(attacker, defender):
    if defender == "军旗":
        return "FLAG"
    if attacker == "炸弹" or defender == "炸弹":
        return "BOTH"
    if defender == "地雷":
        return "ATTACKER" if attacker == "工兵" else "DEFENDER"
    if attacker in {"地雷", "军旗"}:
        return "DEFENDER"
    ap, dp = POWER[attacker], POWER[defender]
    return "ATTACKER" if ap > dp else "DEFENDER" if ap < dp else "BOTH"


def _hq_locked(piece, src):
    # 任何棋子一旦进入大本营都不能离开。
    return topology.is_hq(src)


def _direction(a, b):
    """相邻铁路节点 a->b 的标准方向，用于判断工兵是否转弯。"""
    return (
        0 if b[0] == a[0] else (1 if b[0] > a[0] else -1),
        0 if b[1] == a[1] else (1 if b[1] > a[1] else -1),
    )


def _sorted_nodes(nodes):
    """铁路节点均为 tuple；固定排序保证多条等长路径时结果稳定。"""
    return sorted(nodes, key=lambda n: (n[0], n[1]))


def _normal_rail_path(board, src, dst):
    """普通棋沿同一条直线铁路的最短实际路径；不可转弯。"""
    if not topology.is_rail_node(src) or not topology.is_rail_node(dst):
        return None

    if src[0] != dst[0] and src[1] != dst[1]:
        return None

    q = deque([(src, [src])])
    seen = {src}

    while q:
        cur, path = q.popleft()

        if cur == dst:
            return path

        for nxt in _sorted_nodes(topology.rail_neighbors(cur)):
            if nxt in seen:
                continue

            # 普通棋只能保持在起终点所在的同一直线上。
            if src[0] == dst[0] and nxt[0] != src[0]:
                continue
            if src[1] == dst[1] and nxt[1] != src[1]:
                continue

            # 目标敌棋允许作为终点；其他棋子均不可穿过。
            if nxt != dst and nxt in board:
                continue

            seen.add(nxt)
            q.append((nxt, path + [nxt]))

    return None


def _engineer_rail_path(board, src, dst):
    """
    工兵铁路 BFS。
    返回 (path, turned)；path 为实际经过的铁路节点，选择边数最少的合法路径。
    """
    if not topology.is_rail_node(src) or not topology.is_rail_node(dst):
        return None, False

    q = deque([(src, None, False, [src])])
    seen = {(src, None)}

    while q:
        cur, prev_dir, turned, path = q.popleft()

        for nxt in _sorted_nodes(topology.rail_neighbors(cur)):
            # 最终敌棋可以攻击；中间任何棋都不能穿过。
            if nxt != dst and nxt in board:
                continue

            direction = _direction(cur, nxt)
            new_turned = turned or (
                prev_dir is not None and direction != prev_dir
            )

            if nxt == dst:
                return path + [nxt], new_turned

            state = (nxt, direction)
            if state in seen:
                continue

            seen.add(state)
            q.append((nxt, direction, new_turned, path + [nxt]))

    return None, False


def _engineer_path_to_mountain(board, src, mountain):
    """
    工兵从当前铁路位置到山界。
    只走铁路；到六个入口中最先到达的一个后，同一步进入山界。
    """
    entries = set(topology.mountain_neighbors(mountain))

    if src in entries:
        return [src, mountain]

    q = deque([(src, [src])])
    seen = {src}

    while q:
        cur, path = q.popleft()

        for nxt in _sorted_nodes(topology.rail_neighbors(cur)):
            if nxt in seen:
                continue

            # 入口及中间点都不能被其他棋子占据。
            if nxt in board:
                continue

            new_path = path + [nxt]

            if nxt in entries:
                return new_path + [mountain]

            seen.add(nxt)
            q.append((nxt, new_path))

    return None


def _engineer_path_from_mountain(board, mountain, dst):
    """
    工兵离开山界。
    六个入口同时作为虚拟起点；之后整步只能继续沿铁路。
    返回 [mountain, chosen_entry, ..., dst]。
    """
    entries = _sorted_nodes(topology.mountain_neighbors(mountain))

    # 若目标本身是入口，可一步直接离开到该入口。
    if dst in entries:
        return [mountain, dst]

    q = deque()
    seen = set()

    # 被棋子占据的入口不能作为通往其它目标的虚拟起点。
    for entry in entries:
        if entry in board:
            continue
        q.append((entry, [mountain, entry]))
        seen.add(entry)

    while q:
        cur, path = q.popleft()

        for nxt in _sorted_nodes(topology.rail_neighbors(cur)):
            if nxt in seen:
                continue

            # 允许 dst 上的敌棋作为最终攻击目标。
            if nxt != dst and nxt in board:
                continue

            new_path = path + [nxt]

            if nxt == dst:
                return new_path

            seen.add(nxt)
            q.append((nxt, new_path))

    return None


def movement_details(board, owner, src, dst, mountains_enabled=True):
    """
    返回：
        (合法, reason, reveal_engineer, actual_path)

    actual_path 是本次行动真实采用的节点序列。
    多条等长铁路路径时使用固定 BFS 顺序选择一条，确保双方显示一致。
    """
    if src == dst or src not in board:
        return False, "无效移动。", False, None

    piece = board[src]

    if piece["owner"] != owner:
        return False, "不能移动对方棋子。", False, None

    rank = piece["rank"]

    if not movable(rank):
        return False, "该棋子不能移动。", False, None

    if _hq_locked(piece, src):
        return False, "进入大本营后的棋子不能再移动。", False, None

    # --------------------------------------------------------
    # 山界：只与铁路连接
    # --------------------------------------------------------
    if topology.is_mountain(dst):
        if not mountains_enabled:
            return False, "本局未启用山界。", False, None
        if rank != "工兵":
            return False, "只有工兵可以进入山界。", False, None
        if dst in board:
            return False, "山界已被占用。", False, None
        if piece.get("carrying_flag_owner") is not None:
            return False, "背旗棋子不能进入山界。", False, None
        if not topology.is_rail_node(src):
            return False, "进入山界前，工兵必须位于铁路上。", False, None

        path = _engineer_path_to_mountain(board, src, dst)

        if path is None:
            return False, "当前工兵无法沿无阻挡铁路到达该山界入口。", False, None

        # 进入山界本身必然公开工兵身份。
        return True, "", True, path

    if topology.is_mountain(src):
        if not mountains_enabled:
            return False, "本局未启用山界。", False, None
        if rank != "工兵":
            return False, "只有工兵会出现在山界。", False, None
        if not topology.is_rail_node(dst):
            return False, "工兵离开山界后，本步只能沿铁路移动。", False, None
        if dst in board and board[dst]["owner"] == owner:
            return False, "目标位置已有己方棋子。", False, None

        path = _engineer_path_from_mountain(board, src, dst)

        if path is None:
            return False, "无法从山界入口沿无阻挡铁路到达目标。", False, None

        # 山界中的工兵已经公开；这里保持 reveal=True 也不会产生额外泄密。
        return True, "", True, path

    # --------------------------------------------------------
    # 普通站点
    # --------------------------------------------------------
    if not topology.is_station(dst):
        return False, "目标不是有效站点。", False, None

    if dst in board:
        target = board[dst]

        if target["owner"] == owner:
            return False, "目标位置已有己方棋子。", False, None

        if topology.is_camp(dst):
            return False, "行营中的棋子不能被攻击。", False, None

    # 背旗者禁止进入普通行营。
    if piece.get("carrying_flag_owner") is not None and topology.is_camp(dst):
        return False, "背旗棋子不能进入行营。", False, None

    # 公路：一条显式道路边，一步到达。
    if topology.connected_by_road(src, dst):
        return True, "", False, [src, dst]

    # 铁路
    if rank == "工兵":
        path, turned = _engineer_rail_path(board, src, dst)

        if path is not None:
            return True, "", bool(turned), path
    else:
        path = _normal_rail_path(board, src, dst)

        if path is not None:
            return True, "", False, path

    return False, "两个位置之间没有合法道路。", False, None


def movement_info(board, owner, src, dst, mountains_enabled=True):
    """兼容旧调用：仅返回合法性、原因、是否公开工兵。"""
    ok, reason, reveal, _path = movement_details(
        board, owner, src, dst, mountains_enabled
    )
    return ok, reason, reveal


def has_any_move(board, owner, mountains_enabled=True, ground_flags=None, victory_mode="capture"):
    ground_flags = ground_flags or {}
    destinations = list(board.keys())
    for r in range(topology.ROWS):
        for c in range(topology.COLS):
            destinations.append((r, c))
    if mountains_enabled:
        destinations += [topology.MOUNTAIN_LEFT, topology.MOUNTAIN_RIGHT]

    for src, piece in list(board.items()):
        if piece["owner"] != owner or not movable(piece["rank"]):
            continue
        for dst in destinations:
            ok, _, _ = movement_info(board, owner, src, dst, mountains_enabled)
            if not ok:
                continue
            # return 模式下炸弹不能拾取敌旗
            flag_owner = ground_flags.get(dst)
            if victory_mode == "return" and flag_owner is not None and flag_owner != owner and piece["rank"] == "炸弹":
                continue
            return True
    return False
