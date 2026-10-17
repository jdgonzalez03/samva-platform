import { useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'
import { HISTORY_PAGE_SIZE } from '../constants/predictions'
import { PredictionsQueryKey } from '../constants/query-keys'
import { predictionsApi } from '../utils/api/predictions'
import { hasTokens } from '#api/tokens'

export const irrigationHistoryQueryOptions = (plotId: Ref<number | null>) => ({
  queryKey: [
    PredictionsQueryKey.ROOT,
    PredictionsQueryKey.IRRIGATION,
    PredictionsQueryKey.HISTORY,
    plotId,
  ] as const,
  queryFn: () =>
    predictionsApi.getIrrigationHistory(plotId.value!, {
      page_size: HISTORY_PAGE_SIZE,
    }),
})

export const useIrrigationHistoryQuery = (plotId: Ref<number | null>) =>
  useQuery({
    ...irrigationHistoryQueryOptions(plotId),
    enabled: () => hasTokens() && plotId.value !== null,
  })
