"""Compare a fresh run with the published figures in expected/ (timing fields ignored).

Usage: python3 compare.py <expected-dir> <out-dir>   -> exit 0 if every file matches
"""
import json
import os
import sys

IGNORED = {"seconds", "python"}


def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if k not in IGNORED}
    if isinstance(x, list):
        return [strip(v) for v in x]
    return x


exp_dir, out_dir = sys.argv[1], sys.argv[2]
bad = 0
for name in sorted(os.listdir(exp_dir)):
    if not name.endswith(".json"):
        continue
    with open(os.path.join(exp_dir, name)) as f:
        want = strip(json.load(f))
    path = os.path.join(out_dir, name)
    if not os.path.exists(path):
        print(f"MISSING {name}")
        bad += 1
        continue
    with open(path) as f:
        got = strip(json.load(f))
    ok = got == want
    bad += not ok
    print(f"{'MATCH' if ok else 'DIFF '} {name}")
print("all files match expected/" if not bad else f"{bad} file(s) differ from expected/")
sys.exit(1 if bad else 0)
