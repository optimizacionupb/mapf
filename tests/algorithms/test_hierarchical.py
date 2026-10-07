import pytest

from domain.models import Agent, ExecutionResult, GraphTopology, Node, Scenario
from algorithms.hierarchical import HierarchicalSolver


def _line_topology() -> GraphTopology:
    nodes = {1: Node(1, 0.0, 0.0), 2: Node(2, 1.0, 0.0), 3: Node(3, 2.0, 0.0)}
    adjacency = {1: [(2, 1.0)], 2: [(1, 1.0), (3, 1.0)], 3: [(2, 1.0)]}
    return GraphTopology(id="line3", description="1-2-3 line", nodes=nodes, adjacency=adjacency)


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


def _as_dict(result: ExecutionResult) -> dict[int, list[tuple[int, int]]]:
    return {p.agent: [(pt.node, pt.time) for pt in p.trajectory] for p in result.paths}


def test_returns_execution_result_with_algorithm_name():
    scenario = Scenario(id="h0", topology=_line_topology(), agents=[Agent(id=1, start=1, goal=3)], description="")

    result = HierarchicalSolver().solve(scenario, seed=0)

    assert isinstance(result, ExecutionResult)
    assert result.algorithm == "hierarchical"
    assert result.scenario_id == "h0"
    assert result.seed == 0


def test_single_agent_follows_shortest_path():
    scenario = Scenario(id="h1", topology=_line_topology(), agents=[Agent(id=1, start=1, goal=3)], description="")

    result = HierarchicalSolver().solve(scenario, seed=0)

    assert result.status == "success"
    assert result.makespan == 2
    assert result.sum_of_costs == 2.0
    assert [(p.node, p.time) for p in result.paths[0].trajectory] == [(1, 0), (2, 1), (3, 2)]


def test_returns_no_solution_for_unsolvable_two_node_swap():
    scenario = Scenario(
        id="h2",
        topology=_two_node_topology(),
        agents=[Agent(id=1, start=1, goal=2), Agent(id=2, start=2, goal=1)],
        description="",
    )

    result = HierarchicalSolver(samples=20, max_cycles=2).solve(scenario, seed=0)

    assert result.status == "no_solution"
    assert result.paths == []
    assert result.makespan == 0
    assert result.sum_of_costs == 0.0


def test_several_agents_on_grid_are_conflict_free():
    topology = _grid_topology(4, 4)
    agents = [
        Agent(id=1, start=0, goal=15),
        Agent(id=2, start=15, goal=0),
        Agent(id=3, start=3, goal=12),
        Agent(id=4, start=12, goal=3),
    ]
    scenario = Scenario(id="h3", topology=topology, agents=agents, description="")

    result = HierarchicalSolver().solve(scenario, seed=1)

    assert result.status == "success"
    paths = _as_dict(result)
    assert {a: p[-1][0] for a, p in paths.items()} == {1: 15, 2: 0, 3: 12, 4: 3}
    assert not _has_conflict(paths)


def test_same_seed_gives_same_solution():
    topology = _grid_topology(4, 4)
    agents = [Agent(id=1, start=0, goal=15), Agent(id=2, start=15, goal=0)]
    scenario = Scenario(id="h4", topology=topology, agents=agents, description="")

    first = HierarchicalSolver().solve(scenario, seed=7)
    second = HierarchicalSolver().solve(scenario, seed=7)

    assert _as_dict(first) == _as_dict(second)
    assert first.sum_of_costs == second.sum_of_costs


@pytest.mark.xfail(
    reason="Rutas espaciales simples no pueden apartarse a un nodo sin salida y volver: "
    "el head-on de _hub_topology requiere una ruta con retroceso.",
    strict=True,
)
def test_resolves_head_on_conflict_using_a_passing_bay():
    nodes = {1: Node(1, 0.0, 0.0), 2: Node(2, 1.0, 0.0), 3: Node(3, 2.0, 0.0), 4: Node(4, 1.0, 1.0)}
    adjacency = {1: [(2, 1.0)], 2: [(1, 1.0), (3, 1.0), (4, 1.0)], 3: [(2, 1.0)], 4: [(2, 1.0)]}
    hub = GraphTopology(id="hub4", description="line with a side branch", nodes=nodes, adjacency=adjacency)
    scenario = Scenario(
        id="h5",
        topology=hub,
        agents=[Agent(id=1, start=1, goal=3), Agent(id=2, start=3, goal=1)],
        description="",
    )

    result = HierarchicalSolver().solve(scenario, seed=0)

    assert result.status == "success"
    assert not _has_conflict(_as_dict(result))
