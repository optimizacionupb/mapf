import pytest

from domain.interfaces import MAPFSolver
from domain.models import Agent, ExecutionResult, GraphTopology, Scenario


def test_mapf_solver_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        MAPFSolver()


def test_concrete_solver_satisfies_the_contract():
    class EchoSolver(MAPFSolver):
        @property
        def name(self) -> str:
            return "echo"

        def solve(self, scenario: Scenario, seed: int | None = None) -> ExecutionResult:
            return ExecutionResult(
                id="r1",
                scenario_id=scenario.id,
                algorithm=self.name,
                status="success",
                paths=[],
                seed=seed,
                runtime_ms=0.0,
                makespan=0,
                sum_of_costs=0.0,
            )

    solver = EchoSolver()
    scenario = Scenario(
        id="s1",
        topology=GraphTopology(id="t1", description="", nodes={}, adjacency={}),
        agents=[Agent(id=1, start=1, goal=1)],
        description="",
    )

    assert isinstance(solver, MAPFSolver)
    assert solver.name == "echo"
    assert solver.solve(scenario).algorithm == "echo"
