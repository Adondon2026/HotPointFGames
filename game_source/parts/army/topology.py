"""
标准二人军棋棋盘拓扑。

普通站点用 (row, col)，row=0..11，col=0..4。
中央两个山界使用字符串 "ML" / "MR"。

道路边分为：
- ROAD: 普通公路，只能一步跨一条边；
- RAIL: 铁路，可按军棋铁路规则长距离移动。

这里不再用“只看行列是否相邻”判断合法性，而是先构造显式图。
"""

ROWS = 12
COLS = 5

MOUNTAIN_LEFT = "ML"
MOUNTAIN_RIGHT = "MR"

CAMPS = {
    (2, 1), (2, 3), (3, 2), (4, 1), (4, 3),
    (9, 1), (9, 3), (8, 2), (7, 1), (7, 3),
}

HQ_P0 = {(0, 1), (0, 3)}
HQ_P1 = {(11, 1), (11, 3)}
HQ = HQ_P0 | HQ_P1

# 四条横向铁路 + 两侧纵向铁路 + 中央跨前线铁路
RAIL_NODES = set()
for r in (1, 5, 6, 10):
    for c in range(COLS):
        RAIL_NODES.add((r, c))
for r in range(1, 11):
    RAIL_NODES.add((r, 0))
    RAIL_NODES.add((r, 4))
# 中央一列只在双方前线之间由铁路连接
RAIL_NODES.add((5, 2))
RAIL_NODES.add((6, 2))

ROAD_EDGES = set()
RAIL_EDGES = set()


def _edge(a, b):
    return frozenset((a, b))


def _add_road(a, b):
    ROAD_EDGES.add(_edge(a, b))


def _add_rail(a, b):
    RAIL_EDGES.add(_edge(a, b))


# 每个阵营内部的标准站点网络：
# 相邻横/纵站点均有道路；铁路所在边同时归入铁路。
# 这用显式边集合固定下来，运行时不再按坐标猜测。
for r0, r1 in ((0, 5), (6, 11)):
    for r in range(r0, r1 + 1):
        for c in range(COLS - 1):
            a, b = (r, c), (r, c + 1)
            if r in (1, 5, 6, 10):
                _add_rail(a, b)
            else:
                _add_road(a, b)

    for r in range(r0, r1):
        for c in range(COLS):
            a, b = (r, c), (r + 1, c)
            if c in (0, 4) and 1 <= r <= 9:
                _add_rail(a, b)
            else:
                _add_road(a, b)

# 行营斜线：标准棋盘每个行营连接四个对角站点。
for camp in list(CAMPS):
    r, c = camp
    for dr in (-1, 1):
        for dc in (-1, 1):
            q = (r + dr, c + dc)
            if 0 <= q[0] < ROWS and 0 <= q[1] < COLS:
                # 不跨中央空白
                if (camp[0] <= 5 and q[0] <= 5) or (camp[0] >= 6 and q[0] >= 6):
                    _add_road(camp, q)

# 中央前线只保留 0/2/4 三条铁路跨接。
for c in (0, 2, 4):
    _add_rail((5, c), (6, c))

ROAD_ADJ = {}
RAIL_ADJ = {}
for r in range(ROWS):
    for c in range(COLS):
        ROAD_ADJ[(r, c)] = set()
        RAIL_ADJ[(r, c)] = set()

for e in ROAD_EDGES:
    a, b = tuple(e)
    ROAD_ADJ[a].add(b)
    ROAD_ADJ[b].add(a)

for e in RAIL_EDGES:
    a, b = tuple(e)
    RAIL_ADJ[a].add(b)
    RAIL_ADJ[b].add(a)

# 山界的“外围一圈铁路站点”。
MOUNTAIN_NEIGHBORS = {
    MOUNTAIN_LEFT: {
        (5, 0), (5, 1), (5, 2),
        (6, 0), (6, 1), (6, 2),
    },
    MOUNTAIN_RIGHT: {
        (5, 2), (5, 3), (5, 4),
        (6, 2), (6, 3), (6, 4),
    },
}


def is_station(node):
    return (
        isinstance(node, tuple)
        and len(node) == 2
        and 0 <= node[0] < ROWS
        and 0 <= node[1] < COLS
    )


def is_mountain(node):
    return node in (MOUNTAIN_LEFT, MOUNTAIN_RIGHT)


def is_camp(node):
    return node in CAMPS


def is_hq(node):
    return node in HQ


def hq_for(owner):
    return HQ_P0 if owner == 0 else HQ_P1


def is_rail_node(node):
    return node in RAIL_NODES


def road_neighbors(node):
    return ROAD_ADJ.get(node, set())


def rail_neighbors(node):
    return RAIL_ADJ.get(node, set())


def mountain_neighbors(node):
    return MOUNTAIN_NEIGHBORS.get(node, set())


def connected_by_road(a, b):
    return _edge(a, b) in ROAD_EDGES


def connected_by_rail(a, b):
    return _edge(a, b) in RAIL_EDGES


def rotate_node_180(node):
    """
    棋盘节点做 180° 视角变换。

    普通站点：(r, c) -> (11-r, 4-c)
    山界：ML <-> MR

    这是一个自反变换：调用两次会回到原节点。
    山界必须参与这个变换，否则玩家0旋转棋盘时会出现
    “画面左山界对应逻辑右山界”的主客机显示错位。
    """
    if node == MOUNTAIN_LEFT:
        return MOUNTAIN_RIGHT
    if node == MOUNTAIN_RIGHT:
        return MOUNTAIN_LEFT
    if is_station(node):
        r, c = node
        return (ROWS - 1 - r, COLS - 1 - c)
    return node

