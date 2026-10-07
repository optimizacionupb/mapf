"""Solver jerárquico L1 -> L2 -> L3 descrito en docs/L123.md.

L1 direcciona enlaces con contraflujo persistente (quita un sentido si se puede).
L2 genera rutas espaciales candidatas por agente, penalizando los arcos ya usados.
L3 muestrea una ruta por agente y las temporaliza con planificación priorizada
(solo avanzar o esperar), por componentes del grafo de interacción.

Hacia afuera solo se devuelve el ExecutionResult del contrato MAPFSolver. G_theta,
pools de rutas, probabilidades y congestión son estado interno.
"""

from __future__ import annotations

import heapq
import math
import random
import time
import uuid
from collections import defaultdict
from collections.abc import Callable

from domain.interfaces import MAPFSolver
from domain.models import Agent, AgentPath, ExecutionResult, Scenario, TrajectoryPoint

WAIT_COST = 1.0

Route = tuple[int, ...]
Traj = list[tuple[int, int]]
Adjacency = dict[int, list[tuple[int, float]]]


def _no_extra(u: int, v: int) -> float:
    return 0.0


def _shortest_route(adj: Adjacency, start: int, goal: int, extra: Callable[[int, int], float]) -> Route | None:
    """Dijkstra sobre adj; `extra(u, v)` suma un coste de penalización al arco u->v."""
    dist: dict[int, float] = {start: 0.0}
    prev: dict[int, int | None] = {start: None}
    heap = [(0.0, start)]
    while heap:
        d, u = heapq.heappop(heap)
        if u == goal:
            break
        if d > dist[u]:
            continue
        for v, w in adj.get(u, []):
            nd = d + w + extra(u, v)
            if nd < dist.get(v, math.inf):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd, v))
    if goal not in prev:
        return None
    route = [goal]
    while prev[route[-1]] is not None:
        route.append(prev[route[-1]])
    return tuple(reversed(route))


def _reachable(adj: Adjacency, start: int, goal: int) -> bool:
    return _shortest_route(adj, start, goal, _no_extra) is not None


def _theta_adjacency(original: Adjacency, removed: set[tuple[int, int]]) -> Adjacency:
    """G_theta: el grafo original sin los arcos direccionalizados por L1."""
    return {u: [(v, w) for v, w in edges if (u, v) not in removed] for u, edges in original.items()}


def _route_cost(route: Route, edge_w: dict[tuple[int, int], float]) -> float:
    return sum(edge_w[(u, v)] for u, v in zip(route, route[1:]))


def _softmax(costs: list[float], beta: float) -> list[float]:
    """Probabilidades de elegir cada ruta: favorece costes bajos, `beta` controla la exploración."""
    m = min(costs)
    weights = [math.exp(-beta * (c - m)) for c in costs]
    total = sum(weights)
    return [w / total for w in weights]


# ---------------------------------------------------------------- L2


def _route_pool(
    adj: Adjacency,
    start: int,
    goal: int,
    congestion: dict[int, float],
    gamma: float,
    penalty: float,
    k: int,
) -> list[Route]:
    """Hasta k rutas espaciales: cada una penaliza los arcos de las anteriores y la congestión λ̄."""
    pool: list[Route] = []
    used: dict[tuple[int, int], float] = {}

    def extra(u: int, v: int) -> float:
        return gamma * congestion.get(v, 0.0) + used.get((u, v), 0.0)

    for _ in range(k):
        route = _shortest_route(adj, start, goal, extra)
        if route is None:
            break
        if route not in pool:
            pool.append(route)
        for arc in zip(route, route[1:]):
            used[arc] = used.get(arc, 0.0) + penalty
    return pool


def _flow_signals(
    pools: dict[int, list[Route]], probs: dict[int, list[float]]
) -> dict[tuple[int, int], float]:
    """f_ab: flujo esperado por arco, ponderando cada ruta por su probabilidad."""
    flows: dict[tuple[int, int], float] = defaultdict(float)
    for aid, pool in pools.items():
        for route, p in zip(pool, probs[aid]):
            for arc in zip(route, route[1:]):
                flows[arc] += p
    return flows


