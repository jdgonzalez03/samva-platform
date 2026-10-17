import { useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'
import { SensorsQueryKey } from '../constants/query-keys'
import type { HistoryQueryFilters, PlotAverage } from '../types/sensors'
import { sensorsApi } from '../utils/api/sensors'
import {
  historyCacheKey,
  historyRequestFilters,
} from '../utils/history-filters'
import { hasTokens } from '#api/tokens'

export const historyPlotAveragesQueryOptions = (
  farmId: Ref<number | null>,
  filters: Ref<HistoryQueryFilters>,
  live: Ref<boolean>,
) => ({
  queryKey: [
    SensorsQueryKey.ROOT,
    SensorsQueryKey.HISTORY,
    SensorsQueryKey.PLOT_AVERAGES,
    farmId,
    computed(() => historyCacheKey(filters.value, live.value)),
  ] as const,
  queryFn: (): Promise<PlotAverage[]> =>
    sensorsApi.getHistoryPlotAverages(farmId.value!, {
      ...historyRequestFilters(filters.value, live.value, Date.now()),
    }),
})

// The farm-wide mode: only reached when no plot is selected, which is also the
// only time the endpoint's per-plot breakdown says anything the series cannot.
export const useHistoryPlotAveragesQuery = (
  farmId: Ref<number | null>,
  filters: Ref<HistoryQueryFilters>,
  live: Ref<boolean>,
  isActive: Ref<boolean>,
) =>
  useQuery({
    ...historyPlotAveragesQueryOptions(farmId, filters, live),
    enabled: () =>
      hasTokens() &&
      farmId.value !== null &&
      filters.value.plot === undefined &&
      isActive.value,
    refetchInterval: computed(() =>
      live.value ? LIVE_REFRESH_INTERVAL_MS : false,
    ),
  })
