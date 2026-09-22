def test_analysis_package_exports_public_functions():
    from analysis import analyze, compute_metrics, plot_trajectories

    assert analyze and compute_metrics and plot_trajectories
