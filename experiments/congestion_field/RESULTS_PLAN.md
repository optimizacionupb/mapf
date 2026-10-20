# Pre-registered analysis plan: predicted congestion field for MAPF

This file is written and committed BEFORE any tuning or test experiment is run. It is not edited
afterwards. Before writing it, the only runs were build smoke tests and single-instance sanity checks on
tuning scenario 1. Any later deviation will be reported in RESULTS.md as a deviation, and this
file will stay unchanged.

## Hypothesis under test

Adding a time-indexed congestion forecast to a MAPF planner as a tie-breaker lowers sum of costs.
The forecast has two parts: committed paths inside a window, and a discounted, smoothed
shortest-path occupancy prediction beyond it. The test is relative to (a) the unmodified planner and
(b) a static congestion heat map used at the same place in the code.

## Success test (verbatim from the brief)

Primary metric: sum of costs on instances solved by both methods, plus success rate within the time limit, at 60 seconds per instance.
Success: new method is at least 5 percent better than the baseline on the held-out set, on at least two different maps, at at least three agent counts, with a paired bootstrap 95 percent confidence interval that excludes zero.
Failure: anything less. If the improvement exists only on the tuning set, report that as overfitting.

## Operational definitions

- **SoC**: classical sum of costs. For each agent, this is the last timestep at which it is not yet resting at its goal, summed over agents. It is recomputed by our own validator (`scripts/common.py: validate`) from the solution file. Any solution the validator rejects counts as a failure.
- **Relative improvement** of the new method on instance x: `r(x) = (SoC_base(x) - SoC_new(x)) / SoC_base(x)`. It is computed only on instances that both methods solved.
- **Cell**: one (solver arm, map, agent count) combination. It contains 20 held-out instances.
- **A cell passes** only if all three of these hold:
  1. The mean of r over the cell is >= 0.05.
  2. The paired bootstrap 95% percentile CI of that mean (10,000 resamples of instances, numpy seed 0) has a lower bound > 0.
  3. The new method's success rate in the cell is >= the baseline's success rate.
- **The hypothesis is supported for a solver arm** only if at least 2 different maps each have at least 3 passing cells. The primary arm is LaCAM3, and the PIBT and EECBS arms are secondary. The overall verdict is "supported" only if the primary arm is supported. If only a secondary arm is supported, the verdict is "inconclusive". If no arm is supported, the verdict is "not supported".
- **The "new method" is the full forecast field.** The same test is also applied to the static control, so we can see whether any gain comes from congestion-awareness alone. If the static control passes as well as or better than the forecast, any gain is credited to congestion-awareness, not to prediction.
- **Overfitting:** the same table is computed on the tuning set. If a cell passes on tuning but not on held-out, it is reported as overfitting.
- **Headroom (stated in advance):** SoC can never fall below the sum of individual shortest-path distances (LB). In each cell we report the maximum achievable improvement `(SoC_base - LB) / SoC_base`. In the sanity runs, this headroom was below 5% for LaCAM3 on Berlin_1_256 (about 0.8% at 1000 agents) and for EECBS (about 2% at 200 agents on warehouse). So those cells are expected to fail the 5% criterion by construction. We keep them anyway, because the criterion is fixed.

## Maps, scenarios, split, seeds

- **Maps:** these are the MovingAI files already committed in `data/benchmarks/`. movingai.com is unreachable from this environment, and the user chose to use the maps in the repo only.
  - `warehouse-10-20-10-2-1` uses "even" scenarios. Their files have only 450 agents.
  - `maze-128-128-10` uses "random" scenarios.
  - `Berlin_1_256` uses "random" scenarios.
  - Deviation from the brief: random-32-32-20 and a room or den map are not available.
- **Split:** scenario index 1-5 is the tuning set; scenario index 6-25 is the held-out test set.
- **Seeds:** for LaCAM3 and PIBT, seed = scenario index, identical for every method on that instance. EECBS has no seed option: it calls `srand(0)` internally and is deterministic, which is the same for all arms.
- **Agent counts**, fixed now. These were chosen from the baseline sanity runs only:
  - LaCAM3: warehouse {100,200,300,400,450}, maze {100,200,300,400,500}, Berlin {200,400,600,800,1000}.
  - PIBT (pibt2): warehouse {25,50,75,100,125}, maze {100,200,300,400,500}, Berlin {200,400,600,800,1000}. Plain PIBT livelocks on warehouse at 100 or more agents in sanity runs, hence the smaller warehouse counts.
  - EECBS (w = 1.2): warehouse {50,100,150,200,250}, maze {50,100,150,200,250}, Berlin {100,200,300,400,500}.

