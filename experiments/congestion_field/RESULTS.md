# Results log: predicted congestion field

Stage summaries are appended as each stage finishes. The final verdict is at the end. The
pre-registered plan is in `RESULTS_PLAN.md` (committed in 678eb22, before any experiment, and never edited).

## Deviations from RESULTS_PLAN.md (all decided before seeing any held-out result)

1. **LaCAM3 warehouse top count is 420, not 450.** Of the 25 warehouse "even" scenario files, 11 have fewer than 450 agents (sizes range 420-470). Only scenario 1 was checked when the plan was written. 420 is the smallest file size, so it runs on every instance. The change follows from file sizes alone.
2. **3 solver runs in parallel, not 4.** Each solver is pinned to one of cores 1-3, and core 0 runs the Python harness (validation, bookkeeping). This keeps validation from stealing CPU from the solvers. It applies identically to every method.
3. **Static heat fallback.** Base PIBT solved no tuning instance at warehouse/125, so there is no solution to build a heat map from. Fixed rule: use the heat of the largest smaller agent count with a solution (here warehouse/100, built from 1 solution). Only this one cell is affected.
4. **Tuning baseline rows** for LaCAM3 warehouse/450 exist in `runs/lacam3_tune_base.csv`, from scenarios 1-2 before the crash that revealed deviation 1. They are not used anywhere.

## Stage 0: baselines (done)

- **Builds:** LaCAM3 (Kei18/lacam3 @ 1c3ecf8), PIBT (Kei18/pibt2 @ faab5b9) and EECBS (Jiaoyang-Li/EECBS @ 06ec705) are built from pristine clones; see SOURCES.md.
- **Validator agreement:** every solution is checked by our own validator in `scripts/common.py`. Its SoC equals lacam3's own reported SoC on the sanity runs.
- **Sanity numbers** on tuning scenario 1, 60 s:

  | solver | map / agents | SoC | LB (sum of distances) | gap above LB |
  |---|---|---|---|---|
  | LaCAM3 | warehouse / 450 | 47429 | 42901 | 10.5% |
  | LaCAM3 | Berlin / 1000 | 179968 | 178564 | 0.8% |
  | EECBS w=1.2 | warehouse / 200 | 20052 | 19713 | 1.7% (0.8 s runtime) |

  Plain PIBT livelocks on warehouse at 150 or more agents and solves maze and Berlin at 4-30% above LB. These match the qualitative picture in the LaCAM3 (AAMAS-24), pibt2 (AIJ-22) and EECBS (AAAI-21) papers: LaCAM3 near-optimal and complete at scale, PIBT fast but incomplete, EECBS near-optimal at moderate counts.
- **Noise:** LaCAM3's anytime result is not bit-reproducible, because its refiner threads time-share one core. Two identical runs gave 47429 and 47778 (0.7% apart). The initial solution is deterministic.
- **Baseline mean gap above LB on the tuning set** (scenarios 1-5):
  - LaCAM3: warehouse 0.7% → 8.3% and maze 1.4% → 8.5% as N grows, Berlin at most 0.8%.
  - PIBT: 4.7% → 22%. Warehouse success drops to 2/5 at 75 agents, 1/5 at 100 and 0/5 at 125.
  - EECBS: 0.1% → 3.5%.
- **Consequence:** the 5% criterion is unreachable by any method on every EECBS cell, on every Berlin LaCAM3 cell, and on the low-N LaCAM3 cells, because SoC cannot go below LB.

## Stages 1-2: static control and forecast field (done)

- The static heat map and the time-indexed forecast are implemented in all three solvers, in `variants/`, with the shared code in `variants/common/congestion_field.hpp`.
- With the field off, each variant reproduces its baseline exactly (same SoC and same initial solution).
- Guarantees preserved, as explained in code comments:
  - **LaCAM3:** the field only reorders equal-distance PIBT candidates, so completeness and eventual optimality hold.
  - **PIBT:** the highest-priority agent still moves on a shortest path, so the reachability guarantee holds.
  - **EECBS:** the field only reorders FOCAL, never its membership, so w-suboptimality holds.
- Committed-path window:
  - In LaCAM3 and PIBT the only committed future is the next step already claimed in the current PIBT call, so W = 1.
  - In EECBS the committed paths are the CT-node paths, so W is tunable.

## Stage 3: tuning (scenarios 1-5 only)

Stage 1 selection is in `tuned_params.json` and committed. The selection score is the mean relative SoC improvement over all tuning instances solved by both, pooled over maps and agent counts.

