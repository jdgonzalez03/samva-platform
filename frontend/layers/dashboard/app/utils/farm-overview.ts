import type {
  FarmOverview,
  FarmPlotSummary,
  Plot,
} from '../../../farm/app/types/farm'
import { PLOT_FILL_COLORS } from '../constants/map'
import { STALE_AFTER_MS } from '../constants/plot-detail'
import { getMappedPlots, getUnmappedPlots } from './plot-features'
import type { SeriesPoint } from './plot-series'

const HOUR_MS = 60 * 60 * 1000
const DAY_MS = 24 * HOUR_MS

// The same colour a plot has on the map: mapped plots take the palette in map
// order, and plots without a polygon continue after them.
export const plotColors = (plots: Plot[]): Map<number, string> => {
  const ordered = [...getMappedPlots(plots), ...getUnmappedPlots(plots)]
  return new Map(
    ordered.map((plot, index) => [
      plot.id,
      PLOT_FILL_COLORS[index % PLOT_FILL_COLORS.length]!,
    ]),
  )
}

export const plotSeriesPoints = (
  plot: FarmPlotSummary,
  semanticKey: string,
): SeriesPoint[] =>
  (
    plot.series.find((series) => series.semantic_key === semanticKey)?.points ??
    []
  ).map((point) => ({ t: Date.parse(point.t), value: point.value }))

export type AlertSeverity = 'critical' | 'warning' | 'info'

export type FarmAlert =
  | {
      kind: 'dry'
      severity: AlertSeverity
      plotId: number
      plotName: string
      value: number
      unit: string
    }
  | {
      kind: 'stale'
      severity: AlertSeverity
      plotId: number
      plotName: string
      at: string
    }
  | {
      kind: 'noReadings'
      severity: AlertSeverity
      plotId: number
      plotName: string
    }
  | {
      kind: 'sensorOffline'
      severity: AlertSeverity
      plotId: number
      plotName: string
      sensorName: string
      at: string
    }
  | {
      kind: 'sensorNeverSeen'
      severity: AlertSeverity
      plotId: number
      plotName: string
      sensorName: string
    }
  | {
      kind: 'noIrrigation'
      severity: AlertSeverity
      plotId: number
      plotName: string
    }

const SEVERITY_ORDER: Record<AlertSeverity, number> = {
  critical: 0,
  warning: 1,
  info: 2,
}

// Same thresholds as the plot detail page: "Bajo" on the fuzzy scale is dry
// soil, and 45 minutes without a reading is a plot that stopped reporting.
export const buildAlerts = (
  overview: FarmOverview,
  now: number,
): FarmAlert[] => {
  const alerts: FarmAlert[] = []
  const plotsWithSensors = new Set(
    overview.sensors.map((sensor) => sensor.plot_id),
  )

  for (const plot of overview.plots) {
    const base = { plotId: plot.id, plotName: plot.name }
    const moisture = plot.conditions.find(
      (condition) => condition.semantic_key === 'soil_moisture',
    )
    if (moisture?.level === 'low') {
      alerts.push({
        kind: 'dry',
        severity: 'critical',
        ...base,
        value: moisture.value,
        unit: moisture.unit,
      })
    }

    if (plot.latest_reading_at === null) {
      if (plotsWithSensors.has(plot.id)) {
        alerts.push({ kind: 'noReadings', severity: 'warning', ...base })
      }
      continue
    }
    if (now - Date.parse(plot.latest_reading_at) > STALE_AFTER_MS) {
      alerts.push({
        kind: 'stale',
        severity: 'warning',
        ...base,
        at: plot.latest_reading_at,
      })
    }

    const irrigatedAt = plot.irrigation
      ? Date.parse(plot.irrigation.requested_at)
      : null
    if (irrigatedAt === null || now - irrigatedAt > DAY_MS) {
      alerts.push({ kind: 'noIrrigation', severity: 'info', ...base })
    }
  }

  for (const sensor of overview.sensors) {
    const base = {
      plotId: sensor.plot_id,
      plotName: sensor.plot_name,
      sensorName: sensor.name,
    }
    if (sensor.status === 'offline' && sensor.last_seen_at) {
      alerts.push({
        kind: 'sensorOffline',
        severity: 'warning',
        ...base,
        at: sensor.last_seen_at,
      })
    }
    if (sensor.status === 'never_seen') {
      alerts.push({ kind: 'sensorNeverSeen', severity: 'info', ...base })
    }
  }

  return alerts.sort(
    (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity],
  )
}

export interface DailyStats {
  day: Date
  min: number
  average: number
  max: number
}

const startOfLocalDay = (time: number): number => {
  const day = new Date(time)
  day.setHours(0, 0, 0, 0)
  return day.getTime()
}

// Grouped by the viewer's local calendar day: the backend buckets in UTC.
export const dailyStats = (points: SeriesPoint[]): DailyStats[] => {
  const byDay = new Map<number, number[]>()
  for (const point of points) {
    const day = startOfLocalDay(point.t)
    const values = byDay.get(day) ?? []
    values.push(point.value)
    byDay.set(day, values)
  }
  return [...byDay.entries()]
    .sort(([a], [b]) => a - b)
    .map(([day, values]) => ({
      day: new Date(day),
      min: Math.min(...values),
      average: values.reduce((sum, value) => sum + value, 0) / values.length,
      max: Math.max(...values),
    }))
}

export interface PlotHeatmapRow {
  plotId: number
  plotName: string
  cells: { slot: number; hour: number; value: number | null }[]
}

// The last `hours` clock hours up to now, oldest first, one row per plot.
export const plotsHeatmap = (
  plots: FarmPlotSummary[],
  semanticKey: string,
  hours: number,
  now: number,
): PlotHeatmapRow[] => {
  const currentHour = Math.floor(now / HOUR_MS) * HOUR_MS
  const slots = Array.from(
    { length: hours },
    (_, index) => currentHour - (hours - 1 - index) * HOUR_MS,
  )
  return plots.map((plot) => {
    const valueBySlot = new Map(
      plotSeriesPoints(plot, semanticKey).map((point) => [
        point.t,
        point.value,
      ]),
    )
    return {
      plotId: plot.id,
      plotName: plot.name,
      cells: slots.map((slot) => ({
        slot,
        hour: new Date(slot).getHours(),
        value: valueBySlot.get(slot) ?? null,
      })),
    }
  })
}