## Compute

- **Time limit:** 60 s per instance (lacam3 `-t 60`, pibt2 `max_comp_time=60000`, EECBS `-t 60`). A run is also killed at 90 s of wall time and counted as a failure.
- **Hardware and parallelism:** the same 4-core container is used for all runs. Each run is pinned with `taskset` to a single core, and 4 runs execute in parallel. Jobs are ordered instance by instance with all methods of an instance adjacent, so machine-load drift is shared.
- **LaCAM3 config:** the default configuration as published, including SUO "scatter", Monte-Carlo PIBT (10), refiners and recursive LaCAM. Its threads time-share the single pinned core. (`--no-multi-thread` would silently disable the refiners, so it is not used.) Because of thread timing, LaCAM3's anytime result is not bit-reproducible: two identical runs differed by 0.7% SoC in sanity checks. To measure this noise floor, a second baseline replicate `base2` is run on the test set, and the base vs base2 comparison is reported with the same statistics.
- **Field cost:** the field's wall-clock time (setup, forecast and scoring) is measured inside the solver and reported. It consumes the same 60 s budget, so it is automatically counted against the new method.

## Methods (per arm)

| name | description |
|---|---|
| base | unmodified binary built from `third_party/` (pinned commits) |
| base2 | LaCAM3 only: a second run of base, used as the noise floor |
| static | heat map H(v) = average per-timestep occupancy of v in base solutions of the TUNING instances of the same arm, map and agent count, used in the same tie-breaker slot as the forecast |
| forecast | full time-indexed field (committed window + prediction beyond it) |
| ablA | forecast with no prediction beyond the window (`--field-no-beyond`) |
| ablB | forecast with gamma = 0 (future ignored) |

Where the field is used:
- **PIBT and LaCAM3:** it breaks ties among equal-distance candidates in PIBT. In these arms the only committed information is the next step already claimed by higher-priority agents, so the window is W = 1. With W = 1, ablA and ablB are identical by construction: both keep only the k = 1 committed term. ablB is therefore run only on 1 tuning instance per map, to confirm the outputs equal ablA, and is reported as "= ablA".
- **EECBS:** it is an extra key in the low-level FOCAL ordering. Committed paths are the other agents' current CT-node paths for t <= W. Beyond W, the other agents' paths are spatially smoothed, and agents without a path yet (during root generation) use the greedy shortest-path forecast. In this arm, ablA and ablB differ whenever W > 1.

## Tuning protocol (tuning scenarios 1-5 only)

- **PIBT arm:** full grid for forecast and static, each with gamma in {0.5, 0.8, 0.95} x horizon in {5, 10, 20} x cap in {2, 4}. Fixed values: smooth = 0.5 and W = 1.
- **LaCAM3 arm:** the top 3 forecast configs and top 3 static configs from the PIBT tuning are re-evaluated on the LaCAM3 tuning instances, and the best one is chosen per method.
- **EECBS arm:**
  - forecast: key position in {after #conflicts, after f} x gamma in {0.9, 1.0} x horizon in {32, 128} x W in {1, 8}, with cap = 2 and smooth = 0.5.
  - static: key position in {after #conflicts, after f} x gamma in {0.9, 1.0} x horizon in {32, 128}, with cap = 2.
- **Selection score:** the mean of r over all tuning instances of the arm (all maps and agent counts pooled) that both methods solved. A config is eligible only if its total number of solved tuning instances is >= the baseline's. Ties are broken by the smaller horizon. Ablations use the selected forecast config, changing only the ablated parameter.
- The selected configs are written to `tuned_params.json` and committed before any held-out run.

## Reporting

For every arm and method, and for each map x agent count, we report:
- success rates
- mean SoC
- mean r with its bootstrap CI
- the pass/fail of the cell
- win/tie/loss counts against base (a tie means equal SoC; an instance solved by only one method counts as a win for the solver that solved it)
- field time as a share of wall-clock time
- headroom

Negative and null results are reported with the same prominence as positive ones. No instance is dropped and no metric is changed.
