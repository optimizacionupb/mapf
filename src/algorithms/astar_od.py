"""A* + Operator Decomposition (A* + OD) para MAPF.

Basado en la propuesta de Standley (2010), "Finding Optimal Solutions to Cooperative
Pathfinding Problems", minimizando la Suma de Costos (Sum of Costs / SIC).
"""
from __future__ import annotations

import heapq
import itertools
import math
import random
import time
import uuid
from typing import Any

from domain.interfaces import MAPFSolver
from domain.models import AgentPath, ExecutionResult, GraphTopology, Scenario, TrajectoryPoint

EXITED = -1
GOAL_BEHAVIORS = ("stay", "disappear")
AGENT_ORDERS = ("farthest_first", "id", "random")


def _distances_to_goal(topology: GraphTopology, goal: int) -> dict[int, float]:
    """BFS shortest distance to goal over the reversed adjacency (admissible heuristic)."""
    reverse: dict[int, list[tuple[int, float]]] = {node_id: [] for node_id in topology.nodes}
    for src, edges in topology.adjacency.items():
        for dst, weight in edges:
            reverse.setdefault(dst, []).append((src, weight))

    dist: dict[int, float] = {goal: 0.0}
    heap = [(0.0, goal)]
    while heap:
        d, node = heapq.heappop(heap)
        if d > dist.get(node, math.inf):
            continue
        for neighbor, weight in reverse.get(node, []):
            nd = d + weight
            if nd < dist.get(neighbor, math.inf):
                dist[neighbor] = nd
                heapq.heappush(heap, (nd, neighbor))
    return dist


class AStarODSolver(MAPFSolver):
    """A* + OD solver that minimizes Sum of Costs (SIC)."""

    def __init__(
        self,
        time_limit: float | None = 60.0,
        max_expansions: int | None = None,
        agent_order: str = "farthest_first",
        goal_behavior: str = "stay",
    ) -> None:
        if agent_order not in AGENT_ORDERS:
            raise ValueError(f"agent_order debe ser uno de {AGENT_ORDERS}")
        if goal_behavior not in GOAL_BEHAVIORS:
            raise ValueError(f"goal_behavior debe ser uno de {GOAL_BEHAVIORS}")

        self.time_limit = time_limit
        self.max_expansions = max_expansions
        self.agent_order = agent_order
        self.goal_behavior = goal_behavior

    @property
    def name(self) -> str:
        return "astar_od"

    def _no_solution(
        self, scenario: Scenario, seed: int | None, t0: float, status: str = "no_solution"
    ) -> ExecutionResult:
        return ExecutionResult(
            id=f"{scenario.id}_{self.name}_{uuid.uuid4().hex[:8]}",
            scenario_id=scenario.id,
            algorithm=self.name,
            status=status,
            paths=[],
            seed=seed,
            runtime_ms=(time.perf_counter() - t0) * 1000,
            makespan=0,
            sum_of_costs=0.0,
        )

    def solve(self, scenario: Scenario, seed: int | None = None) -> ExecutionResult:
        t0 = time.perf_counter()

        topology = scenario.topology
        agents = scenario.agents
        starts = [a.start for a in agents]
        goals = [a.goal for a in agents]

        # Validar pertenencia al grafo y colisiones iniciales
        if any(s not in topology.nodes or g not in topology.nodes for s, g in zip(starts, goals)):
            return self._no_solution(scenario, seed, t0)
        if len(set(starts)) != len(starts):
            return self._no_solution(scenario, seed, t0)
        if self.goal_behavior == "stay" and len(set(goals)) != len(goals):
            return self._no_solution(scenario, seed, t0)

        dist = [_distances_to_goal(topology, g) for g in goals]
        order = self._order(starts, dist, seed)

        neighbors: dict[int, tuple[int, ...]] = {}
        for node in topology.nodes:
            neighbors[node] = tuple(neighbor for neighbor, _ in topology.adjacency.get(node, []))

        search = _ODSearch(
            neighbors=neighbors,
            starts=[starts[i] for i in order],
            goals=[goals[i] for i in order],
            dist=[dist[i] for i in order],
            disappear=self.goal_behavior == "disappear",
            deadline=None if self.time_limit is None else t0 + self.time_limit,
            max_expansions=self.max_expansions,
        )
        status, joint_path = search.run()
        runtime = time.perf_counter() - t0

        if joint_path is None:
            return self._no_solution(scenario, seed, t0, status=status)

        paths: list[AgentPath] = []
        makespan = 0
        sum_of_costs = 0.0

        internal = {agent: pos for pos, agent in enumerate(order)}
        for i, agent in enumerate(agents):
            cells = [state[internal[i]] for state in joint_path]
            traj = _trajectory(cells, goals[i])

            agent_path = AgentPath(
                agent=agent.id,
                trajectory=[TrajectoryPoint(node=p["node"], time=p["time"]) for p in traj],
            )
            paths.append(agent_path)

            if agent_path.trajectory:
                makespan = max(makespan, agent_path.trajectory[-1].time)
                sum_of_costs += agent_path.trajectory[-1].time

        return ExecutionResult(
            id=f"{scenario.id}_{self.name}_{uuid.uuid4().hex[:8]}",
            scenario_id=scenario.id,
            algorithm=self.name,
            status=status,
            paths=paths,
            seed=seed,
            runtime_ms=runtime * 1000,
            makespan=makespan,
            sum_of_costs=sum_of_costs,
        )

    def _order(self, starts: list[int], dist: list[dict[int, float]], seed: int | None) -> list[int]:
        idx = list(range(len(starts)))
        if self.agent_order == "farthest_first":
            idx.sort(key=lambda i: -dist[i].get(starts[i], math.inf))
        elif self.agent_order == "random":
            random.Random(seed).shuffle(idx)
        return idx


