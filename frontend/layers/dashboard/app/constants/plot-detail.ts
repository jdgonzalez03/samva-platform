import type {
  ConditionLevel,
  PlotSensorStatus,
} from '../../../farm/app/types/farm'

type BadgeColor = 'error' | 'warning' | 'success' | 'info' | 'neutral'

export const CONDITION_ICONS: Record<string, string> = {
  soil_moisture: 'i-lucide-sprout',
  air_temperature: 'i-lucide-thermometer',
  solar_radiation: 'i-lucide-sun',
  relative_humidity: 'i-lucide-droplets',
  leaf_temperature: 'i-lucide-leaf',
  soil_temperature: 'i-lucide-thermometer-sun',
  soil_water_tension: 'i-lucide-shovel',
  co2: 'i-lucide-wind',
  battery_voltage: 'i-lucide-battery-medium',
  battery_current: 'i-lucide-battery-charging',
  solar_panel_voltage: 'i-lucide-solar-panel',
  solar_panel_current: 'i-lucide-zap',
}
export const FALLBACK_CONDITION_ICON = 'i-lucide-gauge'

// What each fuzzy level means for the crop, per variable: dry soil is the
// alarming end of moisture, while heat and strong sun are for the others.
export const LEVEL_COLORS: Record<
  string,
  Record<ConditionLevel, BadgeColor>
> = {
  soil_moisture: { low: 'error', medium: 'success', high: 'info' },
  air_temperature: { low: 'info', medium: 'success', high: 'warning' },
  solar_radiation: { low: 'neutral', medium: 'success', high: 'warning' },
}

export const SENSOR_STATUS_COLORS: Record<PlotSensorStatus, BadgeColor> = {
  online: 'success',
  offline: 'warning',
  never_seen: 'neutral',
  inactive: 'neutral',
}

// Mirrors the backend's `SENSOR_OFFLINE_AFTER`: a plot whose newest reading is
// older than this is shown as not reporting.
export const STALE_AFTER_MS = 45 * 60 * 1000

export const TREND_RANGES = ['24h', '7d'] as const
export type TrendRange = (typeof TREND_RANGES)[number]
export const TREND_RANGE_HOURS: Record<TrendRange, number> = {
  '24h': 24,
  '7d': 24 * 7,
}

export const HEATMAP_DAYS = 7

// Shared by each chart and its `<ClientOnly>` fallback so hydration never
// jumps. Keep the classes and the pixel values in step.
export const SPARKLINE_HEIGHT_CLASS = 'h-12'
export const SPARKLINE_HEIGHT = 48
export const TREND_CHART_HEIGHT_CLASS = 'h-72'
export const TREND_CHART_HEIGHT = 288
export const MINI_MAP_HEIGHT_CLASS = 'h-56'
