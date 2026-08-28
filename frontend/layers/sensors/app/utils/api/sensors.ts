import { fetcher, type QueryParams } from '#api/fetcher'
import type {
  ExportFormat,
  HistorySeries,
  HistoryVariable,
  PlotAverage,
  ReadingsPage,
} from '../../types/sensors'

export const sensorsApi = {
  getHistoryVariables: (farmId: number, query?: QueryParams) =>
    fetcher.get<HistoryVariable[]>(
      `sensors/farms/${farmId}/history/variables/`,
      query,
    ),
  getHistoryReadings: (farmId: number, query?: QueryParams) =>
    fetcher.get<ReadingsPage>(
      `sensors/farms/${farmId}/history/readings/`,
      query,
    ),
  getHistorySeries: (farmId: number, query?: QueryParams) =>
    fetcher.get<HistorySeries[]>(
      `sensors/farms/${farmId}/history/series/`,
      query,
    ),
  getHistoryPlotAverages: (farmId: number, query?: QueryParams) =>
    fetcher.get<PlotAverage[]>(
      `sensors/farms/${farmId}/history/plot-averages/`,
      query,
    ),
  // Two routes rather than `?format=`: DRF reserves the `format` query param
  // for renderer negotiation and would answer 404 "Invalid format".
  getHistoryExport: (
    farmId: number,
    fileFormat: ExportFormat,
    query?: QueryParams,
  ) =>
    fetcher.getBlob(
      `sensors/farms/${farmId}/history/export/${fileFormat}/`,
      query,
    ),
}
