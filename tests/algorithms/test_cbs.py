from domain.models import Agent, GraphTopology, Scenario
from algorithms.cbs import CBSSolver


def _line_topology() -> GraphTopology:
    from domain.models import Node

    nodes = {1: Node(1, 0.0, 0.0), 2: Node(2, 1.0, 0.0), 3: Node(3, 2.0, 0.0)}
    adjacency = {
        1: [(2, 1.0)],
        2: [(1, 1.0), (3, 1.0)],
        3: [(2, 1.0)],
    }
    return GraphTopology(id="line3", description="1-2-3 line", nodes=nodes, adjacency=adjacency)


def _hub_topology() -> GraphTopology:
    """1-2-3 line plus a side branch 2-4, giving a passing bay to avoid a head-on conflict."""
    from domain.models import Node

    nodes = {
        1: Node(1, 0.0, 0.0),
        2: Node(2, 1.0, 0.0),
        3: Node(3, 2.0, 0.0),
        4: Node(4, 1.0, 1.0),
    }
    adjacency = {
        1: [(2, 1.0)],
        2: [(1, 1.0), (3, 1.0), (4, 1.0)],
        3: [(2, 1.0)],
        4: [(2, 1.0)],
    }
    return GraphTopology(id="hub4", description="line with a side branch", nodes=nodes, adjacency=adjacency)


def _two_node_topology() -> GraphTopology:
    from domain.models import Node

    nodes = {1: Node(1, 0.0, 0.0), 2: Node(2, 1.0, 0.0)}
    adjacency = {1: [(2, 1.0)], 2: [(1, 1.0)]}
    return GraphTopology(id="edge2", description="single edge A-B", nodes=nodes, adjacency=adjacency)


def _has_conflict(paths: dict[int, list[tuple[int, int]]]) -> bool:
    agent_ids = sorted(paths)
    max_time = max(p[-1][1] for p in paths.values())

    def pos_at(path, t):
        return path[min(t, len(path) - 1)][0]

    for t in range(max_time + 1):
        positions = {a: pos_at(paths[a], t) for a in agent_ids}
        for i, a1 in enumerate(agent_ids):
            for a2 in agent_ids[i + 1 :]:
                if positions[a1] == positions[a2]:
                    return True
                if t > 0:
                    p1, p2 = paths[a1], paths[a2]
                    if t < len(p1) and t < len(p2):
                        u1, v1 = p1[t - 1][0], p1[t][0]
                        u2, v2 = p2[t - 1][0], p2[t][0]
                        if u1 == v2 and v1 == u2 and u1 != v1:
                            return True
    return False


def test_single_agent_finds_shortest_path():
    topology = _line_topology()
    scenario = Scenario(
        id="s1", topology=topology, agents=[Agent(id=1, start=1, goal=3)], description=""
    )

    result = CBSSolver().solve(scenario)

    assert result.status == "success"
    assert result.makespan == 2
    assert result.sum_of_costs == 2.0
    assert len(result.paths) == 1
    points = result.paths[0].trajectory
    assert [(p.node, p.time) for p in points] == [(1, 0), (2, 1), (3, 2)]


def test_resolves_head_on_conflict_using_a_passing_bay():
    topology = _hub_topology()
    scenario = Scenario(
        id="s2",
        topology=topology,
        agents=[Agent(id=1, start=1, goal=3), Agent(id=2, start=3, goal=1)],
        description="",
    )

    result = CBSSolver().solve(scenario)

    assert result.status == "success"

    paths = {p.agent: [(pt.node, pt.time) for pt in p.trajectory] for p in result.paths}
    assert paths[1][-1][0] == 3
    assert paths[2][-1][0] == 1
    assert not _has_conflict(paths)


def test_returns_no_solution_for_unsolvable_two_node_swap():
    topology = _two_node_topology()
    scenario = Scenario(
        id="s3",
        topology=topology,
        agents=[Agent(id=1, start=1, goal=2), Agent(id=2, start=2, goal=1)],
        description="",
    )

    result = CBSSolver(max_iterations=50).solve(scenario)

    assert result.status == "no_solution"
    assert result.paths == []


def test_result_carries_scenario_and_algorithm_metadata():
    topology = _line_topology()
    scenario = Scenario(
        id="s4", topology=topology, agents=[Agent(id=1, start=1, goal=3)], description=""
    )

    result = CBSSolver().solve(scenario, seed=7)

    assert result.scenario_id == "s4"
    assert result.algorithm == "cbs"
    assert result.seed == 7
    assert result.runtime_ms >= 0.0
