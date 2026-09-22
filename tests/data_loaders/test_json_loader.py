import json
from pathlib import Path

import pytest

from data_loaders.json_loader import JSONScenarioLoader


def test_load_builds_scenario_from_topology_and_scenario_json(scenario_path, topologies_dir):
    scenario = JSONScenarioLoader(scenario_path, topologies_dir).load()

    assert scenario.id == "small_line_3_two_agents"
    assert scenario.topology.id == "small_line_3"
    assert scenario.topology.nodes[1].x == 0.0
    assert scenario.topology.adjacency[1] == [(2, 1.0)]
    assert scenario.topology.adjacency[2] == [(1, 1.0), (3, 1.0)]
    assert [a.id for a in scenario.agents] == [1, 2]
    assert scenario.agents[0].start == 1
    assert scenario.agents[0].goal == 3


def test_missing_scenario_file_raises_file_not_found(topologies_dir, tmp_path):
    missing = tmp_path / "does_not_exist.json"

    with pytest.raises(FileNotFoundError):
        JSONScenarioLoader(missing, topologies_dir).load()


def test_missing_topology_file_raises_file_not_found(tmp_path):
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps({
        "id": "s1",
        "description": "",
        "topology_id": "missing_topology",
        "agents": [],
    }))
    empty_topologies_dir = tmp_path / "topologies"
    empty_topologies_dir.mkdir()

    with pytest.raises(FileNotFoundError):
        JSONScenarioLoader(scenario_path, empty_topologies_dir).load()


def test_malformed_json_raises_value_error(topologies_dir, tmp_path):
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text("{not valid json")

    with pytest.raises(ValueError):
        JSONScenarioLoader(scenario_path, topologies_dir).load()


def test_missing_required_key_raises_value_error(topologies_dir, tmp_path):
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps({"id": "s1", "description": ""}))

    with pytest.raises(ValueError):
        JSONScenarioLoader(scenario_path, topologies_dir).load()


def test_edge_referencing_unknown_node_raises_value_error(tmp_path):
    (tmp_path / "bad_topology.json").write_text(json.dumps({
        "id": "bad_topology",
        "description": "",
        "nodes": [{"id": 1, "x": 0.0, "y": 0.0}],
        "edges": [{"from": 1, "to": 99, "weight": 1.0}],
    }))
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps({
        "id": "s1",
        "description": "",
        "topology_id": "bad_topology",
        "agents": [],
    }))

    with pytest.raises(ValueError):
        JSONScenarioLoader(scenario_path, tmp_path).load()


def test_agent_referencing_unknown_node_raises_value_error(topologies_dir, tmp_path):
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps({
        "id": "s1",
        "description": "",
        "topology_id": "small_line_3",
        "agents": [{"id": 1, "start": 1, "goal": 99}],
    }))

    with pytest.raises(ValueError):
        JSONScenarioLoader(scenario_path, topologies_dir).load()
