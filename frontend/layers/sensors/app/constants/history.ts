import type { SensorSemanticKey } from '../types/sensors'

// Mirrors the backend's `SensorHistoryPagination.page_size`.
export const HISTORY_PAGE_SIZE = 20

// Mirrors the backend's `HISTORY_MAX_RANGE_DAYS`; a wider span is a 400.
export const HISTORY_MAX_RANGE_DAYS = 90

// Shared by the chart and by the `<ClientOnly>` fallback that stands in for it:
// a fallback of a different height is exactly the hydration jump it exists to
// prevent. Keep the class and the pixel value in step (`h-60` = 240px).
export const CHART_HEIGHT_CLASS = 'h-60'
export const CHART_HEIGHT = 240

export const CHART_MARGIN = { top: 8, right: 16, bottom: 8, left: 8 }

// A `VisLine` through fewer than this many points draws nothing visible.
export const SPARSE_POINT_THRESHOLD = 3

// Cheap guard against a pathological bucket grid: the backend derives
// `bucket_seconds` from the same range, so a real response never gets close.
export const MAX_CHART_BUCKETS = 400

export const VARIABLE_ICONS: Record<SensorSemanticKey, string> = {
  air_temperature: 'i-lucide-thermometer',
  relative_humidity: 'i-lucide-droplets',
  soil_moisture: 'i-lucide-sprout',
  solar_radiation: 'i-lucide-sun',
  other: 'i-lucide-gauge',
}

// Chart series colours, one selected step per mode — never an automatic flip of
// the light value, which lands outside the dark lightness band.
//
// These are decorative: no chart ever plots two variables in the same axes, and
// each figure carries its own title and unit, so identity never rests on hue
// (1.4.1). Validated as an ordered set against both surfaces — lightness band,
// chroma floor, CVD and normal-vision separation of adjacent slots, and ≥3:1
// contrast on the dark surface. The two light steps below 3:1 ride the relief
// rule: every figure has a visible label and the Table view is the full textual
// alternative.
export const VARIABLE_COLORS: Record<
  SensorSemanticKey,
  { light: string; dark: string }
> = {
  air_temperature: { light: '#eb6834', dark: '#d95926' },
  relative_humidity: { light: '#2a78d6', dark: '#3987e5' },
  soil_moisture: { light: '#1baf7a', dark: '#199e70' },
  solar_radiation: { light: '#eda100', dark: '#c98500' },
  other: { light: '#4a3aa7', dark: '#9085e9' },
}
