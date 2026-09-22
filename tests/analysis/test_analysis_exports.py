def test_analysis_package_exports_public_functions():
    from analysis import analyze, animate_trajectories, compute_metrics, plot_trajectories

    assert analyze and compute_metrics and plot_trajectories and animate_trajectories
