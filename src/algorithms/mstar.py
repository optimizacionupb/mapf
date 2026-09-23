from __future__ import annotations

import heapq
import itertools
import math
import time
import uuid
from collections import defaultdict
from collections.abc import Iterator

from domain.interfaces import MAPFSolver
from domain.models import AgentPath, ExecutionResult, GraphTopology, Scenario, TrajectoryPoint

WAIT_COST = 1.0

Positions = tuple[int, ...]
Parked = tuple[bool, ...]
State = tuple[Positions, Parked]


def _individual_policy(
    topology: GraphTopology, goal: int
) -> tuple[dict[int, float], dict[int, tuple[int, float]]]:
    """Backward Dijkstra from goal: cost-to-goal and optimal next step for every node."""
    reverse: dict[int, list[tuple[int, float]]] = {node_id: [] for node_id in topology.nodes}
    for src, edges in topology.adjacency.items():
        for dst, weight in edges:
            reverse.setdefault(dst, []).append((src, weight))

    dist: dict[int, float] = {goal: 0.0}
    next_step: dict[int, tuple[int, float]] = {goal: (goal, 0.0)}
    heap: list[tuple[float, int]] = [(0.0, goal)]

    while heap:
        d, node = heapq.heappop(heap)
        if d > dist.get(node, math.inf):
            continue
        for prev, weight in reverse.get(node, []):
            nd = d + weight
            if nd < dist.get(prev, math.inf):
                dist[prev] = nd
                next_step[prev] = (node, weight)
                heapq.heappush(heap, (nd, prev))

    return dist, next_step


def _collisions(before: Positions, after: Positions) -> frozenset[int]:
    """Indices of agents in a vertex or swap conflict when moving from `before` to `after`."""
    hit: set[int] = set()
    for i in range(len(after)):
        for j in range(i + 1, len(after)):
            vertex = after[i] == after[j]
            swap = after[i] == before[j] and after[j] == before[i]
            if vertex or swap:
                hit.update((i, j))
    return frozenset(hit)


