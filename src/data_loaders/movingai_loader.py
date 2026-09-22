from __future__ import annotations

from pathlib import Path

from data_loaders.base import ScenarioLoader
from domain.models import Agent, GraphTopology, Node, Scenario

PASSABLE_TERRAIN = {".", "G", "S"}
NEIGHBOR_OFFSETS = ((0, -1), (0, 1), (-1, 0), (1, 0))


def _parse_header_int(line: str, prefix: str, path: Path) -> int:
    parts = line.split()
    if len(parts) != 2 or parts[0] != prefix:
        raise ValueError(f"Malformed .map header in {path}: expected '{prefix} <n>', got '{line}'")
    try:
        return int(parts[1])
    except ValueError as exc:
        raise ValueError(f"Malformed .map header in {path}: expected integer for '{prefix}'") from exc


class MovingAILoader(ScenarioLoader):
    """Adapter that builds a Scenario from a Moving AI Lab .map/.scen file pair."""

    def __init__(self, map_path: Path, scen_path: Path, num_agents: int = 10) -> None:
        self.map_path = Path(map_path)
        self.scen_path = Path(scen_path)
        self.num_agents = num_agents

    def load(self) -> Scenario:
        """Parse the .map into a grid topology and the .scen into agents, returning a Scenario."""
        width, height, rows = self._read_map()
        nodes, adjacency = self._build_graph(width, height, rows)
        topology = GraphTopology(
            id=self.map_path.stem,
            description=f"Moving AI map {self.map_path.name} ({width}x{height})",
            nodes=nodes,
            adjacency=adjacency,
        )
        agents = self._read_agents(width, height, nodes)
        return Scenario(
            id=f"{self.map_path.stem}_{self.scen_path.stem}_{self.num_agents}",
            topology=topology,
            agents=agents,
            description=f"MovingAI scenario from {self.scen_path.name} with {self.num_agents} agents",
        )

    def _read_map(self) -> tuple[int, int, list[str]]:
        if not self.map_path.exists():
            raise FileNotFoundError(f"Map file not found: {self.map_path}")
        lines = self.map_path.read_text().splitlines()
        if len(lines) < 4:
            raise ValueError(f"Malformed .map header in {self.map_path}: too few lines")

        height = _parse_header_int(lines[1], "height", self.map_path)
        width = _parse_header_int(lines[2], "width", self.map_path)
        if lines[3].strip() != "map":
            raise ValueError(f"Malformed .map header in {self.map_path}: expected 'map' line")

        rows = lines[4 : 4 + height]
        if len(rows) != height:
            raise ValueError(f"Expected {height} grid rows in {self.map_path}, found {len(rows)}")
        for i, row in enumerate(rows):
            if len(row) != width:
                raise ValueError(f"Row {i} in {self.map_path} has length {len(row)}, expected width {width}")
        return width, height, rows

    def _build_graph(
        self, width: int, height: int, rows: list[str]
    ) -> tuple[dict[int, Node], dict[int, list[tuple[int, float]]]]:
        nodes: dict[int, Node] = {}
        for y in range(height):
            for x in range(width):
                if rows[y][x] in PASSABLE_TERRAIN:
                    node_id = y * width + x
                    nodes[node_id] = Node(id=node_id, x=float(x), y=float(y))

        adjacency: dict[int, list[tuple[int, float]]] = {node_id: [] for node_id in nodes}
        for y in range(height):
            for x in range(width):
                node_id = y * width + x
                if node_id not in nodes:
                    continue
                for dx, dy in NEIGHBOR_OFFSETS:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < width and 0 <= ny < height:
                        neighbor_id = ny * width + nx
                        if neighbor_id in nodes:
                            adjacency[node_id].append((neighbor_id, 1.0))
        return nodes, adjacency

    def _read_agents(self, width: int, height: int, nodes: dict[int, Node]) -> list[Agent]:
        if not self.scen_path.exists():
            raise FileNotFoundError(f"Scenario file not found: {self.scen_path}")
        lines = self.scen_path.read_text().splitlines()
        if not lines or not lines[0].startswith("version"):
            raise ValueError(f"Invalid .scen header in {self.scen_path}: expected 'version' line")

        entries = lines[1 : 1 + self.num_agents]
        if len(entries) < self.num_agents:
            raise ValueError(
                f"Requested {self.num_agents} agents but {self.scen_path} only contains {len(entries)} scen lines"
            )

        agents = []
        for i, line in enumerate(entries):
            fields = line.split("\t")
            if len(fields) != 9:
                raise ValueError(f"Malformed .scen line {i} in {self.scen_path}: expected 9 tab-separated fields")
            _, _, map_width, map_height, start_x, start_y, goal_x, goal_y, _ = fields
            if int(map_width) != width or int(map_height) != height:
                raise ValueError(
                    f"Scenario {self.scen_path} line {i}: map dimensions {map_width}x{map_height} "
                    f"do not match {self.map_path} dimensions {width}x{height}"
                )
            start = int(start_y) * width + int(start_x)
            goal = int(goal_y) * width + int(goal_x)
            if start not in nodes or goal not in nodes:
                raise ValueError(f"Agent start/goal at line {i} is not a passable cell in {self.map_path}")
            agents.append(Agent(id=i + 1, start=start, goal=goal))
        return agents