| arm | method | selected config | tuning mean improvement | solved (new / base) |
|---|---|---|---|---|
| PIBT | forecast | gamma 0.5, H 5, cap 2 | +1.41% | 66 / 63 |
| PIBT | static | gamma 0.5, H 5, cap 2 | +2.15% | 63 / 63 |
| EECBS | forecast | key after f, gamma 1.0, H 128, W 1 | +0.23% | 75 / 75 |
| EECBS | static | key after f, gamma 1.0, H 128 | +0.24% | 75 / 75 |

- Even on the tuning data, the static heat map is at least as good as the forecast in both arms.
- In EECBS, putting the field key before f (right after the conflict count) always hurt: static was as low as -13.7%, and forecast ranged from -0.2% to -1.9%.
- LaCAM3 tuning (top 3 PIBT configs per method, re-evaluated on LaCAM3) is running.

### LaCAM3 tuning (stage 2: top 3 PIBT configs per method re-evaluated on LaCAM3 tuning instances)

| method | config | tuning mean improvement | solved (new / base) |
|---|---|---|---|
| forecast | gamma 0.8, H 5, cap 4 (selected) | -0.39% | 75 / 75 |
| forecast | gamma 0.5, H 5, cap 4 | -0.45% | 75 / 75 |
| forecast | gamma 0.5, H 5, cap 2 | -0.53% | 75 / 75 |
| static | gamma 0.5, H 5, cap 2 (selected) | -0.42% | 70 / 75 |
| static | gamma 0.5, H 5, cap 4 | -0.48% | 70 / 75 |
| static | gamma 0.5, H 10, cap 2 | -0.49% | 70 / 75 |

- **Forecast** made LaCAM3 slightly worse on every candidate, even on the tuning data.
- **Static** made LaCAM3 fail to find any solution within 60 s on 5 of the 75 tuning instances: warehouse scenario 1 at 300 and 420 agents, and scenario 3 at 300, 400 and 420 agents. The baseline solves each of these in about 1 s.
- **Deviation 5:** no static config met the eligibility rule (solve at least as many as base). The plan does not cover this case, so the best-ranked config under the same ordering was taken.
- **Deviation 6:** `select_params.py` first counted the 3 unused warehouse/450 base rows (deviation 4) in the base solved count. This was fixed before selection was finalised. It changed eligibility flags only, not the PIBT or EECBS choices.

## Stage 4 (partial): held-out results for the PIBT and EECBS arms

Full tables are in `analysis.md`, generated by `scripts/analyze.py`. A cell passes only if mean improvement >= 5%, the 95% CI excludes zero, and success rate is no lower than base.

**PIBT, forecast vs base: 0 of 15 cells pass.**
- The forecast helps a little and consistently on maze (+1.6% to +2.4%, CIs above zero) and Berlin (+0.5% to +0.9%).
- Warehouse shows +0.8% to +5.3%. The single cell above 5% (warehouse/75, +5.32% [4.12, 6.46]) fails the success-rate condition: 12/20 solved vs 13/20 for base.
- Field computation takes 24-65% of PIBT's wall-clock time.

**PIBT, static vs base: 0 of 15 cells pass, and static is clearly harmful on held-out data.**
- Success collapses as N grows, from 20/20 to 0/20 on maze/500 and Berlin/1000. Every failure is a livelock: the run hits the 20,000-timestep cap.
- On the tuning set, the same static config solved everything and gained up to +4.9%. That gain was in-sample, because the heat map is built from the tuning instances' own base solutions. It does not transfer to new instances. This is overfitting of the static control, and it is a flaw in the tuning protocol for the static method.
- A plausible mechanism, not tested: a fixed, time-invariant tie-breaker removes PIBT's random tie-breaking and lets agents cycle. The time-varying forecast does not show this.

**PIBT, ablA (no forecast beyond the window) vs base:** identical SoC on every instance (all ties). In PIBT the only committed information is the already-claimed next step, and those candidates are skipped anyway, so this result follows from the code. The PIBT forecast's gain therefore comes entirely from the prediction beyond the window. ablB was confirmed identical to ablA on 3 instances (`runs/pibt_check_ablB.csv`).

