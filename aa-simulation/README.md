# A/A simulation: how often the results banner names a winner when there is no difference

This folder checks Flagsmith PR [#9134](https://github.com/Flagsmith/flagsmith/pull/9134) (issue [#9133](https://github.com/Flagsmith/flagsmith/issues/9133)) with simulated A/A experiments: every arm has the same true conversion rate, so any declared winner is a false one.

For each simulated experiment we take Flagsmith's own code and ask what the results banner (`ExperimentRecommendation.tsx`) would show:

- **Backend:** `api/experimentation/stats.py`, run unchanged. The display floor of `services._infer_treatment` (minimum identities and conversions per arm) is restated in `py/sim.py`, because `services.py` needs Django; the two thresholds are read from `api/experimentation/constants.py`.
- **Frontend:** `frontend/web/components/experiments/results/derive.ts` of each ref, run in Node. Only its five non-relative imports are pointed at small stubs in `js/stubs/` (moment, colours, type names, `getPrimaryMetric`); the decision logic is untouched.
- **Banner rule**, as each ref's `ExperimentRecommendation.tsx` reads the summary: on `main`, any summary is shown as a winner ("Winner Probability Confirmed" or "Control is the winner"); with the PR, a winner is shown only when the summary is conclusive, otherwise "Not enough evidence yet".

No Flagsmith files are copied here. `run.sh` reads them from your Flagsmith checkout with `git show <ref>:<path>`:

| ref | commit |
|---|---|
| upstream (`main`; these files are identical in tag `v2.295.2`) | `98fa536f430053a5a7a49a59d72ffd742ca1a88e` |
| PR #9134 head | `164df6bb9ccfde20d57a54f5b1f98a23453b07f9` |

`run.sh` stops if `stats.py` or the display floor differ between the two refs (the PR does not change the backend).

## Parameters

| scenario | baseline conversion | arms (incl. control) | looks × new users per arm | runs | seed |
|---|---|---|---|---|---|
| A (same setup as [#9135](https://github.com/Flagsmith/flagsmith/issues/9135)) | 10% | 2 | 30 × 100 | 10,000 | 20261127 |
| B | 5% | 2 | 30 × 100 | 10,000 | 20261128 |
| C | 20% | 2 | 30 × 100 | 10,000 | 20261129 |
| D | 10% | 3 | 30 × 100 | 10,000 | 20261130 |

Data are cumulative: look *k* covers all 100·*k* users per arm, as the results page does. Conversion metric (0/1), higher is better, equal traffic per arm.

## Run it

Requires git, Python 3.12+ (uses `random.binomialvariate`) and Node 22.18+ (runs `.ts` with built-in type stripping). No packages to install.

```sh
git clone --filter=blob:none https://github.com/Flagsmith/flagsmith.git
git -C flagsmith fetch origin pull/9134/head      # brings in the PR commit
./run.sh --flagsmith-src ./flagsmith
```

If the PR branch has moved on, the commit can also be fetched from the fork: `git -C flagsmith fetch https://github.com/NadyKor15/flagsmith.git 164df6bb9ccfde20d57a54f5b1f98a23453b07f9`.

`run.sh` prints the table below and, at 10,000 runs, compares every result file with `expected/` (`all files match expected/`). It takes under a minute. Other refs: `--upstream-ref`, `--pr-ref`; fewer runs: `--runs 1000`.

Published figures were produced with Python 3.14.8 and Node 26.12.1.

## Results (95% Wilson intervals)

(a) the banner names a winner at the final look (3,000 users per arm); (b) it names one at least once over the 30 looks.

| scenario | `main` (a) | PR (a) | `main` (b) | PR (b) |
|---|---|---|---|---|
| **A**: 10%, 2 arms | **100.00%** [99.96–100] | **10.36%** [9.78–10.97] | 100.00% [99.96–100] | 45.77% [44.80–46.75] |
| B: 5%, 2 arms | 100.00% [99.96–100] | 9.66% [9.10–10.25] | 100.00% [99.96–100] | 41.59% [40.63–42.56] |
| C: 20%, 2 arms | 100.00% [99.96–100] | 9.21% [8.66–9.79] | 100.00% [99.96–100] | 45.92% [44.95–46.90] |
| D: 10%, 3 arms | 100.00% [99.96–100] | 8.66% [8.12–9.23] | 100.00% [99.96–100] | 35.38% [34.45–36.32] |

On `main` the banner names a winner whenever the display floor is met. With the PR, the final-look rate is close to the 10% that two one-sided 5% thresholds allow on a single look.

### Cross-check with #9135

Issue #9135 reports two numbers for the same setup as scenario A. Computed from our runs with its definitions (`py/control_c.py`):

| | #9135 | this simulation |
|---|---|---|
| single read at the final look, chance to win > 95% | 3.9% [3.5–4.3] | 4.03% [3.66–4.43] |
| stop at the first look above 95% or below 5%; that look is above 95% | 13.4% [12.7–14.1] | 13.72% [13.06–14.41] |

The intervals overlap.

### Self-checks

- The banner decision from the real `derive.ts` is compared with an independent restatement of each rule (`refRule` in `js/decide.mjs`) on every simulated look (1,200,000 looks, both refs): 0 mismatches.
- The same comparison on 5,000 random and boundary inputs (exactly 0.95 and 0.05, missing inference, 1–3 treatments; `js/equiv.mjs`): 0 mismatches.

## Limitations

- Conversion metrics only, higher is better, equal split, equal batches of 100 per look. Value metrics (e.g. revenue), lower-is-better metrics and unequal splits were not simulated.
- Experiment status `running`. With the PR, status only changes the text of the "not enough evidence" banner.
- With the PR, "Control is the winner" is shown when every variant is below 5%. That is how the PR reads the documented rule; the docs state only that a variant under 5% loses.
- The PR does not address peeking. Checking every look and stopping at the first named winner still gives 46% in scenario A; that is the subject of #9135.

## Files

`run.sh` · `py/sim.py` (simulation, backend) · `py/control_c.py` (#9135 cross-check) · `py/summary.py` · `py/compare.py` · `js/decide.mjs` (banner decision per look) · `js/equiv.mjs` · `js/stubs/` · `expected/` (result files of the published run; `out/` and `build/` are created by `run.sh`).
