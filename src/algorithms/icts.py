from __future__ import annotations

import heapq
import itertools
import math
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass

from domain.interfaces import MAPFSolver
from domain.models import Agent, AgentPath, ExecutionResult, GraphTopology, Scenario, TrajectoryPoint

WAIT_COST = 1.0


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


@dataclass
class MDD:
    """Multi-value Decision Diagram: contains all paths of exact cost from start to goal."""

    agent_id: int
    cost: int
    transitions: list[dict[int, tuple[int, ...]]]
    nodes_at_level: list[set[int]]


def _build_mdd(
    topology: GraphTopology,
    start: int,
    goal: int,
    cost: int,
    dist_to_goal: dict[int, float],
) -> MDD | None:
    """Constructs and backward-prunes an MDD representing all paths of length cost."""
    if dist_to_goal.get(start, math.inf) > cost:
        return None

    # Forward pass: expand reachable nodes at each level t
    levels: list[set[int]] = [set() for _ in range(cost + 1)]
    forward_transitions: list[dict[int, list[int]]] = [defaultdict(list) for _ in range(cost)]
    levels[0].add(start)

    for t in range(cost):
        rem = cost - (t + 1)
        for u in levels[t]:
            # Wait action
            if dist_to_goal.get(u, math.inf) <= rem:
                levels[t + 1].add(u)
                forward_transitions[t][u].append(u)
            # Move actions
            for v, _ in topology.adjacency.get(u, ()):
                if dist_to_goal.get(v, math.inf) <= rem:
                    levels[t + 1].add(v)
                    forward_transitions[t][u].append(v)

    if goal not in levels[cost]:
        return None

    # Backward pass: prune nodes and edges that cannot reach goal at level cost
    valid_nodes: set[int] = {goal}
    backward_transitions: list[dict[int, tuple[int, ...]]] = [{} for _ in range(cost)]
    final_levels: list[set[int]] = [set() for _ in range(cost + 1)]
    final_levels[cost] = {goal}

    for t in range(cost - 1, -1, -1):
        next_valid: set[int] = set()
        for u in levels[t]:
            succs = tuple(v for v in forward_transitions[t].get(u, ()) if v in valid_nodes)
            if succs:
                backward_transitions[t][u] = succs
                next_valid.add(u)
        final_levels[t] = next_valid
        valid_nodes = next_valid

    if start not in final_levels[0]:
        return None

    return MDD(
        agent_id=start,
        cost=cost,
        transitions=backward_transitions,
        nodes_at_level=final_levels,
    )


