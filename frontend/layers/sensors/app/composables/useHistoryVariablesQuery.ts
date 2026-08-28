import { useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'
import { SensorsQueryKey } from '../constants/query-keys'
import type { HistoryVariable } from '../types/sensors'
import { sensorsApi } from '../utils/api/sensors'
import { uniqueBySemanticKey } from '../utils/history-filters'
import { hasTokens } from '#api/tokens'

// Farm and plot ride in the key: Vue Query unwraps and tracks the refs, so
// narrowing to a plot refetches the variable list with no watcher.
export const historyVariablesQueryOptions = (
  farmId: Ref<number | null>,
  plotId: Ref<number | null>,
) => ({
  queryKey: [
    SensorsQueryKey.ROOT,
    SensorsQueryKey.HISTORY,
    SensorsQueryKey.VARIABLES,
    farmId,
    plotId,
  ] as const,
  queryFn: (): Promise<HistoryVariable[]> =>
    sensorsApi.getHistoryVariables(farmId.value!, {
      plot: plotId.value ?? undefined,
    }),
})

// `isReady` holds the request back while a plot id from the URL is still
// unconfirmed: asking with an id the farm does not own answers 404, and asking
// without it spends a round trip the confirmed id would immediately redo.
export const useHistoryVariablesQuery = (
  farmId: Ref<number | null>,
  plotId: Ref<number | null>,
  isReady: Ref<boolean>,
) =>
  useQuery({
    ...historyVariablesQueryOptions(farmId, plotId),
    enabled: () => hasTokens() && farmId.value !== null && isReady.value,
    select: uniqueBySemanticKey,
  })
