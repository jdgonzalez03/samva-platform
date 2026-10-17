import { fetcher, type QueryParams } from '#api/fetcher'
import type {
  ExportFormat,
  FieldSensor,
  HistorySeries,
  HistoryVariable,
  PlotAverage,
  ReadingsPage,
  StationReadingsPage,
  WeatherStationDetail,
} from '../../types/sensors'

export const sensorsApi = {
  getFarmSensors: (farmId: number) =>
    fetcher.get<FieldSensor[]>(`sensors/farms/${farmId}/sensors/`),
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
  getStation: (stationId: number) =>
    fetcher.get<WeatherStationDetail>(`sensors/stations/${stationId}/`),
  getStationSeries: (stationId: number, query?: QueryParams) =>
    fetcher.get<HistorySeries[]>(
      `sensors/stations/${stationId}/series/`,
      query,
    ),
  getStationReadings: (stationId: number, query?: QueryParams) =>
    fetcher.get<StationReadingsPage>(
      `sensors/stations/${stationId}/readings/`,
      query,
    ),
  getStationExport: (
    stationId: number,
    fileFormat: ExportFormat,
    query?: QueryParams,
  ) =>
    fetcher.getBlob(
      `sensors/stations/${stationId}/export/${fileFormat}/`,
      query,
    ),
}
