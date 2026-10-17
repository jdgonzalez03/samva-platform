import type { HistoryRangePreset } from './history-filters'

// A station page offers the presets only: every one ends at now, so the page
// is always live.
export type StationRangePreset = Exclude<HistoryRangePreset, 'custom'>

export const STATION_RANGE_PRESETS: StationRangePreset[] = [
  '1h',
  '6h',
  '24h',
  '7d',
  '30d',
]

export const DEFAULT_STATION_RANGE: StationRangePreset = '24h'

export const parseStationRange = (value: unknown): StationRangePreset | null =>
  STATION_RANGE_PRESETS.includes(value as StationRangePreset)
    ? (value as StationRangePreset)
    : null

// A non-numeric or non-positive id is never a station, so it renders the
// not-found state without a request.
export const parseStationId = (value: unknown): number | null => {
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
}
