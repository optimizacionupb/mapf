"""Resumable experiment runner.

Every job is one (arm, method, config, map, scenario, agent count).  Solvers run pinned with taskset to
cores 1..3 (one job per core); core 0 is left to this harness (validation, bookkeeping) so the solvers
never compete with Python for CPU.  Each solution is checked by the independent validator in
common.py and then deleted.  Results are appended to runs/<arm>_<phase>.csv; jobs already present are
skipped, so the runner can be restarted at any time.

Usage: python3 -I scripts/run.py <jobs-name>    (see JOBSETS at the bottom)
"""
import csv
import json
import os
import queue
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (ROOT, TUNE_SCENS, TEST_SCENS, map_path, scen_path, read_scen, read_map,  # noqa: E402
                    parse_config_solution, parse_kv, parse_eecbs_paths, paths_to_configs, validate,
                    soc_lower_bound)

TIME_LIMIT = 60
HARD_KILL = 90
SOLVER_CORES = [1, 2, 3]
RUNS = os.path.join(ROOT, "runs")
TMP = os.path.join(RUNS, "tmp")
HEAT_RAW = os.path.join(RUNS, "heat_raw")
HEAT = os.path.join(RUNS, "heat")

BIN = {
    ("lacam3", "base"): os.path.join(ROOT, "third_party/lacam3/build/main"),
    ("lacam3", "var"): os.path.join(ROOT, "variants/lacam3_field/build/main"),
    ("pibt", "base"): os.path.join(ROOT, "third_party/pibt2/build/mapf"),
    ("pibt", "var"): os.path.join(ROOT, "variants/pibt2_field/build/mapf"),
    ("eecbs", "base"): os.path.join(ROOT, "third_party/EECBS/build/eecbs"),
    ("eecbs", "var"): os.path.join(ROOT, "variants/eecbs_field/build/eecbs"),
}

AGENTS = {
    # lacam3 warehouse top count: 450 was pre-registered, but 11 of the 25 "even" scens have < 450 agents
    "lacam3": {"warehouse": [100, 200, 300, 400, 420], "maze": [100, 200, 300, 400, 500],
               "berlin": [200, 400, 600, 800, 1000]},
    "pibt": {"warehouse": [25, 50, 75, 100, 125], "maze": [100, 200, 300, 400, 500],
             "berlin": [200, 400, 600, 800, 1000]},
    "eecbs": {"warehouse": [50, 100, 150, 200, 250], "maze": [50, 100, 150, 200, 250],
              "berlin": [100, 200, 300, 400, 500]},
}

FIELDS = ["arm", "phase", "method", "cfg", "map", "scen", "N", "seed", "solved", "valid", "soc", "lb",
          "makespan", "wall_ms", "solver_ms", "field_ms", "init_cost", "msg"]


_LB_CACHE = {}
_LB_LOCK = threading.Lock()


def cached_lb(m, scen, n, agents):
    """SoC lower bound is a pure function of the instance; cache it (the grids repeat instances)."""
    k = (m, scen, n)
    with _LB_LOCK:
        if k not in _LB_CACHE:
            _LB_CACHE[k] = soc_lower_bound(map_path(m), agents)
        return _LB_CACHE[k]


def heat_file(arm, m, n):
    return os.path.join(HEAT, f"{arm}_{m}_{n}.txt")


def field_args(arm, method, params, m, n):
    """Translate (method, params) into solver flags.  params: dict gamma/horizon/cap/window/key."""
    if method in ("base", "base2"):
        return []
    mode = "static" if method == "static" else "forecast"
    p = dict(params)
    if method == "ablB":
        p["gamma"] = 0.0
    if arm == "eecbs":
        a = ["--fieldMode", mode, "--fieldKey", str(p.get("key", 1)), "--fieldGamma", str(p["gamma"]),
             "--fieldHorizon", str(p["horizon"]), "--fieldCap", str(p.get("cap", 2)),
             "--fieldWindow", str(p.get("window", 1))]
        if method == "ablA":
            a += ["--fieldNoBeyond", "1"]
        if mode == "static":
            a += ["--fieldHeat", heat_file(arm, m, n)]
        return a
    a = [f"--field-mode={mode}", f"--field-gamma={p['gamma']}", f"--field-horizon={p['horizon']}",
         f"--field-cap={p.get('cap', 2)}", "--field-window=1"]
    if method == "ablA":
        a.append("--field-no-beyond")
    if mode == "static":
        a.append(f"--field-heat={heat_file(arm, m, n)}")
    if arm == "lacam3":  # lacam3's argparse wants "--flag value"
        out = []
        for x in a:
            if "=" in x:
                k, v = x.split("=", 1)
                out += [k, v]
            else:
                out.append(x)
        a = out
    return a


def save_heat_raw(arm, m, n, scen, configs):
    w, h, _ = read_map(map_path(m))
    counts = {}
    for c in configs:
        for (x, y) in c:
            k = y * w + x
            counts[k] = counts.get(k, 0) + 1
    os.makedirs(HEAT_RAW, exist_ok=True)
    with open(os.path.join(HEAT_RAW, f"{arm}_{m}_{n}_s{scen}.json"), "w") as f:
        json.dump({"T": len(configs), "w": w, "h": h, "counts": counts}, f)


