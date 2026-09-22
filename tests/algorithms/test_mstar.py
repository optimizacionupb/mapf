from domain.models import Agent, GraphTopology, Node, Scenario
from algorithms.mstar import MStarSolver, _individual_policy


def _line_topology() -> GraphTopology:
    nodes = {1: Node(1, 0.0, 0.0), 2: Node(2, 1.0, 0.0), 3: Node(3, 2.0, 0.0)}
    adjacency = {1: [(2, 1.0)], 2: [(1, 1.0), (3, 1.0)], 3: [(2, 1.0)]}
    return GraphTopology(id="line3", description="1-2-3 line", nodes=nodes, adjacency=adjacency)


def _hub_topology() -> GraphTopology:
    nodes = {1: Node(1, 0.0, 0.0), 2: Node(2, 1.0, 0.0), 3: Node(3, 2.0, 0.0), 4: Node(4, 1.0, 1.0)}
    adjacency = {1: [(2, 1.0)], 2: [(1, 1.0), (3, 1.0), (4, 1.0)], 3: [(2, 1.0)], 4: [(2, 1.0)]}
    return GraphTopology(id="hub4", description="line with a side branch", nodes=nodes, adjacency=adjacency)


def _two_node_topology() -> GraphTopology:
    nodes = {1: Node(1, 0.0, 0.0), 2: Node(2, 1.0, 0.0)}
    adjacency = {1: [(2, 1.0)], 2: [(1, 1.0)]}
    return GraphTopology(id="edge2", description="single edge A-B", nodes=nodes, adjacency=adjacency)


def _grid_topology(width: int, height: int) -> GraphTopology:
    """Open 4-connected grid; node id = y * width + x."""
    nodes = {y * width + x: Node(y * width + x, float(x), float(y)) for y in range(height) for x in range(width)}
    adjacency: dict[int, list[tuple[int, float]]] = {}
    for y in range(height):
        for x in range(width):
            nbrs = []
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    nbrs.append((ny * width + nx, 1.0))
            adjacency[y * width + x] = nbrs
    return GraphTopology(id=f"grid{width}x{height}", description="open grid", nodes=nodes, adjacency=adjacency)


def _has_conflict(paths: dict[int, list[tuple[int, int]]]) -> bool:
    agent_ids = sorted(paths)
    max_time = max(p[-1][1] for p in paths.values())

    def pos_at(path, t):
        return path[min(t, len(path) - 1)][0]

    for t in range(max_time + 1):
        for i, a1 in enumerate(agent_ids):
            for a2 in agent_ids[i + 1 :]:
                if pos_at(paths[a1], t) == pos_at(paths[a2], t):
                    return True
                if t > 0:
                    u1, v1 = pos_at(paths[a1], t - 1), pos_at(paths[a1], t)
                    u2, v2 = pos_at(paths[a2], t - 1), pos_at(paths[a2], t)
                    if u1 == v2 and v1 == u2 and u1 != v1:
                        return True
    return False


def _as_dict(result) -> dict[int, list[tuple[int, int]]]:
    return {p.agent: [(pt.node, pt.time) for pt in p.trajectory] for p in result.paths}


def test_individual_policy_on_hub():
    dist, next_step = _individual_policy(_hub_topology(), goal=3)
    assert dist == {3: 0.0, 2: 1.0, 1: 2.0, 4: 2.0}
    assert next_step[1] == (2, 1.0)
    assert next_step[2] == (3, 1.0)
    assert next_step[3] == (3, 0.0)


def test_single_agent_finds_shortest_path():
    scenario = Scenario(id="s1", topology=_line_topology(), agents=[Agent(id=1, start=1, goal=3)], description="")

    result = MStarSolver().solve(scenario)

    assert result.status == "success"
    assert result.makespan == 2
    assert result.sum_of_costs == 2.0
    assert [(p.node, p.time) for p in result.paths[0].trajectory] == [(1, 0), (2, 1), (3, 2)]


def test_resolves_head_on_conflict_using_a_passing_bay():
    scenario = Scenario(
        id="s2",
        topology=_hub_topology(),
        agents=[Agent(id=1, start=1, goal=3), Agent(id=2, start=3, goal=1)],
        description="",
    )

    result = MStarSolver().solve(scenario)

    assert result.status == "success"
    paths = _as_dict(result)
    assert paths[1][-1][0] == 3
    assert paths[2][-1][0] == 1
    assert not _has_conflict(paths)
    assert result.sum_of_costs == 7.0  # optimo: un agente se desvia al nodo 4 (4 pasos) y el otro espera 1 (3 pasos)


def test_returns_no_solution_for_unsolvable_two_node_swap():
    scenario = Scenario(
        id="s3",
        topology=_two_node_topology(),
        agents=[Agent(id=1, start=1, goal=2), Agent(id=2, start=2, goal=1)],
        description="",
    )

    result = MStarSolver().solve(scenario)

    assert result.status == "no_solution"
    assert result.paths == []


def test_several_agents_on_grid_are_conflict_free():
    topology = _grid_topology(4, 4)
    agents = [
        Agent(id=1, start=0, goal=15),
        Agent(id=2, start=15, goal=0),
        Agent(id=3, start=3, goal=12),
        Agent(id=4, start=12, goal=3),
    ]
    scenario = Scenario(id="s5", topology=topology, agents=agents, description="")

    result = MStarSolver().solve(scenario)

    assert result.status == "success"
    paths = _as_dict(result)
    for agent in agents:
        assert paths[agent.id][0][0] == agent.start
        assert paths[agent.id][-1][0] == agent.goal
    assert not _has_conflict(paths)
    assert result.sum_of_costs >= 4 * 6.0  # cota inferior: 6 pasos cada uno sin choques


def test_result_carries_scenario_and_algorithm_metadata():
    scenario = Scenario(id="s4", topology=_line_topology(), agents=[Agent(id=1, start=1, goal=3)], description="")

    result = MStarSolver().solve(scenario, seed=7)

    assert result.scenario_id == "s4"
    assert result.algorithm == "mstar"
    assert result.seed == 7
    assert result.runtime_ms >= 0.0