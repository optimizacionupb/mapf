from __future__ import annotations

from typing import Any

from domain.models import ExecutionResult


def compute_metrics(result: ExecutionResult) -> dict[str, Any]:
    """Computes summary metrics for one ExecutionResult: aggregates plus per-agent breakdown."""
    moves = 0
    waits = 0
    for path in result.paths:
        for prev, curr in zip(path.trajectory, path.trajectory[1:]):
            if prev.node == curr.node:
                waits += 1
            else:
                moves += 1

    avg_cost = result.sum_of_costs / len(result.paths) if result.paths else 0.0

    return {
        "makespan": result.makespan,
        "sum_of_costs": result.sum_of_costs,
        "avg_cost": avg_cost,
        "moves": moves,
        "waits": waits,
        "success": result.status == "success",
        "runtime_ms": result.runtime_ms,
    }