def _regulate(
    original: Adjacency,
    removed: set[tuple[int, int]],
    flows: dict[tuple[int, int], float],
    streak: dict[tuple[int, int], int],
    agents: list[Agent],
    threshold: float,
    persistence: int,
) -> bool:
    """L1: si mu_ab = f_ab * f_ba supera el umbral `persistence` ciclos seguidos, quita el sentido menos usado.

    Solo quita el arco si todos los agentes siguen teniendo camino. Devuelve True si cambió algo.
    """
    arcs = {(u, v) for u, edges in original.items() for v, _ in edges}
    changed = False
    for u, v in sorted(arcs):
        if u > v or (v, u) not in arcs:
            continue
        if (u, v) in removed or (v, u) in removed:
            continue
        mu = flows.get((u, v), 0.0) * flows.get((v, u), 0.0)
        streak[(u, v)] = streak.get((u, v), 0) + 1 if mu > threshold else 0
        if streak[(u, v)] < persistence:
            continue
        drop = (u, v) if flows.get((u, v), 0.0) < flows.get((v, u), 0.0) else (v, u)
        theta = _theta_adjacency(original, removed | {drop})
        if all(_reachable(theta, a.start, a.goal) for a in agents):
            removed.add(drop)
            changed = True
        streak[(u, v)] = 0
    return changed


# ---------------------------------------------------------------- L3


def _schedule_fixed(routes: dict[int, Route], members: list[int], horizon: int) -> dict[int, Traj] | None:
    """Temporaliza rutas fijas por prioridad (orden de `members`). Cada paso: avanzar o esperar.

    Un agente que llega a su goal se queda allí para siempre (queda "aparcado").
    Devuelve None si algún agente no puede avanzar ni esperar dentro del horizonte.
    """
    occupied: set[tuple[int, int]] = set()
    edges_used: set[tuple[int, int, int]] = set()  # (u, v, t): alguien entra de u a v en t
    parked: dict[int, int] = {}  # nodo -> instante desde el que queda ocupado para siempre
    last_time: dict[int, int] = {}  # último instante reservado en cada nodo
    trajs: dict[int, Traj] = {}

    def free(node: int, t: int) -> bool:
        return (node, t) not in occupied and not (node in parked and t >= parked[node])

    def occupy(node: int, t: int) -> None:
        occupied.add((node, t))
        last_time[node] = max(last_time.get(node, -1), t)

    for agent in members:
        route = routes[agent]
        if len(route) == 1:
            node = route[0]
            if node in parked or last_time.get(node, -1) >= 0:
                return None
            parked[node] = 0
            trajs[agent] = [(node, 0)]
            continue

        cur, t, idx = route[0], 0, 0
        traj: Traj = [(cur, 0)]
        while idx < len(route) - 1:
            t1 = t + 1
            if t1 > horizon:
                return None
            nxt = route[idx + 1]
            final = idx + 1 == len(route) - 1
            can_move = free(nxt, t1) and (nxt, cur, t1) not in edges_used
            if final:
                can_move = can_move and nxt not in parked and last_time.get(nxt, -1) < t1
            if can_move:
                edges_used.add((cur, nxt, t1))
                if final:
                    parked[nxt] = t1
                else:
                    occupy(nxt, t1)
                cur, idx = nxt, idx + 1
            elif free(cur, t1):
                occupy(cur, t1)
            else:
                return None
            t = t1
            traj.append((cur, t))
        trajs[agent] = traj
    return trajs


def _schedule_components(routes: dict[int, Route], order: list[int]) -> dict[int, Traj] | None:
    """Agrupa agentes por componentes del grafo de interacción (rutas que comparten nodos) y temporaliza cada una."""
    parent = {a: a for a in order}

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    owner: dict[int, int] = {}
    for a in order:
        for node in routes[a]:
            if node in owner:
                parent[find(a)] = find(owner[node])
            else:
                owner[node] = a

    components: dict[int, list[int]] = defaultdict(list)
    for a in order:
        components[find(a)].append(a)

    horizon = 2 * sum(len(r) for r in routes.values()) + 10
    trajs: dict[int, Traj] = {}
    for members in components.values():
        part = _schedule_fixed(routes, members, horizon)
        if part is None:
            return None
        trajs.update(part)
    return trajs


def _has_conflict(trajs: dict[int, Traj]) -> bool:
    """Comprueba vértices y aristas en conflicto. Un agente parado en su posición final sigue ocupándola."""
    ids = sorted(trajs)
    horizon = max((tr[-1][1] for tr in trajs.values()), default=0)

    def at(tr: Traj, t: int) -> int:
        return tr[min(t, len(tr) - 1)][0]

    for t in range(horizon + 1):
        pos = {a: at(trajs[a], t) for a in ids}
        if len(set(pos.values())) < len(ids):
            return True
        if t == 0:
            continue
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                if pos[a] == at(trajs[b], t - 1) and pos[b] == at(trajs[a], t - 1) and pos[a] != pos[b]:
                    return True
    return False


# ---------------------------------------------------------------- solver