class ICTSSolver(MAPFSolver):
    """Increasing Cost Tree Search (ICTS) solver for MAPF minimizing Sum of Costs."""

    def __init__(self, max_iterations: int = 1000, timeout_s: float = 30.0) -> None:
        self.max_iterations = max_iterations
        self.timeout_s = timeout_s

    @property
    def name(self) -> str:
        return "icts"

    def solve(self, scenario: Scenario, seed: int | None = None) -> ExecutionResult:
        """Solves the scenario using ICTS with MDD generation and pairwise pruning."""
        start_time = time.perf_counter()
        agents = scenario.agents

        if not agents:
            return self._empty_success(scenario, seed, start_time)

        # Basic validations
        starts = tuple(agent.start for agent in agents)
        goals = tuple(agent.goal for agent in agents)

        for s, g in zip(starts, goals):
            if s not in scenario.topology.nodes or g not in scenario.topology.nodes:
                return self._no_solution(scenario, seed, start_time)

        if len(set(starts)) < len(starts):
            return self._no_solution(scenario, seed, start_time)

        # Precompute backward distances from goals
        distances: list[dict[int, float]] = []
        c_star: list[int] = []
        for agent in agents:
            d = _distances_to_goal(scenario.topology, agent.goal)
            if d.get(agent.start, math.inf) == math.inf:
                return self._no_solution(scenario, seed, start_time)
            distances.append(d)
            c_star.append(int(round(d[agent.start])))

        root_costs = tuple(c_star)
        mdd_cache: dict[tuple[int, int], MDD | None] = {}

        def get_mdd(agent_idx: int, cost: int) -> MDD | None:
            key = (agent_idx, cost)
            if key not in mdd_cache:
                ag = agents[agent_idx]
                mdd_cache[key] = _build_mdd(
                    scenario.topology, ag.start, ag.goal, cost, distances[agent_idx]
                )
            return mdd_cache[key]

        counter = itertools.count()
        open_heap = [(sum(root_costs), next(counter), root_costs)]
        visited_ict: set[tuple[int, ...]] = {root_costs}
        iterations = 0

        while open_heap:
            if time.perf_counter() - start_time > self.timeout_s:
                return self._no_solution(scenario, seed, start_time)
            if iterations >= self.max_iterations:
                return self._no_solution(scenario, seed, start_time)

            _, _, current_costs = heapq.heappop(open_heap)
            iterations += 1

            # Fetch MDDs for current costs
            mdds: list[MDD | None] = [get_mdd(i, c) for i, c in enumerate(current_costs)]
            if any(m is None for m in mdds):
                # Cannot form MDD for this cost vector
                continue

            # Run low-level search with pairwise pruning
            valid_mdds: list[MDD] = [m for m in mdds if m is not None]
            solution_paths = self._low_level_search(
                agents, valid_mdds, current_costs, starts, goals, start_time
            )

            if solution_paths is not None:
                return self._success(
                    scenario, seed, start_time, solution_paths, current_costs
                )

            # Expand ICT children
            for i in range(len(agents)):
                child = list(current_costs)
                child[i] += 1
                child_tuple = tuple(child)
                if child_tuple not in visited_ict:
                    visited_ict.add(child_tuple)
                    heapq.heappush(open_heap, (sum(child), next(counter), child_tuple))

        return self._no_solution(scenario, seed, start_time)

    def _low_level_search(
        self,
        agents: list[Agent],
        mdds: list[MDD],
        costs: tuple[int, ...],
        starts: tuple[int, ...],
        goals: tuple[int, ...],
        start_time: float,
    ) -> list[list[int]] | None:
        """Finds conflict-free paths within given MDDs, or returns None."""
        num_agents = len(agents)

        if num_agents == 1:
            # Reconstruct single-agent path through MDD
            path = self._single_agent_path(mdds[0], starts[0], goals[0])
            return [path] if path else None

        # Pairwise pruning check
        if num_agents >= 2:
            for i in range(num_agents):
                for j in range(i + 1, num_agents):
                    pair_result = self._check_pair(
                        mdds[i], mdds[j], starts[i], starts[j], goals[i], goals[j]
                    )
                    if pair_result is None:
                        # Infeasible pair
                        return None
                    if num_agents == 2:
                        return [pair_result[0], pair_result[1]]

        # Full joint search for k > 2 agents
        return self._joint_mdd_search(mdds, costs, starts, goals, start_time)

    def _single_agent_path(self, mdd: MDD, start: int, goal: int) -> list[int] | None:
        """Finds any path through the single-agent MDD."""
        path = [start]
        curr = start
        for t in range(mdd.cost):
            succs = mdd.transitions[t].get(curr, ())
            if not succs:
                return None
            curr = succs[0]
            path.append(curr)
        return path if curr == goal else None

    def _check_pair(
        self,
        mdd_i: MDD,
        mdd_j: MDD,
        start_i: int,
        start_j: int,
        goal_i: int,
        goal_j: int,
    ) -> tuple[list[int], list[int]] | None:
        """Checks if a pair of agents has a conflict-free joint path in their MDDs."""
        t_max = max(mdd_i.cost, mdd_j.cost)
        start_state = (0, start_i, start_j)

        parent: dict[tuple[int, int, int], tuple[int, int, int] | None] = {start_state: None}
        queue = deque([start_state])

        while queue:
            t, u_i, u_j = queue.popleft()
            if t == t_max:
                # Reconstruct pair path
                path_i = [u_i]
                path_j = [u_j]
                curr = (t, u_i, u_j)
                while parent[curr] is not None:
                    curr = parent[curr]
                    path_i.append(curr[1])
                    path_j.append(curr[2])
                path_i.reverse()
                path_j.reverse()
                return (path_i[: mdd_i.cost + 1], path_j[: mdd_j.cost + 1])

            succs_i = mdd_i.transitions[t].get(u_i, ()) if t < mdd_i.cost else (goal_i,)
            succs_j = mdd_j.transitions[t].get(u_j, ()) if t < mdd_j.cost else (goal_j,)

            for v_i in succs_i:
                for v_j in succs_j:
                    if v_i == v_j:
                        continue  # Vertex conflict
                    if u_i == v_j and u_j == v_i:
                        continue  # Edge swap conflict

                    nxt = (t + 1, v_i, v_j)
                    if nxt not in parent:
                        parent[nxt] = (t, u_i, u_j)
                        queue.append(nxt)

        return None

    def _joint_mdd_search(
        self,
        mdds: list[MDD],
        costs: tuple[int, ...],
        starts: tuple[int, ...],
        goals: tuple[int, ...],
        start_time: float,
    ) -> list[list[int]] | None:
        """Full joint BFS over k MDDs with incremental conflict detection."""
        num_agents = len(mdds)
        t_max = max(costs)
        start_state = (0, starts)

        parent: dict[tuple[int, tuple[int, ...]], tuple[int, tuple[int, ...]] | None] = {
            start_state: None
        }
        queue = deque([start_state])

        def get_joint_successors(
            t: int, current_pos: tuple[int, ...]
        ) -> list[tuple[int, ...]]:
            successors: list[tuple[int, ...]] = []

            def backtrack(agent_idx: int, chosen: list[int]) -> None:
                if agent_idx == num_agents:
                    successors.append(tuple(chosen))
                    return

                u = current_pos[agent_idx]
                if t < costs[agent_idx]:
                    candidates = mdds[agent_idx].transitions[t].get(u, ())
                else:
                    candidates = (goals[agent_idx],)

                for v in candidates:
                    # Vertex conflict with previously chosen agents
                    if v in chosen:
                        continue

                    # Edge swap conflict with previously chosen agents
                    conflict = False
                    for prev_idx, prev_v in enumerate(chosen):
                        prev_u = current_pos[prev_idx]
                        if u == prev_v and prev_u == v:
                            conflict = True
                            break
                    if conflict:
                        continue

                    chosen.append(v)
                    backtrack(agent_idx + 1, chosen)
                    chosen.pop()

            backtrack(0, [])
            return successors

        while queue:
            if time.perf_counter() - start_time > self.timeout_s:
                return None

            t, current_positions = queue.popleft()
            if t == t_max:
                # Reconstruct joint trajectories
                joint_states: list[tuple[int, ...]] = [current_positions]
                curr = (t, current_positions)
                while parent[curr] is not None:
                    curr = parent[curr]
                    joint_states.append(curr[1])
                joint_states.reverse()

                paths = []
                for i in range(num_agents):
                    agent_nodes = [step[i] for step in joint_states[: costs[i] + 1]]
                    paths.append(agent_nodes)
                return paths

            for next_pos in get_joint_successors(t, current_positions):
                nxt_state = (t + 1, next_pos)
                if nxt_state not in parent:
                    parent[nxt_state] = (t, current_positions)
                    queue.append(nxt_state)

        return None

    def _success(
        self,
        scenario: Scenario,
        seed: int | None,
        start_time: float,
        solution_paths: list[list[int]],
        costs: tuple[int, ...],
    ) -> ExecutionResult:
        paths = [
            AgentPath(
                agent=agent.id,
                trajectory=[TrajectoryPoint(node=n, time=t) for t, n in enumerate(path)],
            )
            for agent, path in zip(scenario.agents, solution_paths)
        ]
        makespan = max((len(path) - 1 for path in solution_paths), default=0)
        return ExecutionResult(
            id=f"{scenario.id}_icts_{uuid.uuid4().hex[:8]}",
            scenario_id=scenario.id,
            algorithm=self.name,
            status="success",
            paths=paths,
            seed=seed,
            runtime_ms=(time.perf_counter() - start_time) * 1000,
            makespan=makespan,
            sum_of_costs=float(sum(costs)),
        )

    def _empty_success(
        self, scenario: Scenario, seed: int | None, start_time: float
    ) -> ExecutionResult:
        return ExecutionResult(
            id=f"{scenario.id}_icts_{uuid.uuid4().hex[:8]}",
            scenario_id=scenario.id,
            algorithm=self.name,
            status="success",
            paths=[],
            seed=seed,
            runtime_ms=(time.perf_counter() - start_time) * 1000,
            makespan=0,
            sum_of_costs=0.0,
        )

    def _no_solution(
        self, scenario: Scenario, seed: int | None, start_time: float
    ) -> ExecutionResult:
        return ExecutionResult(
            id=f"{scenario.id}_icts_{uuid.uuid4().hex[:8]}",
            scenario_id=scenario.id,
            algorithm=self.name,
            status="no_solution",
            paths=[],
            seed=seed,
            runtime_ms=(time.perf_counter() - start_time) * 1000,
            makespan=0,
            sum_of_costs=0.0,
        )
