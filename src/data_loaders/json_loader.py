from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from data_loaders.base import ScenarioLoader
from domain.models import Agent, GraphTopology, Node, Scenario


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON in {path}: {exc}") from exc


def _require(data: dict[str, Any], key: str, path: Path) -> Any:
    if key not in data:
        raise ValueError(f"Missing required key '{key}' in {path}")
    return data[key]


def _build_topology(data: dict[str, Any], path: Path) -> GraphTopology:
    topology_id = _require(data, "id", path)
    description = _require(data, "description", path)
    nodes = {
        node["id"]: Node(id=node["id"], x=node["x"], y=node["y"])
        for node in _require(data, "nodes", path)
    }
    adjacency: dict[int, list[tuple[int, float]]] = {node_id: [] for node_id in nodes}
    for edge in _require(data, "edges", path):
        src, dst, weight = edge["from"], edge["to"], edge["weight"]
        if src not in nodes or dst not in nodes:
            raise ValueError(f"Edge references unknown node id in topology {topology_id} ({path})")
        adjacency[src].append((dst, weight))
    return GraphTopology(id=topology_id, description=description, nodes=nodes, adjacency=adjacency)


def _build_agents(data: dict[str, Any], topology: GraphTopology, path: Path) -> list[Agent]:
    agents = []
    for agent in _require(data, "agents", path):
        start, goal = agent["start"], agent["goal"]
        if start not in topology.nodes or goal not in topology.nodes:
            raise ValueError(
                f"Agent {agent['id']} start/goal node not found in topology {topology.id} ({path})"
            )
        agents.append(Agent(id=agent["id"], start=start, goal=goal))
    return agents


class JSONScenarioLoader(ScenarioLoader):
    """Adapter that builds a Scenario from a custom scenario+topology JSON schema."""

    def __init__(self, scenario_path: Path, topologies_dir: Path) -> None:
        self.scenario_path = Path(scenario_path)
        self.topologies_dir = Path(topologies_dir)

    def load(self) -> Scenario:
        """Read the scenario JSON and its referenced topology JSON into a Scenario."""
        scenario_data = _load_json(self.scenario_path)
        topology_id = _require(scenario_data, "topology_id", self.scenario_path)
        topology_path = self.topologies_dir / f"{topology_id}.json"
        topology_data = _load_json(topology_path)

        topology = _build_topology(topology_data, topology_path)
        agents = _build_agents(scenario_data, topology, self.scenario_path)

        return Scenario(
            id=_require(scenario_data, "id", self.scenario_path),
            topology=topology,
            agents=agents,
            description=_require(scenario_data, "description", self.scenario_path),
        )
