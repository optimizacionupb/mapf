import pytest

from domain.models import (
    AgentPath,
    ExecutionResult,
    GraphTopology,
    Node,
    TrajectoryPoint,
)


@pytest.fixture
def topology() -> GraphTopology:
    nodes = {1: Node(1, 0.0, 0.0), 2: Node(2, 1.0, 0.0), 3: Node(3, 2.0, 0.0)}
    adjacency = {1: [(2, 1.0)], 2: [(1, 1.0), (3, 1.0)], 3: [(2, 1.0)]}
    return GraphTopology(id="line3", description="1-2-3 line", nodes=nodes, adjacency=adjacency)


@pytest.fixture
def result() -> ExecutionResult:
    return ExecutionResult(
        id="scenario_001_cbs_abcd1234",
        scenario_id="scenario_001",
        algorithm="cbs",
        status="success",
        paths=[
            AgentPath(
                agent=1,
                trajectory=[
                    TrajectoryPoint(node=1, time=0),
                    TrajectoryPoint(node=1, time=1),
                    TrajectoryPoint(node=2, time=2),
                    TrajectoryPoint(node=3, time=3),
                ],
            ),
            AgentPath(
                agent=2,
                trajectory=[
                    TrajectoryPoint(node=3, time=0),
                    TrajectoryPoint(node=2, time=1),
                    TrajectoryPoint(node=1, time=2),
                ],
            ),
        ],
        seed=None,
        runtime_ms=12.5,
        makespan=3,
        sum_of_costs=5.0,
    )
