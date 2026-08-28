import { HISTORY_MAX_RANGE_DAYS } from '../constants/history'
import type { HistoryVariable, SensorSemanticKey } from '../types/sensors'

// ---------------------------------------------------------------------------
// Options the user can choose in the history filters
// ---------------------------------------------------------------------------

export type HistoryView = 'chart' | 'table'

export const HISTORY_VIEWS: HistoryView[] = ['chart', 'table']

export const DEFAULT_HISTORY_VIEW: HistoryView = 'chart'

export type HistoryRangePreset = '24h' | '7d' | '30d' | 'custom'

// A preset that is not 'custom' (it has a fixed number of days).
type FixedRangePreset = Exclude<HistoryRangePreset, 'custom'>

export const HISTORY_RANGE_PRESETS: HistoryRangePreset[] = [
  '24h',
  '7d',
  '30d',
  'custom',
]

export const DEFAULT_RANGE_PRESET: FixedRangePreset = '7d'

// How many days each preset looks back from "now".
const PRESET_DAYS: Record<FixedRangePreset, number> = {
  '24h': 1,
  '7d': 7,
  '30d': 30,
}

export const SENSOR_SEMANTIC_KEYS: SensorSemanticKey[] = [
  'soil_moisture',
  'air_temperature',
  'solar_radiation',
  'relative_humidity',
  'other',
]

// One day in milliseconds (24 * 60 * 60 * 1000).
const DAY_MS = 86_400_000

// localStorage key where we remember the last view the user chose.
const HISTORY_VIEW_KEY = 'sensorsHistoryView'

// Shape of a calendar day: four digits, dash, two digits, dash, two digits.
const CALENDAR_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/

// ---------------------------------------------------------------------------
// Parsers: turn an unknown value (usually from the URL) into a safe value
// Each one returns `null` when the value is not valid.
// ---------------------------------------------------------------------------

export const parseHistoryView = (value: unknown): HistoryView | null =>
  HISTORY_VIEWS.includes(value as HistoryView) ? (value as HistoryView) : null

export const parseRangePreset = (value: unknown): HistoryRangePreset | null =>
  HISTORY_RANGE_PRESETS.includes(value as HistoryRangePreset)
    ? (value as HistoryRangePreset)
    : null

export const parseVariableKey = (value: unknown): SensorSemanticKey | null =>
  SENSOR_SEMANTIC_KEYS.includes(value as SensorSemanticKey)
    ? (value as SensorSemanticKey)
    : null

// Accepts "3" or 3, but not "0", "-1", "1.5" or "abc".
const parsePositiveInteger = (value: unknown): number | null => {
  if (typeof value !== 'string' && typeof value !== 'number') return null
  const parsed = Number(value)
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null
}

export const parsePlotId = (value: unknown): number | null =>
  parsePositiveInteger(value)

// Invalid page numbers become page 1. A page bigger than the last page is
// fixed by the caller, because only the caller knows the total `count`.
export const parsePageNumber = (value: unknown): number =>
  parsePositiveInteger(value) ?? 1

// Splits "2026-08-22" into [2026, 8, 22].
// Only call this with a string that matches CALENDAR_DATE_PATTERN.
const splitCalendarDate = (
  calendarDate: string,
): [year: number, month: number, day: number] => {
  const [year, month, day] = calendarDate.split('-').map(Number)
  return [year as number, month as number, day as number]
}

// Accepts only a real calendar day in "YYYY-MM-DD" format.
//
// Checking the shape is not enough: "2026-02-31" has the right shape but the
// day does not exist. `new Date()` would silently change it to March 3rd.
// To detect this, we build a Date and check that the year, month and day did
// not change.
export const parseCalendarDate = (value: unknown): string | null => {
  if (typeof value !== 'string' || !CALENDAR_DATE_PATTERN.test(value))
    return null

  const [year, month, day] = splitCalendarDate(value)
  const probe = new Date(year, month - 1, day)
  const isRealDate =
    probe.getFullYear() === year &&
    probe.getMonth() === month - 1 &&
    probe.getDate() === day
  return isRealDate ? value : null
}

