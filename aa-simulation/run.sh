#!/usr/bin/env bash
# A/A simulation of the Flagsmith Experiments results banner: upstream vs PR #9134.
#
#   ./run.sh --flagsmith-src <path to a Flagsmith git checkout> [--upstream-ref REF] [--pr-ref REF] [--runs N]
#
# The Flagsmith files are not copied into this folder. They are read from your checkout with
# `git show <ref>:<path>`, so both refs must be present there (see README.md).
set -euo pipefail

UP_REF=98fa536f430053a5a7a49a59d72ffd742ca1a88e   # Flagsmith main; same files as tag v2.295.2
PR_REF=164df6bb9ccfde20d57a54f5b1f98a23453b07f9   # PR #9134 head
RUNS=10000
FS_SRC=""

while [ $# -gt 0 ]; do
  case "$1" in
    --flagsmith-src) FS_SRC="$2"; shift 2 ;;
    --upstream-ref) UP_REF="$2"; shift 2 ;;
    --pr-ref) PR_REF="$2"; shift 2 ;;
    --runs) RUNS="$2"; shift 2 ;;
    -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$FS_SRC" ] || { echo "--flagsmith-src is required" >&2; exit 2; }

HERE="$(cd "$(dirname "$0")" && pwd)"
BUILD="$HERE/build"
OUT="$HERE/out"
PY="${PYTHON:-python3}"

STATS=api/experimentation/stats.py
CONST=api/experimentation/constants.py
DERIVE=frontend/web/components/experiments/results/derive.ts

for ref in "$UP_REF" "$PR_REF"; do
  git -C "$FS_SRC" cat-file -e "$ref^{commit}" 2>/dev/null || {
    echo "commit $ref not found in $FS_SRC (see README.md: 'Get the two Flagsmith commits')" >&2; exit 1; }
done

echo "python: $($PY --version 2>&1)   node: $(node --version)"
echo "upstream: $UP_REF"
echo "pr:       $PR_REF"
rm -rf "$BUILD" "$OUT"
mkdir -p "$BUILD/upstream" "$BUILD/pr" "$OUT"
printf '{"type":"module"}\n' > "$BUILD/package.json"

# Backend: stats.py and the display floor. The PR does not change them; check that.
git -C "$FS_SRC" show "$UP_REF:$STATS" > "$BUILD/stats.py"
git -C "$FS_SRC" show "$PR_REF:$STATS" | cmp -s - "$BUILD/stats.py" || {
  echo "$STATS differs between the two refs; this harness runs one backend for both" >&2; exit 1; }
const_val() {
  git -C "$FS_SRC" show "$1:$CONST" | sed -n "s/^$2 *= *\([0-9][0-9]*\).*/\1/p"
}
MIN_IDS=$(const_val "$UP_REF" RESULTS_MIN_IDENTITIES_PER_VARIANT)
MIN_CONV=$(const_val "$UP_REF" RESULTS_MIN_CONVERSIONS_PER_VARIANT)
[ -n "$MIN_IDS" ] && [ -n "$MIN_CONV" ] || { echo "display floor not found in $CONST" >&2; exit 1; }
[ "$MIN_IDS" = "$(const_val "$PR_REF" RESULTS_MIN_IDENTITIES_PER_VARIANT)" ] &&
[ "$MIN_CONV" = "$(const_val "$PR_REF" RESULTS_MIN_CONVERSIONS_PER_VARIANT)" ] || {
  echo "display floor differs between the two refs" >&2; exit 1; }
echo "display floor: $MIN_IDS identities / $MIN_CONV conversions per arm"

# Frontend: derive.ts of each ref; only the 5 non-relative imports are pointed at js/stubs.
for side in upstream pr; do
  ref=$UP_REF; [ "$side" = pr ] && ref=$PR_REF
  git -C "$FS_SRC" show "$ref:$DERIVE" > "$BUILD/$side/derive.orig.ts"
  sed -e "s#from 'moment'#from '../../js/stubs/moment.ts'#" \
      -e "s#from 'components/charts'#from '../../js/stubs/charts.ts'#" \
      -e "s#from 'common/theme/tokens'#from '../../js/stubs/tokens.ts'#" \
      -e "s#from 'common/types/responses'#from '../../js/stubs/responses.ts'#" \
      -e "s#from 'components/experiments/constants'#from '../../js/stubs/constants.ts'#" \
      "$BUILD/$side/derive.orig.ts" > "$BUILD/$side/derive.ts"
  changed=$(diff "$BUILD/$side/derive.orig.ts" "$BUILD/$side/derive.ts" | grep -c '^>' || true)
  [ "$changed" = 5 ] || { echo "$side derive.ts: expected 5 rewritten import lines, got $changed" >&2; exit 1; }
  if grep -nE "from '[^.]" "$BUILD/$side/derive.ts"; then
    echo "$side derive.ts: unexpected non-relative import left" >&2; exit 1
  fi
done

cd "$HERE/py"
common=(--runs "$RUNS" --stats-py "$BUILD/stats.py" --min-identities "$MIN_IDS" --min-conversions "$MIN_CONV" --out "$OUT")
$PY sim.py --name A --base 0.10 --arms 2 --seed 20261127 "${common[@]}"
$PY sim.py --name B --base 0.05 --arms 2 --seed 20261128 "${common[@]}"
$PY sim.py --name C --base 0.20 --arms 2 --seed 20261129 "${common[@]}"
$PY sim.py --name D --base 0.10 --arms 3 --seed 20261130 "${common[@]}"

cd "$HERE/js"
node equiv.mjs > "$OUT/equiv.json"
node decide.mjs "$OUT" "$OUT"/inf-A.json "$OUT"/inf-B.json "$OUT"/inf-C.json "$OUT"/inf-D.json > "$OUT/decide-all.json"
gzip -f "$OUT"/inf-*.json
$PY "$HERE/py/control_c.py" "$OUT" > /dev/null

$PY "$HERE/py/summary.py" "$OUT"
if [ "$RUNS" = 10000 ]; then
  $PY "$HERE/py/compare.py" "$HERE/expected" "$OUT"
fi
