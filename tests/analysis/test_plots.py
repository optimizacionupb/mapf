import matplotlib.animation
import matplotlib.figure

from analysis.plots import _position_at_time, animate_trajectories, plot_trajectories


def test_position_at_time_returns_exact_match_when_time_in_trajectory(result):
    trajectory = result.paths[0].trajectory  # agent 1: nodes 1,1,2,3 at times 0,1,2,3

    assert _position_at_time(trajectory, 2) == 2


def test_position_at_time_holds_last_node_after_trajectory_ends(result):
    trajectory = result.paths[1].trajectory  # agent 2: nodes 3,2,1 at times 0,1,2 (makespan is 3)

    assert _position_at_time(trajectory, 3) == 1


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


def test_animate_trajectories_returns_a_funcanimation(result, topology, tmp_path):
    animation = animate_trajectories(result, topology, output_path=tmp_path / "anim.gif")

    assert isinstance(animation, matplotlib.animation.FuncAnimation)


def test_animate_trajectories_saves_a_gif_with_one_frame_per_timestep(result, topology, tmp_path):
    from PIL import Image

    output_path = tmp_path / "anim.gif"

    animate_trajectories(result, topology, output_path=output_path)

    assert output_path.exists()
    assert output_path.stat().st_size > 0
    with Image.open(output_path) as gif:
        assert gif.n_frames == result.makespan + 1
