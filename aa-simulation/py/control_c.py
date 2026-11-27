"""Cross-check against issue #9135, using its definitions (read from the issue text):
"Stop at the first look over 95% or under 5%: false Winning" = share of runs whose FIRST look with
chance_to_win > 0.95 or < 0.05 (floor applied) is a look with chance_to_win > 0.95.
"Read once at the final look: false Winning" = chance_to_win > 0.95 at look 30.
Computed for the 2-arm scenarios from <out>/inf-*.json.gz. Writes <out>/control-c.json.

Usage: python3 control_c.py <out-dir>
"""
import gzip
import json
import math
import os
import sys

OUT = sys.argv[1]


def wilson(k, n, z=1.959963984540054):
    ph = k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return [ph, max(0.0, c - h), min(1.0, c + h)]


res = {}
for name in ["A", "B", "C"]:
    with gzip.open(os.path.join(OUT, f"inf-{name}.json.gz"), "rt") as f:
        data = json.load(f)
    runs = data["runs"]
    first_upper = first_lower = never = final_upper = 0
    for looks in runs:
        stop = None
        for lk in looks:
            x = lk["inf"][0]
            if x is None:
                continue
            if x[3] > 0.95:
                stop = "up"
                break
            if x[3] < 0.05:
                stop = "down"
                break
        if stop == "up":
            first_upper += 1
        elif stop == "down":
            first_lower += 1
        else:
            never += 1
        x = looks[-1]["inf"][0]
        if x is not None and x[3] > 0.95:
            final_upper += 1
    n = len(runs)
    res[name] = {
        "runs": n,
        "issue9135_stop_first_crossing_is_winning": wilson(first_upper, n), "count": first_upper,
        "stop_first_crossing_is_losing": wilson(first_lower, n),
        "never_crossed": never,
        "issue9135_final_look_winning": wilson(final_upper, n),
    }
with open(os.path.join(OUT, "control-c.json"), "w") as f:
    json.dump(res, f, indent=1)
print(json.dumps(res))
