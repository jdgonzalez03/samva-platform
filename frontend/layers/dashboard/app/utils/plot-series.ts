import type { PlotSeries } from '../../../farm/app/types/farm'

export interface SeriesPoint {
  t: number
  value: number
}

export interface SeriesStats {
  min: number
  max: number
  average: number
}

export interface HeatmapCell {
  hour: number
  value: number | null
}

export interface HeatmapRow {
  day: Date
  cells: HeatmapCell[]
}

const HOUR_MS = 60 * 60 * 1000

export const toSeriesPoints = (series: PlotSeries | undefined): SeriesPoint[] =>
  (series?.points ?? []).map((point) => ({
    t: Date.parse(point.t),
    value: point.value,
  }))

export const pointsWithinHours = (
  points: SeriesPoint[],
  hours: number,
  now: number,
): SeriesPoint[] => points.filter((point) => point.t > now - hours * HOUR_MS)

export const seriesStats = (points: SeriesPoint[]): SeriesStats | null => {
  if (points.length === 0) return null
  const values = points.map((point) => point.value)
  return {
    min: Math.min(...values),
    max: Math.max(...values),
    average: values.reduce((sum, value) => sum + value, 0) / values.length,
  }
}

const startOfLocalDay = (time: number): Date => {
  const day = new Date(time)
  day.setHours(0, 0, 0, 0)
  return day
}

// One row per local calendar day (oldest first) and one cell per local hour.
// The backend buckets in UTC, so the grouping has to happen here, in the
// viewer's timezone, or "18:00" would not mean the farmer's evening.
export const buildHeatmap = (
  points: SeriesPoint[],
  days: number,
  now: number,
): HeatmapRow[] => {
  const today = startOfLocalDay(now)
  const rows: HeatmapRow[] = []
  const cellsByDay = new Map<number, (number | null)[]>()

  for (let offset = days - 1; offset >= 0; offset--) {
    const day = new Date(today)
    day.setDate(today.getDate() - offset)
    const cells: (number | null)[] = Array.from({ length: 24 }, () => null)
    cellsByDay.set(day.getTime(), cells)
    rows.push({ day, cells: [] })
  }

  for (const point of points) {
    const cells = cellsByDay.get(startOfLocalDay(point.t).getTime())
    if (cells) cells[new Date(point.t).getHours()] = point.value
  }

  return rows.map((row) => ({
    day: row.day,
    cells: cellsByDay
      .get(row.day.getTime())!
      .map((value, hour) => ({ hour, value })),
  }))
}
