"""Shared helpers: instance definitions, solver output parsers, and an independent solution validator.

Validator semantics follow classical MAPF (vertex + swap conflicts, 4-connected moves, wait allowed).
Sum of costs (SoC) = sum over agents of the last time step at which the agent is not yet resting at its goal
(standard definition; identical to lacam3's get_sum_of_costs in lacam3/src/metrics.cpp).
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # experiments/congestion_field
REPO = os.path.dirname(os.path.dirname(ROOT))
BENCH = os.path.join(REPO, "data", "benchmarks")

MAPS = {
    "warehouse": ("warehouse/warehouse-10-20-10-2-1.map",
                  "warehouse/warehouse-10-20-10-2-1.map-scen-even/scen-even/warehouse-10-20-10-2-1-even-{k}.scen"),
    "maze": ("maze/maze-128-128-10.map",
             "maze/maze-128-128-10.map-scen-random/scen-random/maze-128-128-10-random-{k}.scen"),
    "berlin": ("berlin/Berlin_1_256.map",
               "berlin/Berlin_1_256.map-scen-random/scen-random/Berlin_1_256-random-{k}.scen"),
}
TUNE_SCENS = [1, 2, 3, 4, 5]
TEST_SCENS = list(range(6, 26))


def map_path(m):
    return os.path.join(BENCH, MAPS[m][0])


def scen_path(m, k):
    return os.path.join(BENCH, MAPS[m][1].format(k=k))


def read_map(path):
    with open(path) as f:
        lines = f.read().splitlines()
    h = int(lines[1].split()[1])
    w = int(lines[2].split()[1])
    grid = [row[:w] for row in lines[4:4 + h]]
    free = [[grid[y][x] in ".GS" for x in range(w)] for y in range(h)]
    return w, h, free


def read_scen(path, n):
    """Returns list of (sx, sy, gx, gy), x = column, y = row, first n rows."""
    out = []
    with open(path) as f:
        f.readline()
        for line in f:
            p = line.split()
            if len(p) < 8:
                continue
            out.append((int(p[4]), int(p[5]), int(p[6]), int(p[7])))
            if len(out) == n:
                break
    if len(out) < n:
        raise ValueError(f"{path} has only {len(out)} agents, need {n}")
    return out


_pair = re.compile(r"\((\d+),(\d+)\)")


def parse_config_solution(path):
    """lacam3 / pibt2 format: lines 't:(x,y),(x,y),...' after 'solution='. Returns list of configs [(x,y),...]."""
    sol = []
    started = False
    with open(path) as f:
        for line in f:
            if line.startswith("solution="):
                started = True
                continue
            if started and re.match(r"^\d+:", line):
                sol.append([(int(a), int(b)) for a, b in _pair.findall(line.split(":", 1)[1])])
    return sol


def parse_kv(path):
    kv = {}
    with open(path) as f:
        for line in f:
            if "=" in line and not re.match(r"^\d+:", line):
                k, v = line.rstrip("\n").split("=", 1)
                if k in ("starts", "goals", "solution"):
                    continue
                kv[k] = v
    return kv


def parse_eecbs_paths(path, n):
    """EECBS --outputPaths format: 'Agent i: (row,col)->(row,col)->...'. Returns per-agent paths as (x,y)."""
    paths = [None] * n
    with open(path) as f:
        for line in f:
            m = re.match(r"Agent (\d+):(.*)", line)
            if not m:
                continue
            i = int(m.group(1))
            paths[i] = [(int(c), int(r)) for r, c in _pair.findall(m.group(2))]
    return paths


def paths_to_configs(paths):
    T = max(len(p) for p in paths)
    return [[p[min(t, len(p) - 1)] for p in paths] for t in range(T)]


def validate(map_file, agents, configs):
    """Independent validator. Returns (ok, message, soc, makespan)."""
    w, h, free = read_map(map_file)
    n = len(agents)
    if not configs:
        return False, "empty", None, None
    if any(len(c) != n for c in configs):
        return False, "wrong number of agents in a config", None, None
    for i, (sx, sy, gx, gy) in enumerate(agents):
        if configs[0][i] != (sx, sy):
            return False, f"agent {i} wrong start", None, None
        if configs[-1][i] != (gx, gy):
            return False, f"agent {i} does not end at goal", None, None
    for t, c in enumerate(configs):
        for (x, y) in c:
            if not (0 <= x < w and 0 <= y < h and free[y][x]):
                return False, f"t={t} obstacle/out of map {(x, y)}", None, None
        if len(set(c)) != n:
            return False, f"vertex conflict at t={t}", None, None
        if t == 0:
            continue
        p = configs[t - 1]
        pos_prev = {v: i for i, v in enumerate(p)}
        for i in range(n):
            (x0, y0), (x1, y1) = p[i], c[i]
            if abs(x0 - x1) + abs(y0 - y1) > 1:
                return False, f"agent {i} jumps at t={t}", None, None
            if (x0, y0) != (x1, y1):
                j = pos_prev.get((x1, y1))
                if j is not None and j != i and c[j] == (x0, y0):
                    return False, f"swap conflict {i},{j} at t={t}", None, None
    soc = 0
    for i in range(n):
        g = configs[-1][i]
        c = len(configs)
        while c > 0 and configs[c - 1][i] == g:
            c -= 1
        soc += c
    return True, "ok", soc, len(configs) - 1


def soc_lower_bound(map_file, agents):
    """Sum of BFS distances (classic SoC lower bound)."""
    from collections import deque
    w, h, free = read_map(map_file)
    cache = {}
    total = 0
    for (sx, sy, gx, gy) in agents:
        if (gx, gy) not in cache:
            d = [[-1] * w for _ in range(h)]
            d[gy][gx] = 0
            q = deque([(gx, gy)])
            while q:
                x, y = q.popleft()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and free[ny][nx] and d[ny][nx] < 0:
                        d[ny][nx] = d[y][x] + 1
                        q.append((nx, ny))
            cache[(gx, gy)] = d
        total += cache[(gx, gy)][sy][sx]
    return total
