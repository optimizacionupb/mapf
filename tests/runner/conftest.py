import json
from pathlib import Path

import pytest

TOPOLOGY = {
    "id": "small_line_3",
    "description": "3-node line for runner tests",
    "nodes": [
        {"id": 1, "x": 0.0, "y": 0.0},
        {"id": 2, "x": 1.0, "y": 0.0},
        {"id": 3, "x": 2.0, "y": 0.0},
    ],
    "edges": [
        {"from": 1, "to": 2, "weight": 1.0},
        {"from": 2, "to": 1, "weight": 1.0},
        {"from": 2, "to": 3, "weight": 1.0},
        {"from": 3, "to": 2, "weight": 1.0},
    ],
}

SCENARIO = {
    "id": "small_line_3_one_agent",
    "description": "One agent crossing a 3-node line",
    "topology_id": "small_line_3",
    "agents": [{"id": 1, "start": 1, "goal": 3}],
}


@pytest.fixture
def topologies_dir(tmp_path: Path) -> Path:
    (tmp_path / "small_line_3.json").write_text(json.dumps(TOPOLOGY))
    return tmp_path


@pytest.fixture
def scenario_json_path(tmp_path: Path, topologies_dir: Path) -> Path:
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(SCENARIO))
    return path


TWO_NODE_TOPOLOGY = {
    "id": "two_node",
    "description": "2-node graph with no room to pass, for forcing no_solution",
    "nodes": [
        {"id": 1, "x": 0.0, "y": 0.0},
        {"id": 2, "x": 1.0, "y": 0.0},
    ],
    "edges": [
        {"from": 1, "to": 2, "weight": 1.0},
        {"from": 2, "to": 1, "weight": 1.0},
    ],
}

UNSOLVABLE_SWAP_SCENARIO = {
    "id": "two_node_swap",
    "description": "Two agents swapping positions on a 2-node graph: unsolvable",
    "topology_id": "two_node",
    "agents": [
        {"id": 1, "start": 1, "goal": 2},
        {"id": 2, "start": 2, "goal": 1},
    ],
}


@pytest.fixture
def unsolvable_topologies_dir(tmp_path: Path) -> Path:
    topologies_dir = tmp_path / "unsolvable_topologies"
    topologies_dir.mkdir()
    (topologies_dir / "two_node.json").write_text(json.dumps(TWO_NODE_TOPOLOGY))
    return topologies_dir


@pytest.fixture
def unsolvable_scenario_json_path(tmp_path: Path, unsolvable_topologies_dir: Path) -> Path:
    path = tmp_path / "unsolvable_scenario.json"
    path.write_text(json.dumps(UNSOLVABLE_SWAP_SCENARIO))
    return path


TINY_MAP = "type octile\nheight 3\nwidth 3\nmap\n...\n...\n...\n"
TINY_SCEN = "version 1\n0\ttiny.map\t3\t3\t0\t0\t2\t2\t2.0\n"


@pytest.fixture
def tiny_map_path(tmp_path: Path) -> Path:
    path = tmp_path / "tiny.map"
    path.write_text(TINY_MAP)
    return path


@pytest.fixture
def tiny_scen_path(tmp_path: Path, tiny_map_path: Path) -> Path:
    path = tmp_path / "tiny.scen"
    path.write_text(TINY_SCEN)
    return path
