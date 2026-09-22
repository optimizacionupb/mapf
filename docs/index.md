---
icon: lucide/rocket
---

# MAPF

A benchmark platform for **Multi-Agent Path Finding (MAPF)**: given a map and a set of
agents that each need to get from a start location to a goal, find a collision-free path
for every agent while keeping total travel time low.

The project is split into five decoupled layers:

- **Domain models** — plain data (`Node`, `Scenario`, `Agent`, `ExecutionResult`, ...) with
  no algorithm logic attached.
- **Data loaders** — adapters that turn an external file format (a custom JSON schema, or
  the Moving AI Lab `.map`/`.scen` benchmark format) into a domain `Scenario`.
- **Algorithms** — solvers (currently Conflict-Based Search) that implement a common
  `MAPFSolver` contract, so new algorithms can be added without touching anything else.
- **Runner** — a CLI that wires a loader and a solver together, and saves the result.
- **Analysis** — computes metrics and renders a trajectory plot and GIF animation from a
  solve, optionally in the same command as the runner.

See [Architecture](architecture.md) for how these fit together,
[Adding an algorithm](extending.md) if you want to plug in your own solver, and
[Analysis & visualization](analysis.md) for metrics, plots, and animations.

For the problem statement itself — what MAPF is, and the objective/constraints this
project optimizes — see the [project README](https://github.com/optimizacionupb/mapf#readme).

## Quick start

```bash
uv sync
uv run python -m runner --format movingai --map <path.map> --scen <path.scen> --agents 10 --algorithm cbs
uv run pytest
```
