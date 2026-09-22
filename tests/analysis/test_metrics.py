from analysis.metrics import compute_metrics


def test_passes_through_stored_aggregate_metrics(result):
    metrics = compute_metrics(result)

    assert metrics["makespan"] == 3
    assert metrics["sum_of_costs"] == 5.0
    assert metrics["runtime_ms"] == 12.5
    assert metrics["success"] is True


def test_computes_average_cost_per_agent(result):
    metrics = compute_metrics(result)

    assert metrics["avg_cost"] == 2.5


def test_counts_moves_and_waits_across_all_agents(result):
    metrics = compute_metrics(result)

    assert metrics["moves"] == 4
    assert metrics["waits"] == 1


def test_failed_result_reports_success_false():
    from domain.models import ExecutionResult

    failed = ExecutionResult(
        id="r1",
        scenario_id="s1",
        algorithm="cbs",
        status="no_solution",
        paths=[],
        seed=None,
        runtime_ms=1.0,
        makespan=0,
        sum_of_costs=0.0,
    )

    metrics = compute_metrics(failed)

    assert metrics["success"] is False
    assert metrics["avg_cost"] == 0.0
    assert metrics["moves"] == 0
    assert metrics["waits"] == 0
