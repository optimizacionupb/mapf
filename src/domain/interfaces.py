from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models import ExecutionResult, Scenario


class MAPFSolver(ABC):
    """Strategy interface every MAPF algorithm implementation must satisfy."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the algorithm's identifying name."""

    @abstractmethod
    def solve(self, scenario: Scenario, seed: int | None = None) -> ExecutionResult:
        """Compute an ExecutionResult for the given scenario."""
