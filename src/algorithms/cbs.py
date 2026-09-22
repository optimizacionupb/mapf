from __future__ import annotations

import heapq
import itertools
import math
import time
import uuid
from dataclasses import dataclass, field

from domain.interfaces import MAPFSolver
from domain.models import Agent, AgentPath, ExecutionResult, GraphTopology, Scenario, TrajectoryPoint

WAIT_COST = 1.0

Path = list[tuple[int, int]]


@dataclass(frozen=True)
class VertexConstraint:
    """Forbids an agent from occupying a node at a given time."""

    agent: int
    node: int
    time: int


@dataclass(frozen=True)
class EdgeConstraint:
    """Forbids an agent from traversing u->v arriving at a given time."""

    agent: int
    u: int
    v: int
    time: int


@dataclass
class VertexConflict:
    """Two agents occupy the same node at the same time."""

    agent1: int
    agent2: int
    node: int
    time: int


@dataclass
class EdgeConflict:
    """Two agents swap positions across the same edge at the same time."""

    agent1: int
    agent2: int
    u: int
    v: int
    time: int


def _distances_to_goal(topology: GraphTopology, goal: int) -> dict[int, float]:
    """Dijkstra shortest distance to goal over the reversed adjacency (admissible heuristic)."""
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


def _reconstruct(came_from: dict[tuple[int, int], tuple[int, int] | None], end: tuple[int, int]) -> Path:
    path: Path = []
    current: tuple[int, int] | None = end
    while current is not None:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path


def _low_level_search(
    topology: GraphTopology,
    agent: Agent,
    vertex_forbidden: set[tuple[int, int]],
    edge_forbidden: set[tuple[int, int, int]],
) -> tuple[Path, float] | None:
    """Space-Time A*: finds the cheapest (node, time) path from agent.start to agent.goal."""
    start, goal = agent.start, agent.goal
    if start not in topology.nodes or goal not in topology.nodes:
        return None

    dist_to_goal = _distances_to_goal(topology, goal)
    if dist_to_goal.get(start, math.inf) == math.inf:
        return None

    last_goal_constraint = max((t for (n, t) in vertex_forbidden if n == goal), default=-1)
    horizon = last_goal_constraint + len(topology.nodes) + 2

    counter = itertools.count()
    start_state = (start, 0)
    g_score: dict[tuple[int, int], float] = {start_state: 0.0}
    came_from: dict[tuple[int, int], tuple[int, int] | None] = {start_state: None}
    open_heap = [(dist_to_goal[start], 0.0, next(counter), start_state)]

    while open_heap:
        _, g, _, state = heapq.heappop(open_heap)
        node, t = state
        if g > g_score.get(state, math.inf):
            continue
        if node == goal and t > last_goal_constraint:
            return _reconstruct(came_from, state), g
        if t > horizon:
            continue

        successors = [(neighbor, weight) for neighbor, weight in topology.adjacency.get(node, [])]
        successors.append((node, WAIT_COST))

        for neighbor, weight in successors:
            nt = t + 1
            if (neighbor, nt) in vertex_forbidden:
                continue
            if neighbor != node and (node, neighbor, nt) in edge_forbidden:
                continue
            next_state = (neighbor, nt)
            ng = g + weight
            if ng < g_score.get(next_state, math.inf):
                g_score[next_state] = ng
                came_from[next_state] = state
                f = ng + dist_to_goal.get(neighbor, math.inf)
                heapq.heappush(open_heap, (f, ng, next(counter), next_state))

    return None


def _find_conflict(solution: dict[int, Path]) -> VertexConflict | EdgeConflict | None:
    """Returns the first vertex or edge conflict between any pair of agents, if any."""
    agent_ids = sorted(solution)
    max_time = max(path[-1][1] for path in solution.values())

    def pos_at(path: Path, t: int) -> int:
        return path[min(t, len(path) - 1)][0]

    for t in range(max_time + 1):
        positions = {a: pos_at(solution[a], t) for a in agent_ids}
        for i, a1 in enumerate(agent_ids):
            for a2 in agent_ids[i + 1 :]:
                if positions[a1] == positions[a2]:
                    return VertexConflict(a1, a2, positions[a1], t)
        if t == 0:
            continue
        for i, a1 in enumerate(agent_ids):
            for a2 in agent_ids[i + 1 :]:
                p1, p2 = solution[a1], solution[a2]
                if t < len(p1) and t < len(p2):
                    u1, v1 = p1[t - 1][0], p1[t][0]
                    u2, v2 = p2[t - 1][0], p2[t][0]
                    if u1 == v2 and v1 == u2 and u1 != v1:
                        return EdgeConflict(a1, a2, u1, v1, t)
    return None


