from domain.models import (
    Agent,
    AgentPath,
    ExecutionResult,
    GraphTopology,
    Node,
    Scenario,
    TrajectoryPoint,
)


def test_node_holds_id_and_coordinates():
    node = Node(id=1, x=2.0, y=3.0)
    assert node.id == 1
    assert node.x == 2.0
    assert node.y == 3.0


def test_node_equality_by_value():
    assert Node(id=1, x=2.0, y=3.0) == Node(id=1, x=2.0, y=3.0)


def test_graph_topology_holds_nodes_and_adjacency():
    nodes = {1: Node(id=1, x=0.0, y=0.0), 2: Node(id=2, x=1.0, y=0.0)}
    adjacency = {1: [(2, 1.0)], 2: [(1, 1.0)]}

    topology = GraphTopology(id="t1", description="line", nodes=nodes, adjacency=adjacency)

    assert topology.id == "t1"
    assert topology.nodes[1] is nodes[1]
    assert topology.adjacency[1] == [(2, 1.0)]


def test_agent_holds_id_start_and_goal():
    agent = Agent(id=1, start=2, goal=3)
    assert agent.id == 1
    assert agent.start == 2
    assert agent.goal == 3


def test_scenario_holds_topology_and_agents():
    nodes = {1: Node(id=1, x=0.0, y=0.0), 2: Node(id=2, x=1.0, y=0.0)}
    topology = GraphTopology(id="t1", description="line", nodes=nodes, adjacency={1: [], 2: []})
    agents = [Agent(id=1, start=1, goal=2)]

    scenario = Scenario(id="s1", topology=topology, agents=agents, description="one agent")

    assert scenario.topology is topology
    assert scenario.agents == agents


def test_agent_path_holds_agent_and_trajectory():
    trajectory = [TrajectoryPoint(node=1, time=0), TrajectoryPoint(node=2, time=1)]

    path = AgentPath(agent=1, trajectory=trajectory)

    assert path.agent == 1
    assert path.trajectory == trajectory


def test_execution_result_holds_run_metadata_and_paths():
    paths = [AgentPath(agent=1, trajectory=[TrajectoryPoint(node=1, time=0)])]

    result = ExecutionResult(
        id="r1",
        scenario_id="s1",
        algorithm="cbs",
        status="success",
        paths=paths,
        seed=42,
        runtime_ms=12.5,
        makespan=1,
        sum_of_costs=1.0,
    )

    assert result.scenario_id == "s1"
    assert result.paths == paths
    assert result.seed == 42
