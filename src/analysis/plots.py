from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.figure
import matplotlib.pyplot as plt

from domain.models import ExecutionResult, GraphTopology


def plot_trajectories(
    result: ExecutionResult, topology: GraphTopology, output_path: Path | None = None
) -> matplotlib.figure.Figure:
    """Plots the topology and every agent's trajectory from an ExecutionResult over it."""
    figure, ax = plt.subplots()

    for node_id, edges in topology.adjacency.items():
        x0, y0 = topology.nodes[node_id].x, topology.nodes[node_id].y
        for neighbor_id, _ in edges:
            x1, y1 = topology.nodes[neighbor_id].x, topology.nodes[neighbor_id].y
            ax.plot([x0, x1], [y0, y1], color="lightgray", zorder=1, linewidth=1)

    xs = [node.x for node in topology.nodes.values()]
    ys = [node.y for node in topology.nodes.values()]
    ax.scatter(xs, ys, color="lightblue", zorder=2, s=100)

    for path in result.paths:
        coords = [(topology.nodes[p.node].x, topology.nodes[p.node].y) for p in path.trajectory]
        px = [c[0] for c in coords]
        py = [c[1] for c in coords]
        ax.plot(px, py, marker="o", zorder=3, label=f"agent {path.agent}")

    ax.set_title(f"{result.scenario_id} — {result.algorithm}")
    ax.legend()
    ax.set_aspect("equal")

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        figure.savefig(output_path)

    return figure