**EECBS, forecast vs base: 0 of 15 cells pass.**
- Gains are tiny but consistent: +0.02% to +0.66%, CIs above zero, success unchanged.
- The ceiling is the binding constraint: base EECBS is only 0.1% to 3.3% above the lower bound, so 5% is impossible in every EECBS cell.
- **The static control matches the forecast cell for cell** (static +0.01% to +0.69%, forecast +0.02% to +0.66%).
- **ablA and ablB are essentially zero** (-0.01% to +0.02%, mostly ties). They are identical to each other, because the tuned window is W = 1.
- So in EECBS the small gain needs the beyond-window term, but a static heat map buys the same gain. The time-indexed prediction adds nothing over plain congestion-awareness.

**LaCAM3 ablB = ablA check** (`runs/lacam3_check_ablB.csv`, tuning scenario 1, three instances): the initial solutions have identical cost in each pair (32092, 60447 and 106608). The final anytime SoC differs by 0.0-0.4%, within the run-to-run timing noise measured in Stage 0 (0.7%).

## Stage 4 (final): LaCAM3 held-out results and verdict

**Pre-registered verdict: NOT SUPPORTED.**
- The full forecast field passes 0 of 45 cells across the three arms. A pass needs mean improvement >= 5%, a 95% CI above zero, and success rate no lower than base.
- The static control also passes 0 of 45, as do both ablations.
- The tuning set shows no pass either. So this is not a case of a gain that exists only on tuning data. There is no gain of the required size anywhere.

**LaCAM3, the primary arm.**
- The forecast is slightly worse than unmodified LaCAM3 in most cells: -1.06% to +0.14%. The CI lies entirely below zero in 6 of 15 cells and entirely above zero in none.
- Win/tie/loss over the 300 held-out instances is 87/29/184.
- Success is unchanged at 100%.
- The base vs base2 replicate gives -0.20% to +0.16%. That is the noise floor from thread timing, and the forecast's losses on maze/400 and warehouse/420 (about -1%) are clearly outside it.
- Likely cause: field computation takes 20-73% of the solver's thread time. That is time LaCAM3's anytime search and refiners do not get, and at its default settings LaCAM3 is already within 0.2-8.5% of the lower bound.

**LaCAM3, static control.** It is worse still. Success drops to 9/20 on warehouse/420 and 12/20 on warehouse/400, and SoC worsens by up to -1.6%.

**LaCAM3, ablA.** It is within noise of base (-0.36% to +0.15%). Its overhead is smaller (7-15%) because it computes no forecast.

**Does prediction add anything beyond existing congestion-awareness?**
- **PIBT:** the time-indexed forecast gives small, consistent gains (+0.5% to +5.3%), but never 5% with success held. All of the gain comes from the beyond-window prediction, since ablA is identical to base there. The static heat map, by contrast, livelocks PIBT on held-out instances.
- **EECBS:** the forecast and the static map give the same tiny gains (at most +0.7%), so prediction adds nothing over plain congestion-awareness.
- **LaCAM3:** neither helps. LaCAM3 already includes SUO "scatter", a congestion-aware path-spreading method that is on by default. Its anytime refinement absorbs whatever ordering signal the field provides, and the field's cost then shows up as a small loss.

### Main table: held-out scenarios 6-25 (20 instances per row)

- r is the relative SoC improvement of the forecast over base, on instances both solved; positive means better.
- Headroom is the most any method could gain, (SoC_base - LB) / SoC_base.
- Full tables, including ablations, base2 and the tuning-set check, are in analysis.md.

