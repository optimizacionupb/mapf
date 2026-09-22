---
icon: lucide/plug
---

# Adding an algorithm

Any MAPF algorithm can be plugged in as long as it implements the `MAPFSolver` contract
(`src/domain/interfaces.py`). Nothing else in the project needs to change.

## 1. Implement `MAPFSolver`

```python
# src/algorithms/my_solver.py
from domain import Agent, ExecutionResult, MAPFSolver, Scenario


class MySolver(MAPFSolver):
    @property
    def name(self) -> str:
        return "my_solver"

    def solve(self, scenario: Scenario, seed: int | None = None) -> ExecutionResult:
        # scenario.topology.nodes / .adjacency describe the graph
        # scenario.agents gives you each Agent.start / .goal
        # build one AgentPath per agent, then:
        return ExecutionResult(
            id=f"{scenario.id}_{self.name}",
            scenario_id=scenario.id,
            algorithm=self.name,
            status="success",  # or "no_solution"
            paths=[...],
            seed=seed,
            runtime_ms=...,
            makespan=...,
            sum_of_costs=...,
        )
```

`src/algorithms/cbs.py` is a complete reference implementation to copy patterns from —
in particular how it turns a `GraphTopology`'s `adjacency` into single-agent paths.

## 2. Register it

Add it to `SOLVERS` in `src/runner.py`:

```python
from algorithms.my_solver import MySolver

SOLVERS: dict[str, type[MAPFSolver]] = {
    "cbs": CBSSolver,
    "my_solver": MySolver,
}
```

## 3. Run it

```bash
uv run python -m runner --format movingai --map <path.map> --scen <path.scen> --algorithm my_solver
```

## 4. Test it

Write tests the same way `tests/algorithms/test_cbs.py` does: build a small
`Scenario` by hand, call `.solve()`, and assert the result is conflict-free (every
agent's path only steps to a graph neighbor or waits, and no two agents ever share a
node or swap across the same edge at the same time).
