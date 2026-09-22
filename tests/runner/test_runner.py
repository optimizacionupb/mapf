import json

import pytest

from runner import main


def test_json_format_runs_cbs_and_saves_result(scenario_json_path, topologies_dir, tmp_path):
    output_dir = tmp_path / "results"

    output_path = main(
        [
            "--format",
            "json",
            "--scenario-json",
            str(scenario_json_path),
            "--topologies-dir",
            str(topologies_dir),
            "--algorithm",
            "cbs",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert output_path.exists()
    assert output_path.parent.name == "cbs"
    assert output_path.parent.parent.name == "small_line_3_one_agent"

    payload = json.loads(output_path.read_text())
    assert payload["scenario_id"] == "small_line_3_one_agent"
    assert payload["algorithm"] == "cbs"
    assert payload["status"] == "success"
    assert len(payload["paths"]) == 1


def test_movingai_format_runs_cbs_and_saves_result(tiny_map_path, tiny_scen_path, tmp_path):
    output_dir = tmp_path / "results"

    output_path = main(
        [
            "--format",
            "movingai",
            "--map",
            str(tiny_map_path),
            "--scen",
            str(tiny_scen_path),
            "--agents",
            "1",
            "--algorithm",
            "cbs",
            "--output-dir",
            str(output_dir),
        ]
    )

    payload = json.loads(output_path.read_text())
    assert payload["status"] == "success"
    assert payload["algorithm"] == "cbs"


def test_visualize_flag_writes_metrics_plot_and_gif_for_a_successful_run(scenario_json_path, topologies_dir, tmp_path):
    output_dir = tmp_path / "results"

    output_path = main(
        [
            "--format",
            "json",
            "--scenario-json",
            str(scenario_json_path),
            "--topologies-dir",
            str(topologies_dir),
            "--algorithm",
            "cbs",
            "--output-dir",
            str(output_dir),
            "--visualize",
        ]
    )

    result_dir = output_path.parent
    result_id = output_path.stem

    metrics_path = result_dir / f"{result_id}_metrics.json"
    plot_path = result_dir / f"{result_id}_trajectories.png"
    gif_path = result_dir / f"{result_id}.gif"

    assert metrics_path.exists()
    metrics = json.loads(metrics_path.read_text())
    assert metrics["success"] is True

    assert plot_path.exists() and plot_path.stat().st_size > 0
    assert gif_path.exists() and gif_path.stat().st_size > 0


def test_visualize_flag_skips_plot_and_gif_when_no_solution_found(unsolvable_scenario_json_path, unsolvable_topologies_dir, tmp_path):
    output_dir = tmp_path / "results"

    output_path = main(
        [
            "--format",
            "json",
            "--scenario-json",
            str(unsolvable_scenario_json_path),
            "--topologies-dir",
            str(unsolvable_topologies_dir),
            "--algorithm",
            "cbs",
            "--output-dir",
            str(output_dir),
            "--visualize",
        ]
    )

    result_dir = output_path.parent
    result_id = output_path.stem

    payload = json.loads(output_path.read_text())
    assert payload["status"] == "no_solution"

    metrics_path = result_dir / f"{result_id}_metrics.json"
    assert metrics_path.exists()
    metrics = json.loads(metrics_path.read_text())
    assert metrics["success"] is False

    assert not (result_dir / f"{result_id}_trajectories.png").exists()
    assert not (result_dir / f"{result_id}.gif").exists()


def test_json_format_without_scenario_json_errors(tmp_path):
    with pytest.raises(SystemExit):
        main(["--format", "json", "--output-dir", str(tmp_path / "results")])


def test_movingai_format_without_map_errors(tmp_path):
    with pytest.raises(SystemExit):
        main(["--format", "movingai", "--output-dir", str(tmp_path / "results")])
