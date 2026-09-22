from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path

from algorithms import CBSSolver
from analysis import animate_trajectories, compute_metrics, plot_trajectories
from data_loaders import JSONScenarioLoader, MovingAILoader, ScenarioLoader
from domain import ExecutionResult, GraphTopology, MAPFSolver

SOLVERS: dict[str, type[MAPFSolver]] = {
    "cbs": CBSSolver,
}


def build_arg_parser() -> argparse.ArgumentParser:
    """Builds the CLI argument parser for the scenario execution pipeline."""
    parser = argparse.ArgumentParser(description="Load a MAPF scenario, run a solver, and save the result.")
    parser.add_argument("--format", choices=["json", "movingai"], required=True)
    parser.add_argument("--map", type=Path, help="Path to a .map file (movingai format).")
    parser.add_argument("--scen", type=Path, help="Path to a .scen file (movingai format).")
    parser.add_argument("--scenario-json", type=Path, help="Path to a scenario JSON file (json format).")
    parser.add_argument(
        "--topologies-dir", type=Path, default=Path("data/topologies"), help="Topology JSON directory (json format)."
    )
    parser.add_argument("--agents", type=int, default=10, help="Number of agents to load (movingai format).")
    parser.add_argument("--algorithm", choices=sorted(SOLVERS), default="cbs")
    parser.add_argument("--output-dir", type=Path, default=Path("data/results"))
    parser.add_argument(
        "--visualize", action="store_true", help="Also write metrics, a trajectory plot, and a GIF animation."
    )
    return parser


def _build_loader(args: argparse.Namespace, parser: argparse.ArgumentParser) -> ScenarioLoader:
    if args.format == "json":
        if args.scenario_json is None:
            parser.error("--scenario-json is required when --format=json")
        return JSONScenarioLoader(args.scenario_json, args.topologies_dir)

    if args.map is None or args.scen is None:
        parser.error("--map and --scen are required when --format=movingai")
    return MovingAILoader(args.map, args.scen, num_agents=args.agents)


def _save_result(result: ExecutionResult, scenario_id: str, algorithm: str, output_dir: Path) -> Path:
    output_path = output_dir / scenario_id / algorithm / f"{result.id}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(dataclasses.asdict(result), indent=2))
    return output_path


def _visualize(result: ExecutionResult, topology: GraphTopology, output_path: Path) -> None:
    metrics = compute_metrics(result)
    metrics_path = output_path.with_name(f"{output_path.stem}_metrics.json")
    metrics_path.write_text(json.dumps(metrics, indent=2))
    print(
        f"Metrics: success={metrics['success']} makespan={metrics['makespan']} "
        f"sum_of_costs={metrics['sum_of_costs']} runtime_ms={metrics['runtime_ms']:.1f}"
    )

    if not result.paths:
        print("No successful paths — skipping plot and animation.")
        return

    plot_path = output_path.with_name(f"{output_path.stem}_trajectories.png")
    plot_trajectories(result, topology, output_path=plot_path)
    print(f"Plot saved to {plot_path}")

    gif_path = output_path.with_name(f"{output_path.stem}.gif")
    animate_trajectories(result, topology, output_path=gif_path)
    print(f"Animation saved to {gif_path}")


def main(argv: list[str] | None = None) -> Path:
    """Loads a scenario, runs the selected solver, and saves the ExecutionResult as JSON."""
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    loader = _build_loader(args, parser)
    scenario = loader.load()

    solver = SOLVERS[args.algorithm]()
    result = solver.solve(scenario)

    output_path = _save_result(result, scenario.id, args.algorithm, args.output_dir)
    print(f"Result saved to {output_path}")

    if args.visualize:
        _visualize(result, scenario.topology, output_path)

    return output_path


if __name__ == "__main__":
    main()
