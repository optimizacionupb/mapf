"""Static control: H(v) = average number of agents at v per timestep, averaged over the base solutions
of the TUNING scenarios (1-5) of the same arm, map and agent count.  Only tuning-set solutions are used.
Output: runs/heat/<arm>_<map>_<N>.txt, one float per grid cell (row-major, y * width + x)."""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import HEAT, HEAT_RAW  # noqa: E402

os.makedirs(HEAT, exist_ok=True)
groups = {}
for p in sorted(glob.glob(os.path.join(HEAT_RAW, "*.json"))):
    name = os.path.basename(p)[:-5]
    arm, m, n, s = name.split("_")
    assert int(s[1:]) <= 5, "heat must come from tuning scenarios only"
    groups.setdefault((arm, m, n), []).append(p)
for (arm, m, n), files in sorted(groups.items()):
    acc = None
    for p in files:
        d = json.load(open(p))
        if acc is None:
            acc = [0.0] * (d["w"] * d["h"])
        for k, c in d["counts"].items():
            acc[int(k)] += c / d["T"] / len(files)
    with open(os.path.join(HEAT, f"{arm}_{m}_{n}.txt"), "w") as f:
        f.write(" ".join(f"{x:.5g}" for x in acc))
    print(arm, m, n, "from", len(files), "solutions, max", round(max(acc), 3))

# Fallback (fixed rule, independent of results): if the base solver solved no tuning instance at
# (arm, map, N), use the heat of the largest smaller N of the same arm and map that has one.
from run import AGENTS  # noqa: E402
import shutil  # noqa: E402
for arm, maps in AGENTS.items():
    for m, ns in maps.items():
        for i, n in enumerate(ns):
            target = os.path.join(HEAT, f"{arm}_{m}_{n}.txt")
            if os.path.exists(target):
                continue
            for n2 in reversed(ns[:i]):
                src = os.path.join(HEAT, f"{arm}_{m}_{n2}.txt")
                if os.path.exists(src):
                    shutil.copy(src, target)
                    print(arm, m, n, "has no solved tuning instance; heat copied from N =", n2)
                    break
