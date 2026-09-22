from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from analysis.metrics import compute_metrics
from domain.models import AgentPath, ExecutionResult, TrajectoryPoint


def _result_from_dict(data: dict[str, Any]) -> ExecutionResult:
    paths = [
        AgentPath(
            agent=p["agent"],
            trajectory=[TrajectoryPoint(node=tp["node"], time=tp["time"]) for tp in p["trajectory"]],
        )
        for p in data["paths"]
    ]
    return ExecutionResult(
        id=data["id"],
        scenario_id=data["scenario_id"],
        algorithm=data["algorithm"],
        status=data["status"],
        paths=paths,
        seed=data["seed"],
        runtime_ms=data["runtime_ms"],
        makespan=data["makespan"],
        sum_of_costs=data["sum_of_costs"],
    )


def analyze(result_path: str | Path) -> dict[str, Any]:
    """Loads an ExecutionResult JSON file (as written by the runner) and returns its metrics."""
    data = json.loads(Path(result_path).read_text())
    return compute_metrics(_result_from_dict(data))