@dataclass
class _CTNode:
    constraints: frozenset[VertexConstraint | EdgeConstraint]
    solution: dict[int, tuple[Path, float]]
    cost: float = field(init=False)

    def __post_init__(self) -> None:
        self.cost = sum(cost for _, cost in self.solution.values())


class CBSSolver(MAPFSolver):
    """Conflict-Based Search: a two-level Strategy implementation of MAPFSolver."""

    def __init__(self, max_iterations: int = 1000, timeout_s: float = 30.0) -> None:
        self.max_iterations = max_iterations
        self.timeout_s = timeout_s

    @property
    def name(self) -> str:
        return "cbs"

    def solve(self, scenario: Scenario, seed: int | None = None) -> ExecutionResult:
        """Runs CBS to find a conflict-free set of paths for every agent in the scenario."""
        start_time = time.perf_counter()
        topology = scenario.topology

        root_solution: dict[int, tuple[Path, float]] = {}
        for agent in scenario.agents:
            planned = _low_level_search(topology, agent, set(), set())
            if planned is None:
                return self._no_solution(scenario, seed, start_time)
            root_solution[agent.id] = planned

        root = _CTNode(constraints=frozenset(), solution=root_solution)
        counter = itertools.count()
        heap = [(root.cost, next(counter), root)]

        iterations = 0
        while heap:
            iterations += 1
            if iterations > self.max_iterations:
                break
            if (time.perf_counter() - start_time) > self.timeout_s:
                break

            _, _, node = heapq.heappop(heap)
            conflict = _find_conflict({aid: path for aid, (path, _) in node.solution.items()})
            if conflict is None:
                return self._success(scenario, seed, start_time, node)

            for constraint in self._branch(conflict):
                child_constraints = node.constraints | {constraint}
                agent = next(a for a in scenario.agents if a.id == constraint.agent)
                vertex_forbidden = {
                    (c.node, c.time)
                    for c in child_constraints
                    if isinstance(c, VertexConstraint) and c.agent == agent.id
                }
                edge_forbidden = {
                    (c.u, c.v, c.time)
                    for c in child_constraints
                    if isinstance(c, EdgeConstraint) and c.agent == agent.id
                }
                planned = _low_level_search(topology, agent, vertex_forbidden, edge_forbidden)
                if planned is None:
                    continue
                child_solution = dict(node.solution)
                child_solution[agent.id] = planned
                child = _CTNode(constraints=child_constraints, solution=child_solution)
                heapq.heappush(heap, (child.cost, next(counter), child))

        return self._no_solution(scenario, seed, start_time)

    @staticmethod
    def _branch(conflict: VertexConflict | EdgeConflict) -> tuple[VertexConstraint | EdgeConstraint, ...]:
        if isinstance(conflict, VertexConflict):
            return (
                VertexConstraint(conflict.agent1, conflict.node, conflict.time),
                VertexConstraint(conflict.agent2, conflict.node, conflict.time),
            )
        return (
            EdgeConstraint(conflict.agent1, conflict.u, conflict.v, conflict.time),
            EdgeConstraint(conflict.agent2, conflict.v, conflict.u, conflict.time),
        )

    def _success(
        self, scenario: Scenario, seed: int | None, start_time: float, node: _CTNode
    ) -> ExecutionResult:
        paths = [
            AgentPath(
                agent=agent_id,
                trajectory=[TrajectoryPoint(node=n, time=t) for n, t in path],
            )
            for agent_id, (path, _) in node.solution.items()
        ]
        makespan = max((path[-1][1] for path, _ in node.solution.values()), default=0)
        return ExecutionResult(
            id=f"{scenario.id}_cbs_{uuid.uuid4().hex[:8]}",
            scenario_id=scenario.id,
            algorithm=self.name,
            status="success",
            paths=paths,
            seed=seed,
            runtime_ms=(time.perf_counter() - start_time) * 1000,
            makespan=makespan,
            sum_of_costs=node.cost,
        )

    def _no_solution(self, scenario: Scenario, seed: int | None, start_time: float) -> ExecutionResult:
        return ExecutionResult(
            id=f"{scenario.id}_cbs_{uuid.uuid4().hex[:8]}",
            scenario_id=scenario.id,
            algorithm=self.name,
            status="no_solution",
            paths=[],
            seed=seed,
            runtime_ms=(time.perf_counter() - start_time) * 1000,
            makespan=0,
            sum_of_costs=0.0,
        )
