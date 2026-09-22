from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Node:
    """A single vertex of a MAPF graph topology."""

    id: int
    x: float
    y: float


@dataclass
class GraphTopology:
    """A graph over which agents move: nodes plus a directed weighted adjacency map."""

    id: str
    description: str
    nodes: dict[int, Node]
    adjacency: dict[int, list[tuple[int, float]]]


@dataclass
class Agent:
    """A single MAPF agent identified by its start and goal node ids."""

    id: int
    start: int
    goal: int


@dataclass
class Scenario:
    """A complete MAPF problem instance: a topology plus the agents to route on it."""

    id: str
    topology: GraphTopology
    agents: list[Agent]
    description: str


@dataclass
class TrajectoryPoint:
    """One (node, time) sample of an agent's path."""

    node: int
    time: int


@dataclass
class AgentPath:
    """The full timed trajectory found for a single agent."""

    agent: int
    trajectory: list[TrajectoryPoint]


@dataclass
class ExecutionResult:
    """The outcome of running one solver on one scenario."""

    id: str
    scenario_id: str
    algorithm: str
    status: str
    paths: list[AgentPath]
    seed: int | None
    runtime_ms: float
    makespan: int
    sum_of_costs: float
