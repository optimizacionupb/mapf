def test_data_loaders_package_exports_loaders():
    from data_loaders import JSONScenarioLoader, MovingAILoader, ScenarioLoader

    assert all([JSONScenarioLoader, MovingAILoader, ScenarioLoader])
