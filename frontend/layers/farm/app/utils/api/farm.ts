import { fetcher } from '#api/fetcher'
import type { Farm, Plot } from '../../types/farm'

export const farmApi = {
  getFarms: () => fetcher.get<Farm[]>('farm/farms/'),
  getPlots: (farmId: number) =>
    fetcher.get<Plot[]>(`farm/farms/${farmId}/plots/`),
}
