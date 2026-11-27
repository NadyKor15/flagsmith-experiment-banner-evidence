// Runs the real derive.ts of both refs (extracted into ../build by run.sh) over the simulated
// backend inference and counts how often the results banner (ExperimentRecommendation.tsx)
// declares a winner.
//
// Banner semantics, read from ExperimentRecommendation.tsx of each ref:
//   upstream: summary === null -> no banner; summary.controlWins -> "Control is the winner";
//             otherwise "<chance> Winner Probability Confirmed". Every non-null summary declares a winner.
//   PR:       summary === null -> no banner; !summary.isConclusive -> info banner "Not enough evidence yet"
//             (no winner); otherwise the same two winner banners.
//
// Usage: node decide.mjs <out-dir> <out-dir>/inf-A.json [more files…]
//        -> prints JSON, writes <out-dir>/decide-<name>.json
import fs from 'node:fs'
import path from 'node:path'

const U = await import('../build/upstream/derive.ts')
const P = await import('../build/pr/derive.ts')
const [outDir, ...files] = process.argv.slice(2)

const wilson = (k, n, z = 1.959963984540054) => {
  if (n === 0) return [null, null, null]
  const ph = k / n
  const d = 1 + (z * z) / n
  const c = (ph + (z * z) / (2 * n)) / d
  const h = (z * Math.sqrt((ph * (1 - ph)) / n + (z * z) / (4 * n * n))) / d
  return [ph, Math.max(0, c - h), Math.min(1, c + h)]
}

const TREAT_KEYS = ['B', 'C', 'D', 'E']

const makeExperiment = (arms) => ({
  feature: {
    initial_value: 'a',
    multivariate_options: TREAT_KEYS.slice(0, arms - 1).map((key, i) => ({
      id: i + 1, key, string_value: key.toLowerCase(), type: 'string',
    })),
  },
  metrics: [{ direction: 'up', metric: 1 }],
  status: 'running',
})

const banner = (mod, isPr, experiment, results) => {
  const s = mod.deriveSummary(experiment, results)
  if (!s) return 'none'
  if (isPr && !s.isConclusive) return 'inconclusive'
  return s.controlWins ? 'control' : 'variant'
}

// Independent restatement of each rule (cross-check that the stubbed module behaves as read).
const refRule = (isPr, inf) => {
  const present = inf.filter((x) => x !== null)
  if (!present.length) return 'none'
  let best = -1
  for (const x of present) if (x[3] > best) best = x[3]
  const all = present.length === inf.length
  const ctrl = all ? Math.max(0, 1 - inf.reduce((s, x) => s + x[3], 0)) : null
  if (!isPr) return ctrl !== null && ctrl > best ? 'control' : 'variant'
  if (best > 0.95) return 'variant'
  if (ctrl !== null && best < 0.05) return 'control'
  return 'inconclusive'
}

const declares = (b) => b === 'variant' || b === 'control'

const report = {}
for (const file of files) {
  const { meta, runs } = JSON.parse(fs.readFileSync(file, 'utf8'))
  const experiment = makeExperiment(meta.arms)
  const keys = TREAT_KEYS.slice(0, meta.arms - 1)
  const out = {}
  for (const [ver, mod, isPr] of [['upstream', U, false], ['pr', P, true]]) {
    let final = 0, any = 0, first = 0, finalCtrl = 0, finalVar = 0, finalNone = 0, mismatch = 0
    let looksShown = 0, looksDeclared = 0, looksTotal = 0
    const firstDeclareLook = {}
    for (const looks of runs) {
      let anyHit = false
      looks.forEach((lk, i) => {
        const inference = {}
        keys.forEach((k, j) => {
          const x = lk.inf[j]
          inference[k] = x === null ? null
            : { chance_to_win: x[3], ci_high: x[2], ci_low: x[1], lift: x[0] }
        })
        const results = { metrics: [{ inference, metric_id: 1, variants: {} }] }
        const b = banner(mod, isPr, experiment, results)
        if (b !== refRule(isPr, lk.inf)) mismatch++
        looksTotal++
        if (b !== 'none') looksShown++
        if (declares(b)) {
          looksDeclared++
          if (!anyHit) firstDeclareLook[i + 1] = (firstDeclareLook[i + 1] ?? 0) + 1
          anyHit = true
          if (i === 0) first++
        }
        if (i === looks.length - 1) {
          if (declares(b)) final++
          if (b === 'control') finalCtrl++
          if (b === 'variant') finalVar++
          if (b === 'none') finalNone++
        }
      })
      if (anyHit) any++
    }
    const n = runs.length
    out[ver] = {
      a_final_look_declares: wilson(final, n), a_count: final,
      a_final_variant: wilson(finalVar, n), a_final_control: wilson(finalCtrl, n), a_final_no_banner: finalNone,
      b_any_look_declares: wilson(any, n), b_count: any,
      first_look_declares: wilson(first, n),
      share_of_all_looks_declaring: wilson(looksDeclared, looksTotal),
      share_of_all_looks_banner_shown: wilson(looksShown, looksTotal),
      first_declaring_look_histogram: firstDeclareLook,
      module_vs_restated_rule_mismatches: mismatch,
    }
  }
  out.c_control = {
    any_look_gt95: wilson(meta.c_any_look_gt95, meta.runs), any_count: meta.c_any_look_gt95,
    first_look_gt95: wilson(meta.c_first_look_gt95, meta.runs),
    final_look_gt95: wilson(meta.c_final_look_gt95, meta.runs),
  }
  out.meta = meta
  report[meta.name] = out
  fs.writeFileSync(path.join(outDir, `decide-${meta.name}.json`), JSON.stringify(out, null, 1))
}
console.log(JSON.stringify(report))
