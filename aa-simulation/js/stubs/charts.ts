// stub: only colours; not used in the winner decision
export const ChartDataPoint = undefined
export const buildChartColorMap = (keys: string[]) => Object.fromEntries(keys.map((k) => [k, `colour-${k}`]))
