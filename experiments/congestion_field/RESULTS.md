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
- Static gives similar gains. See analysis.md for static, ablA and ablB.
