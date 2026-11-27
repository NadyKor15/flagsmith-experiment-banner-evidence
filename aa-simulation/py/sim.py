"""A/A simulation of the Flagsmith Experiments backend inference.

The statistics are Flagsmith's own api/experimentation/stats.py, read unchanged from a Flagsmith
checkout (run.sh extracts it with `git show <ref>:api/experimentation/stats.py`). The display floor
of services._infer_treatment (minimum identities / conversions per arm, OCCURRENCE metric,
higher-is-better) is restated below because services.py imports Django; the two thresholds are read
from api/experimentation/constants.py of the same ref by run.sh and passed in.

Per run: every arm gets `--per-look` new identities per look, each converting with the SAME
probability (A/A); results are cumulative, as the results query covers the whole window.
Writes <out>/inf-<name>.json with the per-look inference for every treatment.

Usage: python3 sim.py --name A --base 0.10 --arms 2 --seed 20261127 \
    --stats-py ../build/stats.py --min-identities 50 --min-conversions 5 --out ../out
"""
import argparse
import json
import os
import random
import sys
import time
import types


def load_stats(path):
    src = open(path, encoding="utf-8").read()
    if sys.version_info < (3, 10):
        # stats.py uses PEP 604 annotations (X | None); only annotations become strings.
        src = "from __future__ import annotations\n" + src
    mod = types.ModuleType("flagsmith_stats")
    exec(compile(src, path, "exec"), mod.__dict__)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--base", type=float, required=True)
    ap.add_argument("--arms", type=int, required=True)  # incl. control
    ap.add_argument("--looks", type=int, default=30)
    ap.add_argument("--per-look", type=int, default=100)
    ap.add_argument("--runs", type=int, default=10000)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--stats-py", required=True)
    ap.add_argument("--min-identities", type=int, required=True)
    ap.add_argument("--min-conversions", type=int, required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    rng = random.Random(a.seed)
    if not hasattr(rng, "binomialvariate"):
        sys.exit("Python >= 3.12 is required (random.binomialvariate); the published figures depend on it.")

    stats = load_stats(a.stats_py)
    VariantStats = stats.VariantStats
    compare_to_control = stats.compare_to_control

    def infer_treatment(control, treatment):
        """services._infer_treatment for an OCCURRENCE metric with lower_is_better=False."""
        if (
            control is None
            or control.n < a.min_identities
            or treatment.n < a.min_identities
        ):
            return None
        if control.sum < a.min_conversions or treatment.sum < a.min_conversions:
            return None
        return compare_to_control(control, treatment)

    p, m = a.base, a.per_look
    t0 = time.time()
    runs = []
    c_any = c_first = c_final = 0
    for _ in range(a.runs):
        conv = [0] * a.arms
        looks = []
        hit_any = False
        for look in range(a.looks):
            for i in range(a.arms):
                conv[i] += rng.binomialvariate(m, p)
            n = m * (look + 1)
            arms = [VariantStats(n=n, sum=float(c), sum_squares=float(c)) for c in conv]
            row = []
            hit = False
            for t in arms[1:]:
                inf = infer_treatment(arms[0], t)
                if inf is None:
                    row.append(None)
                else:
                    row.append([inf.lift, inf.ci_low, inf.ci_high, inf.chance_to_win])
                    if inf.chance_to_win > 0.95:
                        hit = True
            if hit:
                hit_any = True
                if look == 0:
                    c_first += 1
            if hit and look == a.looks - 1:
                c_final += 1
            looks.append({"n": n, "conv": list(conv), "inf": row})
        if hit_any:
            c_any += 1
        runs.append(looks)

    meta = {
        "name": a.name, "base": p, "arms": a.arms, "looks": a.looks, "per_look": m,
        "runs": a.runs, "seed": a.seed, "python": sys.version.split()[0],
        "rng_draw": "binomialvariate",
        "seconds": round(time.time() - t0, 2),
        # raw backend counts: chance_to_win > 0.95 for any treatment (display floor applied)
        "c_any_look_gt95": c_any, "c_first_look_gt95": c_first, "c_final_look_gt95": c_final,
    }
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, f"inf-{a.name}.json"), "w") as f:
        json.dump({"meta": meta, "runs": runs}, f, separators=(",", ":"))
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
