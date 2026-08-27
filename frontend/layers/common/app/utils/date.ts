// Formats an ISO date as "month year" in the given locale (e.g. "agosto de 2026").
export const formatMonthYear = (iso: string, locale: string): string =>
  new Intl.DateTimeFormat(locale, { year: 'numeric', month: 'long' }).format(
    new Date(iso),
  )

const MS_PER_SECOND = 1_000
const MS_PER_MINUTE = 60 * MS_PER_SECOND
const MS_PER_HOUR = 60 * MS_PER_MINUTE
const MS_PER_DAY = 24 * MS_PER_HOUR

// Each unit applies while the elapsed time is below `upTo`; days cover the rest.
const RELATIVE_UNITS: {
  unit: Intl.RelativeTimeFormatUnit
  ms: number
  upTo: number
}[] = [
  { unit: 'second', ms: MS_PER_SECOND, upTo: MS_PER_MINUTE },
  { unit: 'minute', ms: MS_PER_MINUTE, upTo: MS_PER_HOUR },
  { unit: 'hour', ms: MS_PER_HOUR, upTo: MS_PER_DAY },
  { unit: 'day', ms: MS_PER_DAY, upTo: Number.POSITIVE_INFINITY },
]

const pickUnit = (elapsedMs: number) =>
  RELATIVE_UNITS.find(({ upTo }) => Math.abs(elapsedMs) < upTo) ??
  RELATIVE_UNITS[RELATIVE_UNITS.length - 1]!

// Formats an ISO instant as an age relative to `now` (e.g. "hace 3 minutos").
// `now` is a parameter rather than `Date.now()` so the caller can drive the age
// and any threshold derived from it off the same instant, keeping them in sync.
export const formatRelativeTime = (
  iso: string,
  locale: string,
  now: number,
): string => {
  const recordedAt = Date.parse(iso)
  if (Number.isNaN(recordedAt)) return ''

  const elapsedMs = recordedAt - now
  const { unit, ms } = pickUnit(elapsedMs)
  const amount = Math.round(elapsedMs / ms)

  return new Intl.RelativeTimeFormat(locale, { numeric: 'auto' }).format(
    amount,
    unit,
  )
}
