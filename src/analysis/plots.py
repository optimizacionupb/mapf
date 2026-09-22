from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.animation
import matplotlib.artist
import matplotlib.axes
import matplotlib.figure
import matplotlib.pyplot as plt

from domain.models import ExecutionResult, GraphTopology, TrajectoryPoint

AGENT_COLORS = plt.rcParams["axes.prop_cycle"].by_key()["color"]


def _position_at_time(trajectory: list[TrajectoryPoint], time: int) -> int:
    """Returns the node an agent occupies at a given time, holding at its last node once its trajectory ends."""
    node = trajectory[0].node
    for point in trajectory:
        if point.time > time:
            break
        node = point.node
    return node


def _draw_topology(ax: matplotlib.axes.Axes, topology: GraphTopology) -> None:
    """Draws a topology's edges and nodes as the static background of a plot.

    All edges are drawn as a single Line2D with NaN breaks between segments — one
    ax.plot() call per edge is too slow for maps with thousands of edges.
    """
    edge_xs: list[float] = []
    edge_ys: list[float] = []
    for node_id, edges in topology.adjacency.items():
        x0, y0 = topology.nodes[node_id].x, topology.nodes[node_id].y
        for neighbor_id, _ in edges:
            x1, y1 = topology.nodes[neighbor_id].x, topology.nodes[neighbor_id].y
            edge_xs.extend((x0, x1, float("nan")))
            edge_ys.extend((y0, y1, float("nan")))
    ax.plot(edge_xs, edge_ys, color="lightgray", zorder=1, linewidth=1)

    xs = [node.x for node in topology.nodes.values()]
    ys = [node.y for node in topology.nodes.values()]
    ax.scatter(xs, ys, color="lightblue", zorder=2, s=100)


def plot_trajectories(
    result: ExecutionResult, topology: GraphTopology, output_path: Path | None = None
) -> matplotlib.figure.Figure:
    """Plots the topology and every agent's trajectory from an ExecutionResult over it."""
    figure, ax = plt.subplots()
    _draw_topology(ax, topology)

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


def animate_trajectories(
    result: ExecutionResult, topology: GraphTopology, output_path: Path, fps: int = 2
) -> matplotlib.animation.FuncAnimation:
    """Animates every agent stepping through its trajectory over the topology, saving a GIF to output_path."""
    figure, ax = plt.subplots()
    _draw_topology(ax, topology)
    ax.set_title(f"{result.scenario_id} — {result.algorithm}")
    ax.set_aspect("equal")

    dots = []
    trails = []
    for i, path in enumerate(result.paths):
        color = AGENT_COLORS[i % len(AGENT_COLORS)]
        (trail,) = ax.plot([], [], color=color, alpha=0.4, zorder=2)
        (dot,) = ax.plot([], [], marker="o", color=color, zorder=3, label=f"agent {path.agent}")
        trails.append(trail)
        dots.append(dot)
    ax.legend()

    def update(time: int) -> list[matplotlib.artist.Artist]:
        for path, dot, trail in zip(result.paths, dots, trails):
            visited = [_position_at_time(path.trajectory, t) for t in range(time + 1)]
            xs = [topology.nodes[n].x for n in visited]
            ys = [topology.nodes[n].y for n in visited]
            trail.set_data(xs, ys)
            dot.set_data(xs[-1:], ys[-1:])
        return [*trails, *dots]

    animation = matplotlib.animation.FuncAnimation(
        figure, update, frames=range(result.makespan + 1), blit=True
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    animation.save(output_path, writer=matplotlib.animation.PillowWriter(fps=fps))
    return animation
