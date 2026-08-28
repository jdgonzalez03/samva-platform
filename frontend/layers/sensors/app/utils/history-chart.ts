import { MAX_CHART_BUCKETS } from '../constants/history'
import type { PlotAverage, SeriesPoint } from '../types/sensors'

export interface ChartPoint {
  // Time in epoch milliseconds, so the x axis can work with numbers.
  t: number
  // `null` means "no data in this bucket".
  value: number | null
}

export interface BarPoint {
  index: number
  label: string
  value: number
  // How many readings were used to compute the average.
  // More readings = more reliable average.
  sampleCount: number
}

export interface SeriesSummary {
  // Points sent by the backend (empty buckets are not counted).
  pointCount: number
  // Raw readings behind those points.
  readingCount: number
  min: number
  max: number
  average: number
  firstAt: number
  lastAt: number
}

// The backend does not send empty buckets. This function adds them back,
// with `value: null`.
//
// Why: without the empty buckets, the line chart would draw a straight line
// between two hours where no sensor reported anything. That looks like real
// data, but it is not. With `null`, the chart leaves a gap instead.
//
// Note: `null` is only used here. The chart changes it to `NaN` before giving
// it to Unovis, because Unovis reads `null` as the number zero.
//
// The grid starts at `fromMs`, the same origin the backend uses for
// `date_bin`, so every received point falls exactly on one slot.
export const fillBuckets = (
  points: SeriesPoint[],
  fromMs: number,
  toMs: number,
  bucketSeconds: number,
): ChartPoint[] => {
  const received = points.map((point) => ({
    t: Date.parse(point.t),
    value: point.value,
  }))

  // If the bucket size is not valid, return the points as they are.
  const bucketMs = bucketSeconds * 1000
  if (!Number.isFinite(bucketMs) || bucketMs <= 0) return received

  // If the grid would be empty or too big, return the points as they are.
  const slots = Math.ceil((toMs - fromMs) / bucketMs)
  if (slots <= 0 || slots > MAX_CHART_BUCKETS) return received

  // Put each received point in its slot.
  const byBucket = new Map<number, number>()
  for (const point of received) {
    if (Number.isNaN(point.t)) continue
    const slot = Math.floor((point.t - fromMs) / bucketMs)
    byBucket.set(slot, point.value)
  }

  // Build the full grid. Slots without a point get `null`.
  const grid: ChartPoint[] = []
  for (let slot = 0; slot < slots; slot += 1) {
    grid.push({
      t: fromMs + slot * bucketMs,
      value: byBucket.get(slot) ?? null,
    })
  }
  return grid
}

// Computes the numbers that the screen reader reads instead of the chart.
// It uses the same data the chart draws, so both always say the same thing.
export const summariseSeries = (
  points: SeriesPoint[],
): SeriesSummary | null => {
  if (points.length === 0) return null

  let min = Number.POSITIVE_INFINITY
  let max = Number.NEGATIVE_INFINITY
  let total = 0
  let readingCount = 0
  let firstAt = Number.POSITIVE_INFINITY
  let lastAt = Number.NEGATIVE_INFINITY

  for (const point of points) {
    min = Math.min(min, point.value)
    max = Math.max(max, point.value)
    total += point.value
    readingCount += point.sample_count
    // Skip points with a date we cannot parse.
    const at = Date.parse(point.t)
    if (Number.isNaN(at)) continue
    firstAt = Math.min(firstAt, at)
    lastAt = Math.max(lastAt, at)
  }

  return {
    pointCount: points.length,
    readingCount,
    min,
    max,
    average: total / points.length,
    firstAt,
    lastAt,
  }
}

export interface AverageGroup {
  variableId: number
  name: string
  unit: string
  semanticKey: PlotAverage['semantic_key']
  bars: BarPoint[]
}

// Groups the averages by variable. Each group becomes one bar chart, with one
// bar per plot of the farm.
//
// Groups are keyed by `variable_id`, not by `semantic_key`. Two variables can
// share the same `semantic_key`, and mixing them would average readings that
// have nothing to do with each other.
export const groupAveragesByVariable = (
  averages: PlotAverage[],
): AverageGroup[] => {
  const groups = new Map<number, AverageGroup>()

  for (const average of averages) {
    // Create the group the first time we see this variable.
    let group = groups.get(average.variable_id)
    if (!group) {
      group = {
        variableId: average.variable_id,
        name: average.variable_name,
        unit: average.unit,
        semanticKey: average.semantic_key,
        bars: [],
      }
      groups.set(average.variable_id, group)
    }
    group.bars.push({
      index: group.bars.length,
      label: average.plot_name,
      value: average.average,
      sampleCount: average.sample_count,
    })
  }

  // Sort groups by name so the charts always appear in the same order.
  return [...groups.values()].sort((a, b) => a.name.localeCompare(b.name))
}
