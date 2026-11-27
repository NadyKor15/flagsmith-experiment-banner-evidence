"""Print the headline table from <out>/decide-*.json and <out>/control-c.json.

Usage: python3 summary.py <out-dir>
"""
import json
import os
import sys

out = sys.argv[1]


def pct(w):
    return f"{100 * w[0]:6.2f}% [{100 * w[1]:.2f}-{100 * w[2]:.2f}]"


print("\nscenario  side       (a) final look declares     (b) any of 30 looks declares")
for name in "ABCD":
    with open(os.path.join(out, f"decide-{name}.json")) as f:
        d = json.load(f)
    m = d["meta"]
    for side in ("upstream", "pr"):
        s = d[side]
        print(f"{name} base={m['base']:.2f} arms={m['arms']}  {side:8s}  "
              f"{pct(s['a_final_look_declares'])}    {pct(s['b_any_look_declares'])}")
    print(f"{'':22s}derive.ts vs restated rule, mismatching looks: "
          f"upstream {d['upstream']['module_vs_restated_rule_mismatches']}, "
          f"pr {d['pr']['module_vs_restated_rule_mismatches']}")

with open(os.path.join(out, "control-c.json")) as f:
    c = json.load(f)["A"]
print("\ncross-check with #9135 (scenario A):")
print(f"  final look, chance_to_win > 95%:            {pct(c['issue9135_final_look_winning'])}   (#9135: 3.9% [3.5-4.3])")
print(f"  stop at first crossing, crossing is > 95%:  {pct(c['issue9135_stop_first_crossing_is_winning'])}   (#9135: 13.4% [12.7-14.1])")
with open(os.path.join(out, "equiv.json")) as f:
    e = json.load(f)
print(f"\nrandom/boundary inputs: {e['cases']} cases, mismatches upstream {e['upstream_mismatch']}, pr {e['pr_mismatch']}")
