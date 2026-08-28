import { useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'
import { SensorsQueryKey } from '../constants/query-keys'
import type { HistoryQueryFilters, PlotAverage } from '../types/sensors'
import { sensorsApi } from '../utils/api/sensors'
import { hasTokens } from '#api/tokens'

export const historyPlotAveragesQueryOptions = (
  farmId: Ref<number | null>,
  filters: Ref<HistoryQueryFilters>,
) => ({
  queryKey: [
    SensorsQueryKey.ROOT,
    SensorsQueryKey.HISTORY,
    SensorsQueryKey.PLOT_AVERAGES,
    farmId,
    filters,
  ] as const,
  queryFn: (): Promise<PlotAverage[]> =>
    sensorsApi.getHistoryPlotAverages(farmId.value!, { ...filters.value }),
})

// The farm-wide mode: only reached when no plot is selected, which is also the
// only time the endpoint's per-plot breakdown says anything the series cannot.
export const useHistoryPlotAveragesQuery = (
  farmId: Ref<number | null>,
  filters: Ref<HistoryQueryFilters>,
  isActive: Ref<boolean>,
) =>
  useQuery({
    ...historyPlotAveragesQueryOptions(farmId, filters),
    enabled: () =>
      hasTokens() &&
      farmId.value !== null &&
      filters.value.plot === undefined &&
      isActive.value,
  })
