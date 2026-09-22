from __future__ import annotations

import argparse
import dataclasses
import json
from pathlib import Path

from algorithms import CBSSolver
from data_loaders import JSONScenarioLoader, MovingAILoader, ScenarioLoader
from domain import ExecutionResult, MAPFSolver

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
    return output_path


if __name__ == "__main__":
    main()
