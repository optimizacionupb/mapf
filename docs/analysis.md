---
icon: lucide/chart-line
---

# Analysis & visualization

`src/analysis/` turns a saved `ExecutionResult` into metrics, a static plot, and a GIF
animation. It only depends on `domain` — it knows nothing about solvers or file formats.

## One-command flow

Pass `--visualize` to the runner and, right after solving, it also writes:

```bash
uv run python -m runner \
    --format movingai --map <path.map> --scen <path.scen> \
    --agents 10 --algorithm cbs \
    --visualize
```

```
data/results/<scenario_id>/<algorithm>/
  <result_id>.json               # the ExecutionResult
  <result_id>_metrics.json       # compute_metrics() output
  <result_id>_trajectories.png   # plot_trajectories() output
  <result_id>.gif                # animate_trajectories() output
```

If the solver doesn't find a solution (`status == "no_solution"`), the plot and
animation are skipped — there are no paths to draw — but metrics are still written.

## Functions (`src/analysis/`)

- `compute_metrics(result) -> dict` (`metrics.py`) — aggregates (`makespan`,
  `sum_of_costs`, `avg_cost`, `runtime_ms`, `success`) plus a `moves`/`waits` breakdown
  computed from every agent's trajectory.
- `plot_trajectories(result, topology, output_path=None)` (`plots.py`) — draws the
  topology as a static background (all edges as a single `Line2D`, to stay fast on
  maps with thousands of edges) with each agent's path overlaid.
- `animate_trajectories(result, topology, output_path, fps=2)` (`plots.py`) — one
  frame per timestep (`0..makespan`), each agent shown as a dot with a fading trail.
  An agent that reaches its goal before `makespan` just holds there for the remaining
  frames. Saved as a GIF via `matplotlib`'s `PillowWriter`.
- `analyze(result_path) -> dict` (`analyze.py`) — reloads a saved result JSON and
  returns `compute_metrics()` for it, for post-hoc analysis outside the runner (e.g.
  in a notebook under `src/notebooks/`).

Because `runner.py` already holds the `Scenario` (and therefore its `GraphTopology`)
in memory right after solving, `--visualize` calls these functions directly instead of
reloading anything from disk — the topology is never persisted separately.
