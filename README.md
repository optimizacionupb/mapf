# MAPF — Multi-Agent Path Finding benchmark platform

A decoupled MAPF experimentation platform: pure domain models (`src/domain`), a Strategy-pattern solver
contract (`src/domain/interfaces.py`) with a Conflict-Based Search implementation (`src/algorithms/cbs.py`),
an Adapter-pattern data loader layer for custom JSON and Moving AI `.map`/`.scen` scenarios
(`src/data_loaders`), and a CLI runner (`src/runner.py`) that loads a scenario, runs a solver, and
saves the `ExecutionResult` to `data/results/<scenario_id>/<algorithm>/<result_id>.json`.

## Cómo ejecutar

Requiere [`uv`](https://docs.astral.sh/uv/) y Python ≥ 3.12.

```bash
uv sync    # instala dependencias
uv run pytest    # corre los tests
uv run python -m runner --format json --scenario-json <path> --topologies-dir <dir> --algorithm cbs
uv run python -m runner --format movingai --map <path.map> --scen <path.scen> --agents 10 --algorithm cbs
```