| arm | map | N | headroom | forecast: mean r [95% CI] | forecast W/T/L | static: mean r | success base / forecast / static |
|---|---|---|---|---|---|---|---|
| lacam3 | warehouse | 100 | 0.5% | -0.02% [-0.06, -0.00] | 1/15/4 | -0.00% | 20 / 20 / 20 |
| lacam3 | warehouse | 200 | 2.5% | +0.14% [-0.03, +0.31] | 12/0/8 | -0.03% | 20 / 20 / 20 |
| lacam3 | warehouse | 300 | 4.7% | -0.20% [-0.40, -0.00] | 6/0/14 | -0.17% | 20 / 20 / 19 |
| lacam3 | warehouse | 400 | 7.8% | -0.26% [-0.63, +0.07] | 9/0/11 | -0.37% | 20 / 20 / 12 |
| lacam3 | warehouse | 420 | 8.3% | -0.88% [-1.21, -0.57] | 1/0/19 | -1.57% | 20 / 20 / 9 |
| lacam3 | maze | 100 | 1.3% | +0.05% [-0.17, +0.33] | 5/5/10 | -0.00% | 20 / 20 / 20 |
| lacam3 | maze | 200 | 2.4% | -0.84% [-1.23, -0.48] | 2/0/18 | -1.00% | 20 / 20 / 20 |
| lacam3 | maze | 300 | 4.8% | -0.04% [-0.29, +0.20] | 8/0/12 | -0.18% | 20 / 20 / 20 |
| lacam3 | maze | 400 | 7.0% | -1.06% [-1.44, -0.70] | 2/0/18 | -1.03% | 20 / 20 / 20 |
| lacam3 | maze | 500 | 8.5% | -0.81% [-1.30, -0.34] | 6/0/14 | -1.61% | 20 / 20 / 20 |
| lacam3 | berlin | 200 | 0.2% | +0.01% [-0.02, +0.03] | 6/8/6 | +0.01% | 20 / 20 / 20 |
| lacam3 | berlin | 400 | 0.3% | -0.00% [-0.06, +0.07] | 5/0/15 | -0.04% | 20 / 20 / 20 |
| lacam3 | berlin | 600 | 0.4% | -0.08% [-0.16, -0.01] | 5/0/15 | -0.01% | 20 / 20 / 20 |
| lacam3 | berlin | 800 | 0.6% | -0.02% [-0.09, +0.06] | 9/1/10 | -0.05% | 20 / 20 / 20 |
| lacam3 | berlin | 1000 | 1.0% | -0.09% [-0.33, +0.13] | 10/0/10 | -0.13% | 20 / 20 / 20 |
| pibt | warehouse | 25 | 7.1% | +0.84% [-1.10, +2.57] | 10/0/8 | -2.10% | 18 / 17 / 18 |
| pibt | warehouse | 50 | 14.2% | +2.90% [+0.90, +4.97] | 13/0/3 | +0.30% | 15 / 16 / 14 |
| pibt | warehouse | 75 | 17.9% | +5.32% [+4.12, +6.46] | 12/0/2 | +2.26% | 13 / 12 / 7 |
| pibt | warehouse | 100 | 22.1% | +3.66% [+2.40, +5.06] | 8/0/2 | -0.07% | 8 / 8 / 6 |
| pibt | warehouse | 125 | 26.5% | +3.45% [+2.07, +4.83] | 2/0/1 | +0.29% | 3 / 2 / 3 |
| pibt | maze | 100 | 8.4% | +1.63% [+1.18, +2.15] | 19/0/1 | -0.45% | 20 / 20 / 17 |
| pibt | maze | 200 | 12.9% | +1.57% [+1.01, +2.06] | 19/0/1 | -1.16% | 20 / 20 / 10 |
| pibt | maze | 300 | 15.7% | +1.64% [+1.18, +2.11] | 20/0/0 | +0.40% | 20 / 20 / 7 |
| pibt | maze | 400 | 18.8% | +2.00% [+1.60, +2.39] | 20/0/0 | +0.93% | 20 / 20 / 5 |
| pibt | maze | 500 | 21.6% | +2.44% [+2.12, +2.74] | 20/0/0 | n/a | 20 / 20 / 0 |
| pibt | berlin | 200 | 4.1% | +0.45% [+0.17, +0.73] | 17/0/3 | -2.17% | 19 / 20 / 16 |
| pibt | berlin | 400 | 7.3% | +0.70% [+0.45, +0.96] | 18/0/1 | -2.00% | 19 / 19 / 11 |
| pibt | berlin | 600 | 9.4% | +0.70% [+0.52, +0.89] | 19/0/1 | -2.72% | 20 / 19 / 8 |
| pibt | berlin | 800 | 11.6% | +0.63% [+0.40, +0.87] | 18/0/2 | -2.17% | 20 / 20 / 1 |
| pibt | berlin | 1000 | 13.6% | +0.93% [+0.70, +1.16] | 19/0/1 | n/a | 20 / 20 / 0 |
| eecbs | warehouse | 50 | 0.3% | +0.11% [+0.05, +0.17] | 12/4/4 | +0.01% | 20 / 20 / 20 |
| eecbs | warehouse | 100 | 0.7% | +0.22% [+0.17, +0.27] | 19/0/1 | +0.09% | 20 / 20 / 20 |
| eecbs | warehouse | 150 | 1.3% | +0.31% [+0.21, +0.40] | 19/0/1 | +0.07% | 20 / 20 / 20 |
| eecbs | warehouse | 200 | 2.2% | +0.31% [+0.11, +0.53] | 16/0/4 | +0.27% | 20 / 20 / 20 |
| eecbs | warehouse | 250 | 3.3% | +0.59% [+0.34, +0.86] | 16/0/4 | +0.57% | 20 / 20 / 20 |
| eecbs | maze | 50 | 0.8% | +0.10% [+0.08, +0.13] | 19/1/0 | +0.12% | 20 / 20 / 20 |
| eecbs | maze | 100 | 1.4% | +0.23% [+0.20, +0.27] | 20/0/0 | +0.25% | 20 / 20 / 20 |
| eecbs | maze | 150 | 2.0% | +0.38% [+0.34, +0.44] | 20/0/0 | +0.40% | 20 / 20 / 20 |
| eecbs | maze | 200 | 2.6% | +0.53% [+0.47, +0.58] | 20/0/0 | +0.52% | 20 / 20 / 20 |
| eecbs | maze | 250 | 3.3% | +0.66% [+0.60, +0.72] | 20/0/0 | +0.69% | 20 / 20 / 20 |
| eecbs | berlin | 100 | 0.1% | +0.02% [+0.02, +0.03] | 19/0/0 | +0.02% | 19 / 19 / 19 |
| eecbs | berlin | 200 | 0.1% | +0.04% [+0.03, +0.04] | 19/0/0 | +0.03% | 19 / 19 / 19 |
| eecbs | berlin | 300 | 0.2% | +0.05% [+0.04, +0.06] | 18/0/1 | +0.06% | 19 / 19 / 19 |
| eecbs | berlin | 400 | 0.3% | +0.07% [+0.06, +0.08] | 19/0/0 | +0.07% | 19 / 19 / 19 |
| eecbs | berlin | 500 | 0.3% | +0.09% [+0.08, +0.10] | 19/0/0 | +0.09% | 19 / 19 / 19 |

