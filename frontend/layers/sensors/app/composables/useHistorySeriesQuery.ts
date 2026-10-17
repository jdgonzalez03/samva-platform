import { useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'
import { SensorsQueryKey } from '../constants/query-keys'
import type { HistoryQueryFilters, HistorySeriesResult } from '../types/sensors'
import { sensorsApi } from '../utils/api/sensors'
import {
  historyCacheKey,
  historyRequestFilters,
} from '../utils/history-filters'
import { hasTokens } from '#api/tokens'

export const historySeriesQueryOptions = (
  farmId: Ref<number | null>,
  filters: Ref<HistoryQueryFilters>,
  live: Ref<boolean>,
) => ({
  queryKey: [
    SensorsQueryKey.ROOT,
    SensorsQueryKey.HISTORY,
    SensorsQueryKey.SERIES,
    farmId,
    computed(() => historyCacheKey(filters.value, live.value)),
  ] as const,
  // The window travels with the data: a live poll slides it, and the chart's
  // time axis must match the request the points came from.
  queryFn: async (): Promise<HistorySeriesResult> => {
    const request = historyRequestFilters(filters.value, live.value, Date.now())
    const series = await sensorsApi.getHistorySeries(farmId.value!, {
      ...request,
    })
    return { date_from: request.date_from, date_to: request.date_to, series }
  },
})

// The endpoint requires `plot`; without one it answers 400, so the query stays
// disabled and the page renders the plot-averages mode instead.
export const useHistorySeriesQuery = (
  farmId: Ref<number | null>,
  filters: Ref<HistoryQueryFilters>,
  live: Ref<boolean>,
  isActive: Ref<boolean>,
) =>
  useQuery({
    ...historySeriesQueryOptions(farmId, filters, live),
    enabled: () =>
      hasTokens() &&
      farmId.value !== null &&
      filters.value.plot !== undefined &&
      isActive.value,
    refetchInterval: computed(() =>
      live.value ? LIVE_REFRESH_INTERVAL_MS : false,
    ),
  })