class _FullState:
    __slots__ = ("positions", "t", "cost", "parent")

    def __init__(self, positions: tuple[int, ...], t: int, cost: float, parent: _FullState | None) -> None:
        self.positions = positions
        self.t = t
        self.cost = cost
        self.parent = parent


class _ODSearch:
    def __init__(
        self,
        neighbors: dict[int, tuple[int, ...]],
        starts: list[int],
        goals: list[int],
        dist: list[dict[int, float]],
        disappear: bool,
        deadline: float | None,
        max_expansions: int | None,
    ) -> None:
        self.neighbors = neighbors
        self.starts = tuple(starts)
        self.goals = tuple(goals)
        self.dist = dist
        self.k = len(starts)
        self.disappear = disappear
        self.deadline = deadline
        self.max_expansions = max_expansions
        self.expanded = 0
        self.expanded_full = 0
        self.generated = 0

    def run(self) -> tuple[str, list[tuple[int, ...]] | None]:
        if self.k == 0:
            return "success", [()]
        root = _FullState(self.starts, 0, 0.0, None)
        f, tie_val = self._evaluate(0.0, 0, self.starts, ())
        if f == math.inf:
            return "no_solution", None

        tie = itertools.count()
        open_list = [(f, tie_val, 0, next(tie), root, ())]
        best_g = {self.starts: 0.0}
        closed: set[tuple[int, ...]] = set()

        while open_list:
            if self._out_of_budget():
                return "timeout", None
            _, _, _, _, state, prefix = heapq.heappop(open_list)
            if not prefix:
                if state.positions in closed or state.cost > best_g[state.positions]:
                    continue
                if self._is_goal(state.positions):
                    return "success", self._reconstruct(state)
                closed.add(state.positions)
                self.expanded_full += 1
            self.expanded += 1
            self._expand(state, prefix, open_list, tie, best_g, closed)
        return "no_solution", None

    def _agent_step_cost(self, i: int, u: int, v: int) -> float:
        if u == EXITED:
            return 0.0
        if u == self.goals[i] and v == self.goals[i]:
            return 0.0
        return 1.0

    def _expand(self, state: _FullState, prefix: tuple[int, ...], open_list: list, tie, best_g: dict, closed: set) -> None:
        i = len(prefix)
        old, t, cost = state.positions, state.t, state.cost
        for v in self._actions(i, old[i]):
            if self._conflict(i, v, old, prefix):
                continue
            new = prefix + (v,)
            if len(new) < self.k:
                f, tie_val = self._evaluate(cost, t, old, new)
                if f == math.inf:
                    continue
                heapq.heappush(open_list, (f, tie_val, -(t * self.k + len(new)), next(tie), state, new))
            else:
                new_t = t + 1
                step_cost = sum(self._agent_step_cost(j, old[j], new[j]) for j in range(self.k))
                new_cost = cost + step_cost

                if new in closed or best_g.get(new, math.inf) <= new_cost:
                    continue
                f, tie_val = self._evaluate(new_cost, new_t, new, ())
                if f == math.inf:
                    continue
                best_g[new] = new_cost
                child = _FullState(new, new_t, new_cost, state)
                heapq.heappush(open_list, (f, tie_val, -(new_t * self.k), next(tie), child, ()))
            self.generated += 1

    def _actions(self, i: int, v: int) -> tuple[int, ...]:
        if v == EXITED or (self.disappear and v == self.goals[i]):
            return (EXITED,)
        return (v,) + self.neighbors.get(v, ())

    @staticmethod
    def _conflict(i: int, v: int, old: tuple[int, ...], prefix: tuple[int, ...]) -> bool:
        if v == EXITED:
            return False
        u = old[i]
        for j, vj in enumerate(prefix):
            if vj == v:
                return True
            if u != v and vj == u and old[j] == v:
                return True
        return False

    def _evaluate(self, cost: float, t: int, old: tuple[int, ...], new: tuple[int, ...]) -> tuple[float, float]:
        m = len(new)
        if m == 0:
            hs = [self._h(i, v) for i, v in enumerate(old)]
            return cost + sum(hs), max(hs)
        step_costs = sum(self._agent_step_cost(j, old[j], new[j]) for j in range(m))
        h_new = [self._h(j, new[j]) for j in range(m)]
        h_old = [self._h(j, old[j]) for j in range(m, self.k)]
        hs = h_new + h_old
        return cost + step_costs + sum(hs), max(hs)

    def _h(self, i: int, v: int) -> float:
        return 0.0 if v == EXITED else self.dist[i].get(v, math.inf)

    def _is_goal(self, positions: tuple[int, ...]) -> bool:
        if self.disappear:
            return all(v == EXITED or v == g for v, g in zip(positions, self.goals))
        return positions == self.goals

    def _out_of_budget(self) -> bool:
        if self.max_expansions is not None and self.expanded >= self.max_expansions:
            return True
        return self.deadline is not None and time.perf_counter() > self.deadline

    @staticmethod
    def _reconstruct(state: _FullState) -> list[tuple[int, ...]]:
        path = []
        while state is not None:
            path.append(state.positions)
            state = state.parent
        return path[::-1]


def _check_instance(starts, goals, goal_behavior) -> None:
    if len(set(starts)) != len(starts):
        raise ValueError("dos robots comparten nodo inicial (conflicto de vértice en t = 0)")
    if goal_behavior == "stay" and len(set(goals)) != len(goals):
        raise ValueError("con goal_behavior = 'stay' dos robots no pueden compartir meta")


def _trajectory(cells: list[int], goal: int) -> list[dict[str, int]]:
    cells = [v for v in cells if v != EXITED]
    while len(cells) > 1 and cells[-1] == goal and cells[-2] == goal:
        cells.pop()
    return [{"node": v, "time": t} for t, v in enumerate(cells)]
