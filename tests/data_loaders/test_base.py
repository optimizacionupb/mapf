import pytest

from data_loaders.base import ScenarioLoader
from domain.models import Agent, GraphTopology, Scenario


def test_scenario_loader_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        ScenarioLoader()


def test_concrete_loader_satisfies_the_contract():
    class DummyLoader(ScenarioLoader):
        def load(self) -> Scenario:
            return Scenario(
                id="s1",
                topology=GraphTopology(id="t1", description="", nodes={}, adjacency={}),
                agents=[Agent(id=1, start=1, goal=1)],
                description="",
            )

    loader = DummyLoader()

    assert isinstance(loader, ScenarioLoader)
    assert loader.load().id == "s1"
