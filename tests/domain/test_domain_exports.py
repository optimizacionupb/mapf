def test_domain_package_exports_models_and_solver_contract():
    from domain import (
        Agent,
        AgentPath,
        ExecutionResult,
        GraphTopology,
        MAPFSolver,
        Node,
        Scenario,
        TrajectoryPoint,
    )

    assert all([Agent, AgentPath, ExecutionResult, GraphTopology, MAPFSolver, Node, Scenario, TrajectoryPoint])