class HierarchicalSolver(MAPFSolver):
    """Solver jerárquico L1 (direcciones) -> L2 (rutas) -> L3 (temporalización por muestreo)."""

    def __init__(
        self,
        max_cycles: int = 5,
        samples: int = 200,
        beta: float = 1.0,
        gamma: float = 1.0,
        route_penalty: float = 1.0,
        routes_per_agent: int = 3,
        mu_threshold: float = 1.0,
        persistence: int = 2,
        timeout_s: float = 30.0,
    ) -> None:
        self.max_cycles = max_cycles
        self.samples = samples
        self.beta = beta
        self.gamma = gamma
        self.route_penalty = route_penalty
        self.routes_per_agent = routes_per_agent
        self.mu_threshold = mu_threshold
        self.persistence = persistence
        self.timeout_s = timeout_s

    @property
    def name(self) -> str:
        return "hierarchical"

    def solve(self, scenario: Scenario, seed: int | None = None) -> ExecutionResult:
        """Busca una solución sin conflictos. `no_solution`: no se encontró en el presupuesto; `timeout`: se agotó el tiempo."""
        start_time = time.perf_counter()
        topology = scenario.topology
        agents = scenario.agents
        original = topology.adjacency
        starts = [a.start for a in agents]
        goals = [a.goal for a in agents]

        if any(n not in topology.nodes for n in starts + goals):
            return self._result(scenario, seed, start_time, "no_solution", None)
        if len(set(starts)) < len(starts) or len(set(goals)) < len(goals):
            return self._result(scenario, seed, start_time, "no_solution", None)
        if any(not _reachable(original, a.start, a.goal) for a in agents):
            return self._result(scenario, seed, start_time, "no_solution", None)

        edge_w = {(u, v): w for u, edges in original.items() for v, w in edges}
        rng = random.Random(seed)
        order = [a.id for a in agents]
        removed: set[tuple[int, int]] = set()
        streak: dict[tuple[int, int], int] = {}
        congestion: dict[int, float] = {}
        best: tuple[int, dict[int, Traj]] | None = None

        for _ in range(self.max_cycles):
            if self._out_of_time(start_time):
                break
            cycle_best = best[0] if best is not None else None

            theta = _theta_adjacency(original, removed)
            pools = {
                a.id: _route_pool(theta, a.start, a.goal, congestion, self.gamma, self.route_penalty, self.routes_per_agent)
                for a in agents
            }
            probs = {aid: _softmax([_route_cost(r, edge_w) for r in pool], self.beta) for aid, pool in pools.items()}
            flows = _flow_signals(pools, probs)

            waits: dict[int, int] = defaultdict(int)
            feasible = 0
            for _ in range(self.samples):
                if self._out_of_time(start_time):
                    break
                routes = {
                    aid: pool[rng.choices(range(len(pool)), weights=probs[aid])[0]] for aid, pool in pools.items()
                }
                trajs = _schedule_components(routes, order)
                if trajs is None:
                    continue
                feasible += 1
                for tr in trajs.values():
                    for (n, _), (m, _) in zip(tr, tr[1:]):
                        if n == m:
                            waits[n] += 1
                k = max(tr[-1][1] for tr in trajs.values())
                if best is None or k < best[0]:
                    best = (k, trajs)

            congestion = {v: c / feasible for v, c in waits.items()} if feasible else {}
            changed = _regulate(
                original, removed, flows, streak, agents, self.mu_threshold, self.persistence
            )
            if not changed and best is not None and best[0] == cycle_best:
                break

        if best is None or _has_conflict(best[1]):
            status = "timeout" if self._out_of_time(start_time) else "no_solution"
            return self._result(scenario, seed, start_time, status, None)
        return self._result(scenario, seed, start_time, "success", best[1])

    def _out_of_time(self, start_time: float) -> bool:
        return (time.perf_counter() - start_time) > self.timeout_s

    def _result(
        self,
        scenario: Scenario,
        seed: int | None,
        start_time: float,
        status: str,
        trajs: dict[int, Traj] | None,
    ) -> ExecutionResult:
        paths: list[AgentPath] = []
        sum_of_costs = 0.0
        makespan = 0
        if trajs is not None:
            edge_w = {(u, v): w for u, edges in scenario.topology.adjacency.items() for v, w in edges}
            for agent in scenario.agents:
                tr = trajs[agent.id]
                paths.append(
                    AgentPath(
                        agent=agent.id,
                        trajectory=[TrajectoryPoint(node=n, time=t) for n, t in tr],
                    )
                )
                sum_of_costs += sum(WAIT_COST if u == v else edge_w[(u, v)] for (u, _), (v, _) in zip(tr, tr[1:]))
                makespan = max(makespan, tr[-1][1])

        return ExecutionResult(
            id=f"{scenario.id}_{self.name}_{uuid.uuid4().hex[:8]}",
            scenario_id=scenario.id,
            algorithm=self.name,
            status=status,
            paths=paths,
            seed=seed,
            runtime_ms=(time.perf_counter() - start_time) * 1000,
            makespan=makespan,
            sum_of_costs=sum_of_costs,
        )
