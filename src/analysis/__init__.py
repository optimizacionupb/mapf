"""Analysis layer: computes metrics and renders trajectory plots from an ExecutionResult."""

from analysis.analyze import analyze
from analysis.metrics import compute_metrics
from analysis.plots import animate_trajectories, plot_trajectories

__all__ = ["analyze", "animate_trajectories", "compute_metrics", "plot_trajectories"]