class MStarSolver(MAPFSolver):
    """M*: A* over the joint space that expands only agents in a collision set."""

    def __init__(
        self, epsilon: float = 0.0, max_expansions: int = 200_000, timeout_s: float = 30.0
    ) -> None:
        self.epsilon = epsilon
        self.max_expansions = max_expansions
        self.timeout_s = timeout_s

    @property
    def name(self) -> str:
        return "mstar"

    def solve(self, scenario: Scenario, seed: int | None = None) -> ExecutionResult:
        """Runs M* to find conflict-free paths minimizing sum of costs."""
        start_time = time.perf_counter()
        topology = scenario.topology
        starts: Positions = tuple(agent.start for agent in scenario.agents)
        goals: Positions = tuple(agent.goal for agent in scenario.agents)

        if any(node not in topology.nodes for node in starts + goals):
            return self._no_solution(scenario, seed, start_time)
        if len(set(starts)) < len(starts) or len(set(goals)) < len(goals):
            return self._no_solution(scenario, seed, start_time)

        policies = [_individual_policy(topology, goal) for goal in goals]
        dists = [dist for dist, _ in policies]
        next_steps = [step for _, step in policies]
        if any(start not in dist for start, dist in zip(starts, dists)):
            return self._no_solution(scenario, seed, start_time)

        inflation = 1.0 + self.epsilon

        def h(state: State) -> float:
            return inflation * sum(dists[i][pos] for i, pos in enumerate(state[0]))

        start_state: State = (starts, tuple(False for _ in starts))
        g_score: dict[State, float] = {start_state: 0.0}
        parent: dict[State, State | None] = {start_state: None}
        collision_set: dict[State, frozenset[int]] = defaultdict(frozenset)
        back_set: dict[State, set[State]] = defaultdict(set)
        counter = itertools.count()
        open_heap: list[tuple[float, int, State]] = [(h(start_state), next(counter), start_state)]

        def backpropagate(state: State, incoming: frozenset[int]) -> None:
            stack = [(state, incoming)]
            while stack:
                current, new_agents = stack.pop()
                if new_agents <= collision_set[current]:
                    continue
                collision_set[current] = collision_set[current] | new_agents
                heapq.heappush(open_heap, (g_score[current] + h(current), next(counter), current))
                for predecessor in back_set[current]:
                    stack.append((predecessor, collision_set[current]))

        expansions = 0
        while open_heap:
            if expansions >= self.max_expansions:
                break
            if (time.perf_counter() - start_time) > self.timeout_s:
                break

            f, _, state = heapq.heappop(open_heap)
            if f > g_score[state] + h(state) + 1e-9:
                continue
            if state[0] == goals:
                return self._success(scenario, seed, start_time, parent, state)
            expansions += 1

            for successor, cost in self._successors(
                state, collision_set[state], topology, goals, dists, next_steps
            ):
                back_set[successor].add(state)
                conflict = _collisions(state[0], successor[0])
                backpropagate(state, conflict | collision_set[successor])
                if conflict:
                    continue
                new_g = g_score[state] + cost
                if new_g < g_score.get(successor, math.inf):
                    g_score[successor] = new_g
                    parent[successor] = state
                    heapq.heappush(open_heap, (new_g + h(successor), next(counter), successor))

        return self._no_solution(scenario, seed, start_time)

    @staticmethod
    def _successors(
        state: State,
        conflict_agents: frozenset[int],
        topology: GraphTopology,
        goals: Positions,
        dists: list[dict[int, float]],
        next_steps: list[dict[int, tuple[int, float]]],
    ) -> Iterator[tuple[State, float]]:
        """Joint moves: all options for agents in the collision set, policy move for the rest.

        An agent standing on its goal may "park" (stay there for good, at no further cost).
        A non-parked wait costs WAIT_COST even on the goal, so leaving the goal later is
        charged exactly like CBS charges it.
        """
        positions, parked = state
        options: list[list[tuple[int, bool, float]]] = []
        for i, pos in enumerate(positions):
            at_goal = pos == goals[i]
            if parked[i]:
                options.append([(pos, True, 0.0)])
            elif i not in conflict_agents:
                if at_goal:
                    options.append([(pos, True, 0.0)])
                else:
                    nxt, w = next_steps[i][pos]
                    options.append([(nxt, False, w)])
            else:
                agent_options = [(pos, False, WAIT_COST)]
                if at_goal:
                    agent_options.append((pos, True, 0.0))
                agent_options += [
                    (nbr, False, w) for nbr, w in topology.adjacency.get(pos, []) if nbr in dists[i]
                ]
                options.append(agent_options)

        for combo in itertools.product(*options):
            new_positions = tuple(node for node, _, _ in combo)
            new_parked = tuple(flag for _, flag, _ in combo)
            yield (new_positions, new_parked), sum(cost for _, _, cost in combo)

    def _success(
        self,
        scenario: Scenario,
        seed: int | None,
        start_time: float,
        parent: dict[State, State | None],
        goal_state: State,
    ) -> ExecutionResult:
        states: list[State] = []
        current: State | None = goal_state
        while current is not None:
            states.append(current)
            current = parent[current]
        states.reverse()

        edge_cost = {
            (src, dst): w for src, edges in scenario.topology.adjacency.items() for dst, w in edges
        }
        paths: list[AgentPath] = []
        sum_of_costs = 0.0
        makespan = 0
        for i, agent in enumerate(scenario.agents):
            nodes = [positions[i] for positions, _ in states]
            while len(nodes) > 1 and nodes[-1] == nodes[-2]:
                nodes.pop()
            sum_of_costs += sum(
                WAIT_COST if u == v else edge_cost[(u, v)] for u, v in zip(nodes, nodes[1:])
            )
            makespan = max(makespan, len(nodes) - 1)
            paths.append(
                AgentPath(
                    agent=agent.id,
                    trajectory=[TrajectoryPoint(node=n, time=t) for t, n in enumerate(nodes)],
                )
            )

        return ExecutionResult(
            id=f"{scenario.id}_mstar_{uuid.uuid4().hex[:8]}",
            scenario_id=scenario.id,
            algorithm=self.name,
            status="success",
            paths=paths,
            seed=seed,
            runtime_ms=(time.perf_counter() - start_time) * 1000,
            makespan=makespan,
            sum_of_costs=sum_of_costs,
        )

    def _no_solution(self, scenario: Scenario, seed: int | None, start_time: float) -> ExecutionResult:
        return ExecutionResult(
            id=f"{scenario.id}_mstar_{uuid.uuid4().hex[:8]}",
            scenario_id=scenario.id,
            algorithm=self.name,
            status="no_solution",
            paths=[],
            seed=seed,
            runtime_ms=(time.perf_counter() - start_time) * 1000,
            makespan=0,
            sum_of_costs=0.0,
        )