Forecast vs base, total win/tie/loss over all held-out instances: lacam3 87/29/184, pibt 234/0/26, eecbs 275/5/15

### Runtime overhead of the field (share of wall-clock time, held-out)

| arm | forecast | static | ablA |
|---|---|---|---|
| LaCAM3 | 20-73% | 19-59% | 7-15% |
| PIBT | 24-65% | 24-70% | 14-44% |
| EECBS | 16-27% | 5-7% | see analysis.md |

- For LaCAM3, field time is summed over its threads, which time-share one core, so it is an upper bound.
- The time limit was the same for everyone, so this cost is already charged against the field methods.

### Limitations

1. **Maps.** Only 3 maps were used: warehouse-10-20-10-2-1, maze-128-128-10 and Berlin_1_256. random-32-32-20 and a room or den map were not available, because movingai.com was unreachable from this environment, and the user chose to use the maps already in the repository. Small, dense maps like random-32-32-20 are where congestion matters most, and they are untested here.
2. **Headroom.** Most cells had less than 5% headroom: every EECBS cell, every LaCAM3 Berlin cell, and the LaCAM3 low-N cells. The 5% bar could only be reached by LaCAM3 at high N on warehouse and maze, and by PIBT. Our finding is that a 5% gain is impossible or not reached, not that a smaller gain cannot exist. The forecast does give a small, statistically clear gain for PIBT and EECBS.
3. **One field design.** We tested one implementation of the idea: a greedy shortest-path forecast with spatial smoothing, used strictly as a tie-breaker. A soft cost term that can trade path length for congestion, a learned motion model, or a rolling-horizon planner (where "committed paths in the window" is a richer concept) might behave differently. Using the field only as a tie-breaker was chosen to preserve guarantees, and it caps the possible effect.
4. **Window.** In LaCAM3 and PIBT the only committed information is the next step, so the "committed window" part of the idea is nearly empty there. Only EECBS has real committed paths, and its tuning picked W = 1.
5. **Tuning budget.** LaCAM3 was tuned only over the top 3 PIBT configs per method, as pre-registered, to fit the compute budget.
6. **Static control flaw.** The static heat map was built from the tuning instances' own base solutions, so its tuning results were in-sample and optimistic. On held-out data it hurt PIBT and LaCAM3. A heat map built from separate instances might behave differently.
7. **Compute setup.** Single machine. Solvers ran on 3 cores in parallel, not the 4 in the plan. LaCAM3's anytime result has about 0.2-0.7% run-to-run noise from thread timing, measured with base2.
8. **Deviations.** Six deviations from the plan are listed at the top of this file. All were decided before any held-out result was seen.