def run_job(job, core):
    arm, method, m, scen, n = job["arm"], job["method"], job["map"], job["scen"], job["N"]
    seed = scen
    tag = f"{arm}_{job['phase']}_{method}_{job['cfg']}_{m}_{scen}_{n}".replace(".", "p")
    os.makedirs(TMP, exist_ok=True)
    out = os.path.join(TMP, tag + ".out")
    binkey = (arm, "base" if method in ("base", "base2") else "var")
    fargs = field_args(arm, method, job["params"], m, n)
    agents = read_scen(scen_path(m, scen), n)
    files = [out]
    if arm == "lacam3":
        cmd = [BIN[binkey], "-m", map_path(m), "-i", scen_path(m, scen), "-N", str(n), "-t", str(TIME_LIMIT),
               "-s", str(seed), "-o", out] + fargs
    elif arm == "pibt":
        inst = os.path.join(TMP, tag + ".inst")
        rel = os.path.relpath(map_path(m), os.path.join(ROOT, "third_party/pibt2/map"))
        with open(inst, "w") as f:
            f.write(f"map_file={rel}\nagents={n}\nseed={seed}\nrandom_problem=0\nmax_timestep=20000\n"
                    f"max_comp_time={TIME_LIMIT * 1000}\n")
            f.writelines(f"{a},{b},{c},{d}\n" for a, b, c, d in agents)
        files.append(inst)
        cmd = [BIN[binkey], "-i", inst, "-s", "PIBT", "-o", out] + fargs
    else:
        paths = os.path.join(TMP, tag + ".paths")
        csvf = os.path.join(TMP, tag + ".csv")
        files += [paths, csvf]
        cmd = [BIN[binkey], "-m", map_path(m), "-a", scen_path(m, scen), "-k", str(n), "-t", str(TIME_LIMIT),
               "-o", csvf, f"--outputPaths={paths}", "-s", "0"] + fargs
    for fpath in files[1:] if arm == "eecbs" else []:
        if os.path.exists(fpath):
            os.remove(fpath)
    t0 = time.time()
    msg = ""
    try:
        proc = subprocess.run(["taskset", "-c", str(core)] + cmd, capture_output=True, text=True,
                              timeout=HARD_KILL)
        stdout = proc.stdout
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        stdout, rc, msg = "", -9, "hard-kill"
    wall = (time.time() - t0) * 1000
    row = dict(arm=arm, phase=job["phase"], method=method, cfg=job["cfg"], map=m, scen=scen, N=n, seed=seed,
               solved=0, valid=0, soc="", lb=cached_lb(m, scen, n, agents), makespan="",
               wall_ms=round(wall), solver_ms="", field_ms=0, init_cost="", msg=msg)
    configs = None
    try:
        if arm in ("lacam3", "pibt") and os.path.exists(out):
            kv = parse_kv(out)
            row["solver_ms"] = kv.get("comp_time", "")
            row["field_ms"] = kv.get("field_time_ms", 0)
            row["init_cost"] = kv.get("cost_initial_solution", "")
            if kv.get("solved") == "1":
                configs = parse_config_solution(out)
        elif arm == "eecbs":
            for line in stdout.splitlines():
                if line.startswith("field_time_ms="):
                    row["field_ms"] = line.split("=", 1)[1]
            if os.path.exists(csvf):
                with open(csvf) as f:
                    r = list(csv.reader(f))
                row["solver_ms"] = round(float(r[-1][0]) * 1000)
                if int(float(r[-1][5])) > 0 and os.path.exists(paths):
                    configs = paths_to_configs(parse_eecbs_paths(paths, n))
        if configs is not None:
            ok, why, soc, mk = validate(map_path(m), agents, configs)
            row["solved"] = 1
            row["valid"] = int(ok)
            if ok:
                row["soc"], row["makespan"] = soc, mk
                if method == "base" and job["phase"] == "tune":
                    save_heat_raw(arm, m, n, scen, configs)
            else:
                row["msg"] = (row["msg"] + " invalid:" + why).strip()
        elif rc not in (0, 1) and not msg:
            row["msg"] = f"rc={rc}"
    finally:
        for fpath in files:
            if os.path.exists(fpath):
                os.remove(fpath)
    return row


def key_of(r):
    return (r["arm"], r["phase"], r["method"], r["cfg"], r["map"], str(r["scen"]), str(r["N"]))


