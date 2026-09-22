import dataclasses
import json

from analysis.analyze import analyze


def test_analyze_loads_result_json_and_returns_metrics(result, tmp_path):
    result_path = tmp_path / "result_001.json"
    result_path.write_text(json.dumps(dataclasses.asdict(result)))

    metrics = analyze(result_path)

    assert metrics["makespan"] == 3
    assert metrics["sum_of_costs"] == 5.0
    assert metrics["success"] is True
    assert metrics["moves"] == 4
    assert metrics["waits"] == 1


def test_analyze_accepts_a_string_path(result, tmp_path):
    result_path = tmp_path / "result_001.json"
    result_path.write_text(json.dumps(dataclasses.asdict(result)))

    metrics = analyze(str(result_path))

    assert metrics["success"] is True
