/** Formats an ISO date as "month year" in the given locale (e.g. "agosto de 2026"). */
export const formatMonthYear = (iso: string, locale: string): string =>
  new Intl.DateTimeFormat(locale, { year: 'numeric', month: 'long' }).format(
    new Date(iso),
  )
