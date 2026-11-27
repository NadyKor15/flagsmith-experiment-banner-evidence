// Cross-check on random and boundary inputs: the real derive.ts (both refs) vs the restated rule
// used in decide.mjs. Includes exact 0.95 / 0.05, nulls, 1–3 treatments. Prints mismatch counts.
const U = await import('../build/upstream/derive.ts')
const P = await import('../build/pr/derive.ts')
let seed = 20261127
const rnd = () => ((seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648)
const KEYS = ['B', 'C', 'D']
const SPECIAL = [0, 0.05, 0.0499999, 0.0500001, 0.5, 0.95, 0.9499999, 0.9500001, 1]
const ref = (isPr, inf) => {
  const present = inf.filter((x) => x !== null)
  if (!present.length) return 'none'
  const best = Math.max(...present.map((x) => x.chance_to_win))
  const ctrl = present.length === inf.length ? Math.max(0, 1 - inf.reduce((s, x) => s + x.chance_to_win, 0)) : null
  if (!isPr) return ctrl !== null && ctrl > best ? 'control' : 'variant'
  if (best > 0.95) return 'variant'
  if (ctrl !== null && best < 0.05) return 'control'
  return 'inconclusive'
}
const res = { cases: 0, upstream_mismatch: 0, pr_mismatch: 0, by_outcome: {} }
for (let t = 0; t < 5000; t++) {
  const k = 1 + Math.floor(rnd() * 3)
  const exp = {
    feature: { initial_value: 'a', multivariate_options: KEYS.slice(0, k).map((key, i) => ({ id: i + 1, key, string_value: key, type: 'string' })) },
    metrics: [{ direction: 'up', metric: 1 }], status: 'running',
  }
  const infArr = KEYS.slice(0, k).map(() => {
    if (rnd() < 0.1) return null
    const c = rnd() < 0.4 ? SPECIAL[Math.floor(rnd() * SPECIAL.length)] : rnd()
    return { chance_to_win: c, ci_high: 0.1, ci_low: -0.1, lift: (rnd() - 0.5) / 5 }
  })
  const inference = Object.fromEntries(KEYS.slice(0, k).map((key, i) => [key, infArr[i]]))
  const results = { metrics: [{ inference, metric_id: 1, variants: {} }] }
  for (const [mod, isPr, name] of [[U, false, 'upstream'], [P, true, 'pr']]) {
    const s = mod.deriveSummary(exp, results)
    const got = !s ? 'none' : isPr && !s.isConclusive ? 'inconclusive' : s.controlWins ? 'control' : 'variant'
    const want = ref(isPr, infArr)
    if (got !== want) res[`${name}_mismatch`]++
    res.by_outcome[`${name}:${got}`] = (res.by_outcome[`${name}:${got}`] ?? 0) + 1
  }
  res.cases++
}
console.log(JSON.stringify(res))
