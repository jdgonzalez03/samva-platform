import type { ExportErrorPayload, ExportFormat } from '../types/sensors'

const slugify = (value: string): string =>
  value
    .normalize('NFD')
    // Strip the combining marks NFD just split off, so "Tesoro" survives and
    // the accent does not become a hyphen.
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'finca'

// `YYYYMMDD` of the **local** calendar day an instant falls on. Formatting in
// UTC would name a Bogotá evening after the following day, so the file would
// disagree with the days the user picked.
const compactLocalDate = (ms: number): string => {
  const date = new Date(ms)
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}${month}${day}`
}

// Built client-side on purpose: reading the server's `Content-Disposition`
// would need `Access-Control-Expose-Headers` in the cross-origin dev topology.
//
// `date_to` is the exclusive end of the window, so the name is taken from the
// instant just before it — otherwise a range ending at midnight would be named
// after a day it does not contain.
export const buildExportFilename = (
  farmName: string,
  fileFormat: ExportFormat,
  dateFrom: string,
  dateTo: string,
): string => {
  const startMs = Date.parse(dateFrom)
  const endMs = Date.parse(dateTo)
  if (Number.isNaN(startMs) || Number.isNaN(endMs)) {
    return `historial-sensores-${slugify(farmName)}.${fileFormat}`
  }

  return `historial-sensores-${slugify(farmName)}-${compactLocalDate(startMs)}_${compactLocalDate(endMs - 1)}.${fileFormat}`
}

const readPayload = (raw: unknown): ExportErrorPayload | null => {
  if (typeof raw === 'string') {
    try {
      return JSON.parse(raw) as ExportErrorPayload
    } catch {
      return null
    }
  }
  return raw && typeof raw === 'object' ? (raw as ExportErrorPayload) : null
}

// With `responseType: 'blob'`, ofetch hands back the *error* body as a Blob
// too, so the row-cap 400 has to be read out of it rather than off `error.data`
// as parsed JSON.
export const parseExportError = async (
  error: unknown,
): Promise<ExportErrorPayload | null> => {
  const data = (error as { data?: unknown } | null)?.data
  if (data instanceof Blob) return readPayload(await data.text())
  return readPayload(data)
}
