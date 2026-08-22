import { fetcher } from '#api/fetcher'
import type { Farm, FarmWeather, Plot, PlotDetail } from '../../types/farm'

export const farmApi = {
  getFarms: () => fetcher.get<Farm[]>('farm/farms/'),
  getPlots: (farmId: number) =>
    fetcher.get<Plot[]>(`farm/farms/${farmId}/plots/`),
  getPlot: (plotId: number) => fetcher.get<PlotDetail>(`farm/plots/${plotId}/`),
  getWeather: (farmId: number) =>
    fetcher.get<FarmWeather>(`farm/farms/${farmId}/weather/`),
}
