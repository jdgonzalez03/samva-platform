import { useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'
import { SensorsQueryKey } from '../constants/query-keys'
import type { HistorySeriesResult, StationQueryFilters } from '../types/sensors'
import { sensorsApi } from '../utils/api/sensors'
import {
  historyCacheKey,
  historyRequestFilters,
} from '../utils/history-filters'
import { hasTokens } from '#api/tokens'

export const stationSeriesQueryOptions = (
  stationId: Ref<number | null>,
  filters: Ref<StationQueryFilters>,
  live: Ref<boolean>,
) => ({
  queryKey: [
    SensorsQueryKey.ROOT,
    SensorsQueryKey.STATION,
    stationId,
    SensorsQueryKey.SERIES,
    computed(() => historyCacheKey(filters.value, live.value)),
  ] as const,
  // The window travels with the data: a live poll slides it, and the chart's
  // time axis must match the request the points came from.
  queryFn: async (): Promise<HistorySeriesResult> => {
    const request = historyRequestFilters(filters.value, live.value, Date.now())
    const series = await sensorsApi.getStationSeries(stationId.value!, {
      ...request,
    })
    return { date_from: request.date_from, date_to: request.date_to, series }
  },
})

export const useStationSeriesQuery = (
  stationId: Ref<number | null>,
  filters: Ref<StationQueryFilters>,
  live: Ref<boolean>,
  isActive: Ref<boolean>,
) =>
  useQuery({
    ...stationSeriesQueryOptions(stationId, filters, live),
    enabled: () => hasTokens() && stationId.value !== null && isActive.value,
    refetchInterval: computed(() =>
      live.value ? LIVE_REFRESH_INTERVAL_MS : false,
    ),
  })