// Returns midnight (00:00) of a calendar day in the user's own timezone.
//
// Important: we use `new Date(year, month, day)` on purpose, because it works
// in local time. `new Date("2026-08-22")` would read the string as UTC, and in
// Bogotá (UTC-5) "22 de agosto" would start at 7 PM the day before. That is a
// classic bug here, so do not change this.
const localDayStart = (calendarDate: string): Date => {
  const [year, month, day] = splitCalendarDate(calendarDate)
  return new Date(year, month - 1, day)
}

// ---------------------------------------------------------------------------
// Date range: from URL state to the two UTC dates the API needs
// ---------------------------------------------------------------------------

export type RangeIssue = 'invalid' | 'tooLong' | null

export interface ResolvedRange {
  date_from: string
  date_to: string
  // Not null when the custom dates could not be used and we fell back to the
  // default preset. Tells the UI which message to show.
  issue: RangeIssue
}

// Range for a fixed preset: from N days ago until now.
const presetRange = (
  preset: FixedRangePreset,
  anchorMs: number,
): ResolvedRange => {
  const days = PRESET_DAYS[preset]
  return {
    date_from: new Date(anchorMs - days * DAY_MS).toISOString(),
    date_to: new Date(anchorMs).toISOString(),
    issue: null,
  }
}

// Range used when the custom dates cannot be used.
const fallbackRange = (anchorMs: number, issue: RangeIssue): ResolvedRange => ({
  ...presetRange(DEFAULT_RANGE_PRESET, anchorMs),
  issue,
})

// Turns the range chosen by the user into `date_from` and `date_to` for the API.
//
// - For a fixed preset ('24h', '7d', '30d') the range ends at `anchorMs` (now).
// - For 'custom', `from` and `to` are calendar days in the user's local time.
//   The range goes from the start of `from` to the start of the day AFTER `to`.
//   This way the whole `to` day is included, because the backend uses
//   `recorded_at < date_to` (the end is not included).
//
// If the custom dates are missing, wrong, reversed or too far apart, we use
// the default preset instead and say why in `issue`. The user may have edited
// the URL by hand, and a raw 400 error from the API would not help them.
export const resolveRange = (
  preset: HistoryRangePreset,
  from: string | null,
  to: string | null,
  anchorMs: number,
): ResolvedRange => {
  if (preset !== 'custom') return presetRange(preset, anchorMs)

  // 'custom' with no dates yet is normal: the user just opened the date picker.
  // It is not an error, so we do not show any message.
  if (!from || !to) return fallbackRange(anchorMs, null)

  const startMs = localDayStart(from).getTime()
  const endMs = localDayStart(to).getTime() + DAY_MS

  // `to` is before `from`.
  if (endMs <= startMs) return fallbackRange(anchorMs, 'invalid')

  // The range is longer than the backend allows.
  if (endMs - startMs > HISTORY_MAX_RANGE_DAYS * DAY_MS) {
    return fallbackRange(anchorMs, 'tooLong')
  }

  return {
    date_from: new Date(startMs).toISOString(),
    date_to: new Date(endMs).toISOString(),
    issue: null,
  }
}

// ---------------------------------------------------------------------------
// Remember the chosen view (chart / table) in the browser
// Both functions do nothing on the server, where localStorage does not exist.
// ---------------------------------------------------------------------------

export const getStoredHistoryView = (): HistoryView | null => {
  if (!import.meta.client) return null
  return parseHistoryView(localStorage.getItem(HISTORY_VIEW_KEY))
}

export const setStoredHistoryView = (view: HistoryView): void => {
  if (!import.meta.client) return
  localStorage.setItem(HISTORY_VIEW_KEY, view)
}

// `?variable=` filters by semantic key, so two variables sharing one would be
// the same request twice; the first occurrence wins.
export const uniqueBySemanticKey = (
  variables: HistoryVariable[],
): HistoryVariable[] => {
  const seen = new Set<SensorSemanticKey>()
  return variables.filter((variable) => {
    if (seen.has(variable.semantic_key)) return false
    seen.add(variable.semantic_key)
    return true
  })
}