def run_all(jobs, csv_path):
    done = set()
    if os.path.exists(csv_path):
        with open(csv_path) as f:
            done = {key_of(r) for r in csv.DictReader(f)}
    todo = [j for j in jobs if key_of(j) not in done]
    print(f"{csv_path}: {len(jobs)} jobs, {len(todo)} to run", flush=True)
    q = queue.Queue()
    for j in todo:
        q.put(j)
    lock = threading.Lock()
    new = not os.path.exists(csv_path)
    fh = open(csv_path, "a", newline="")
    wr = csv.DictWriter(fh, fieldnames=FIELDS)
    if new:
        wr.writeheader()
        fh.flush()
    count = [0]

    def worker(core):
        while True:
            try:
                j = q.get_nowait()
            except queue.Empty:
                return
            try:
                row = run_job(j, core)
            except Exception as e:  # never lose a worker; record the job as a failure
                row = dict(arm=j["arm"], phase=j["phase"], method=j["method"], cfg=j["cfg"], map=j["map"],
                           scen=j["scen"], N=j["N"], seed=j["scen"], solved=0, valid=0,
                           msg=f"harness-error:{type(e).__name__}:{e}"[:200])
            with lock:
                wr.writerow(row)
                fh.flush()
                count[0] += 1
                if count[0] % 10 == 0 or count[0] == len(todo):
                    print(f"  {count[0]}/{len(todo)} {time.strftime('%H:%M:%S')}", flush=True)

    ths = [threading.Thread(target=worker, args=(c,)) for c in SOLVER_CORES]
    for t in ths:
        t.start()
    for t in ths:
        t.join()
    fh.close()


def make_jobs(arm, phase, methods, scens):
    """methods: list of (method, cfg_id, params).  Jobs are ordered instance by instance, with all
    methods of one instance adjacent, so machine-load drift is shared between methods."""
    jobs = []
    for m, ns in AGENTS[arm].items():
        for n in ns:
            for s in scens:
                for (meth, cfg, params) in methods:
                    jobs.append(dict(arm=arm, phase=phase, method=meth, cfg=cfg, params=params, map=m,
                                     scen=s, N=n))
    return jobs


def cfg_id(p):
    return "_".join(f"{k[0]}{v}" for k, v in sorted(p.items()))


def pibt_grid():
    out = []
    for g in (0.5, 0.8, 0.95):
        for h in (5, 10, 20):
            for c in (2, 4):
                out.append(dict(gamma=g, horizon=h, cap=c))
    return out


def eecbs_grid(static):
    out = []
    for key in (1, 2):
        for g in (0.9, 1.0):
            for h in (32, 128):
                if static:
                    out.append(dict(key=key, gamma=g, horizon=h, cap=2))
                else:
                    for w in (1, 8):
                        out.append(dict(key=key, gamma=g, horizon=h, cap=2, window=w))
    return out


def tuned():
    with open(os.path.join(ROOT, "tuned_params.json")) as f:
        return json.load(f)


def jobset(name):
    base = [("base", "-", {})]
    if name == "tune_base":  # baselines on tuning set for all arms (needed for heat maps)
        return [("lacam3", make_jobs("lacam3", "tune", base, TUNE_SCENS)),
                ("pibt", make_jobs("pibt", "tune", base, TUNE_SCENS)),
                ("eecbs", make_jobs("eecbs", "tune", base, TUNE_SCENS))]
    if name == "tune_pibt":
        meth = [(mm, cfg_id(p), p) for p in pibt_grid() for mm in ("forecast", "static")]
        return [("pibt", make_jobs("pibt", "tune", meth, TUNE_SCENS))]
    if name == "tune_eecbs":
        meth = [("forecast", cfg_id(p), p) for p in eecbs_grid(False)] + \
               [("static", cfg_id(p), p) for p in eecbs_grid(True)]
        return [("eecbs", make_jobs("eecbs", "tune", meth, TUNE_SCENS))]
    if name == "tune_lacam3":
        t = tuned()["lacam3_candidates"]
        meth = [(mm, cfg_id(p), p) for mm in ("forecast", "static") for p in t[mm]]
        return [("lacam3", make_jobs("lacam3", "tune", meth, TUNE_SCENS))]
    if name.startswith("test_"):
        arm = name[5:]
        t = tuned()[arm]
        meth = [("base", "-", {})]
        if arm == "lacam3":
            meth.append(("base2", "-", {}))
        meth += [("static", cfg_id(t["static"]), t["static"]),
                 ("forecast", cfg_id(t["forecast"]), t["forecast"]),
                 ("ablA", cfg_id(t["forecast"]), t["forecast"])]
        if arm == "eecbs":
            meth.append(("ablB", cfg_id(t["forecast"]), t["forecast"]))
        return [(arm, make_jobs(arm, "test", meth, TEST_SCENS))]
    if name == "check_ablB":  # ablB == ablA by construction for W=1 arms: confirm on scen 1
        out = []
        for arm in ("pibt", "lacam3"):
            t = tuned()[arm]["forecast"]
            jobs = [j for j in make_jobs(arm, "check", [("ablA", cfg_id(t), t), ("ablB", cfg_id(t), t)], [1])]
            jobs = [j for j in jobs if j["N"] == AGENTS[arm][j["map"]][2]]
            out.append((arm, jobs))
        return out
    raise SystemExit(f"unknown jobset {name}")


if __name__ == "__main__":
    os.makedirs(RUNS, exist_ok=True)
    for arm, jobs in jobset(sys.argv[1]):
        run_all(jobs, os.path.join(RUNS, f"{arm}_{sys.argv[1]}.csv"))
