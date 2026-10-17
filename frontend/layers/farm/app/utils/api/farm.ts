import { fetcher } from '#api/fetcher'
import type {
  Farm,
  FarmOverview,
  Plot,
  PlotDetail,
  PlotOverview,
  PlotSummary,
  WeatherStation,
} from '../../types/farm'

export const farmApi = {
  getFarms: () => fetcher.get<Farm[]>('farm/farms/'),
  getPlots: (farmId: number) =>
    fetcher.get<Plot[]>(`farm/farms/${farmId}/plots/`),
  getPlotSummaries: () => fetcher.get<PlotSummary[]>('farm/plots/'),
  getPlot: (plotId: number) => fetcher.get<PlotDetail>(`farm/plots/${plotId}/`),
  getPlotOverview: (plotId: number) =>
    fetcher.get<PlotOverview>(`farm/plots/${plotId}/overview/`),
  getFarmOverview: (farmId: number) =>
    fetcher.get<FarmOverview>(`farm/farms/${farmId}/overview/`),
  // Served by the sensors app; it lives here because the home dashboard and
  // the sensors layer both render the farm's station cards.
  getStations: (farmId: number) =>
    fetcher.get<WeatherStation[]>(`sensors/farms/${farmId}/stations/`),
}
