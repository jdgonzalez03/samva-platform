import { useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'
import { SensorsQueryKey } from '../constants/query-keys'
import type { HistoryQueryFilters, HistorySeries } from '../types/sensors'
import { sensorsApi } from '../utils/api/sensors'
import { hasTokens } from '#api/tokens'

export const historySeriesQueryOptions = (
  farmId: Ref<number | null>,
  filters: Ref<HistoryQueryFilters>,
) => ({
  queryKey: [
    SensorsQueryKey.ROOT,
    SensorsQueryKey.HISTORY,
    SensorsQueryKey.SERIES,
    farmId,
    filters,
  ] as const,
  queryFn: (): Promise<HistorySeries[]> =>
    sensorsApi.getHistorySeries(farmId.value!, { ...filters.value }),
})

// The endpoint requires `plot`; without one it answers 400, so the query stays
// disabled and the page renders the plot-averages mode instead.
export const useHistorySeriesQuery = (
  farmId: Ref<number | null>,
  filters: Ref<HistoryQueryFilters>,
  isActive: Ref<boolean>,
) =>
  useQuery({
    ...historySeriesQueryOptions(farmId, filters),
    enabled: () =>
      hasTokens() &&
      farmId.value !== null &&
      filters.value.plot !== undefined &&
      isActive.value,
  })
