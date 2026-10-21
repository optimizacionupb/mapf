"""Select field parameters on the TUNING set only (pre-registered protocol, see RESULTS_PLAN.md).
stage1: PIBT and EECBS grids -> best per method; top-3 PIBT configs -> LaCAM3 candidates.
stage2: best LaCAM3 candidate per method.  Writes tuned_params.json."""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import RUNS, ROOT, cfg_id, pibt_grid, eecbs_grid  # noqa: E402

OUT = os.path.join(ROOT, "tuned_params.json")


def load(*names):
    rows = []
    for n in names:
        with open(os.path.join(RUNS, n)) as f:
            rows += list(csv.DictReader(f))
    return rows


def ranking(rows, method, grid):
    inst = lambda r: (r["map"], r["scen"], r["N"])  # noqa: E731
    # only instances that are part of the design (e.g. ignore the unused warehouse/450 base rows)
    design = {inst(r) for r in rows if r["method"] != "base"}
    base = {inst(r): r for r in rows if r["method"] == "base" and inst(r) in design}
    base_solved = sum(1 for r in base.values() if r["valid"] == "1")
    res = []
    for p in grid:
        c = cfg_id(p)
        mine = [r for r in rows if r["method"] == method and r["cfg"] == c]
        solved = sum(1 for r in mine if r["valid"] == "1")
        rs = []
        for r in mine:
            b = base.get(inst(r))
            if b and b["valid"] == "1" and r["valid"] == "1":
                rs.append((int(b["soc"]) - int(r["soc"])) / int(b["soc"]))
        mean = sum(rs) / len(rs) if rs else float("-inf")
        res.append(dict(params=p, cfg=c, solved=solved, base_solved=base_solved, n_both=len(rs),
                        mean_r=mean, eligible=solved >= base_solved, runs=len(mine)))
    res.sort(key=lambda d: (not d["eligible"], -d["mean_r"], d["params"]["horizon"]))
    return res


def main(stage):
    tp = json.load(open(OUT)) if os.path.exists(OUT) else {}
    rank = tp.setdefault("tuning_ranking", {})
    if stage == "stage1":
        pibt = load("pibt_tune_base.csv", "pibt_tune_pibt.csv")
        eec = load("eecbs_tune_base.csv", "eecbs_tune_eecbs.csv")
        for arm, rows, gf, gs in (("pibt", pibt, pibt_grid(), pibt_grid()),
                                  ("eecbs", eec, eecbs_grid(False), eecbs_grid(True))):
            tp[arm] = {}
            for meth, grid in (("forecast", gf), ("static", gs)):
                r = ranking(rows, meth, grid)
                rank[f"{arm}_{meth}"] = r
                tp[arm][meth] = r[0]["params"]
        tp["lacam3_candidates"] = {m: [d["params"] for d in rank[f"pibt_{m}"][:3]] for m in ("forecast", "static")}
    else:
        rows = load("lacam3_tune_base.csv", "lacam3_tune_lacam3.csv")
        tp["lacam3"] = {}
        for meth in ("forecast", "static"):
            r = ranking(rows, meth, tp["lacam3_candidates"][meth])
            rank[f"lacam3_{meth}"] = r
            tp["lacam3"][meth] = r[0]["params"]
    json.dump(tp, open(OUT, "w"), indent=1)
    for k, v in rank.items():
        print(k)
        for d in v[:5]:
            print(f"   {d['cfg']:28s} mean_r={d['mean_r']:+.4f} solved={d['solved']}/{d['base_solved']} "
                  f"n_both={d['n_both']} eligible={d['eligible']}")


if __name__ == "__main__":
    main(sys.argv[1])
