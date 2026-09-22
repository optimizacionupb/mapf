import matplotlib.figure

from analysis.plots import plot_trajectories


def test_returns_a_figure_when_no_output_path_given(result, topology):
    figure = plot_trajectories(result, topology)

    assert isinstance(figure, matplotlib.figure.Figure)
    assert len(figure.axes) == 1
    agent_labels = {line.get_label() for line in figure.axes[0].lines if not line.get_label().startswith("_")}
    assert agent_labels == {f"agent {p.agent}" for p in result.paths}


def test_saves_png_when_output_path_given(result, topology, tmp_path):
    output_path = tmp_path / "plot.png"

    plot_trajectories(result, topology, output_path=output_path)

    assert output_path.exists()
    assert output_path.stat().st_size > 0
