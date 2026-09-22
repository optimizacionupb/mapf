from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models import Scenario


class ScenarioLoader(ABC):
    """Adapter interface: turns some external scenario format into a domain Scenario."""

    @abstractmethod
    def load(self) -> Scenario:
        """Parse the configured source and return a fully-built Scenario."""
