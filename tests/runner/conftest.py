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
