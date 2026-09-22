from pathlib import Path

import pytest

from data_loaders.movingai_loader import MovingAILoader


def test_map_parses_grid_into_passable_nodes_and_4_neighbor_adjacency(tiny_map_file, tiny_scen_file):
    scenario = MovingAILoader(tiny_map_file, tiny_scen_file, num_agents=1).load()
    topology = scenario.topology

    assert len(topology.nodes) == 8
    assert 4 not in topology.nodes
    assert topology.nodes[1].x == 1.0
    assert topology.nodes[1].y == 0.0
    assert set(topology.adjacency[0]) == {(1, 1.0), (3, 1.0)}
    assert set(topology.adjacency[8]) == {(5, 1.0), (7, 1.0)}


def test_scen_parses_agents_with_sequential_ids(tiny_map_file, tiny_scen_file):
    scenario = MovingAILoader(tiny_map_file, tiny_scen_file, num_agents=2).load()

    assert [a.id for a in scenario.agents] == [1, 2]
    assert scenario.agents[0].start == 0
    assert scenario.agents[0].goal == 8
    assert scenario.agents[1].start == 2
    assert scenario.agents[1].goal == 6


def test_missing_map_file_raises_file_not_found(tmp_path, tiny_scen_file):
    with pytest.raises(FileNotFoundError):
        MovingAILoader(tmp_path / "missing.map", tiny_scen_file, num_agents=1).load()


def test_missing_scen_file_raises_file_not_found(tmp_path, tiny_map_file):
    with pytest.raises(FileNotFoundError):
        MovingAILoader(tiny_map_file, tmp_path / "missing.scen", num_agents=1).load()


def test_malformed_map_header_raises_value_error(tmp_path, tiny_scen_file):
    bad_map = tmp_path / "bad.map"
    bad_map.write_text("type octile\nheight 3\nwidth abc\nmap\n...\n...\n...\n")

    with pytest.raises(ValueError):
        MovingAILoader(bad_map, tiny_scen_file, num_agents=1).load()


def test_requesting_more_agents_than_available_raises_value_error(tiny_map_file, tiny_scen_file):
    with pytest.raises(ValueError):
        MovingAILoader(tiny_map_file, tiny_scen_file, num_agents=10).load()


def test_mismatched_map_dimensions_raises_value_error(tmp_path, tiny_map_file):
    bad_scen = tmp_path / "bad.scen"
    bad_scen.write_text("version 1\n0\ttiny.map\t9\t9\t0\t0\t2\t2\t2.0\n")

    with pytest.raises(ValueError):
        MovingAILoader(tiny_map_file, bad_scen, num_agents=1).load()


def test_start_on_obstacle_raises_value_error(tmp_path, tiny_map_file):
    bad_scen = tmp_path / "bad.scen"
    bad_scen.write_text("version 1\n0\ttiny.map\t3\t3\t1\t1\t2\t2\t2.0\n")

    with pytest.raises(ValueError):
        MovingAILoader(tiny_map_file, bad_scen, num_agents=1).load()


def test_loads_real_berlin_benchmark(berlin_map_path, berlin_scen_path):
    scenario = MovingAILoader(berlin_map_path, berlin_scen_path, num_agents=5).load()

    assert len(scenario.agents) == 5
    assert scenario.agents[0].start == 3741
    assert scenario.agents[0].goal == 57827
