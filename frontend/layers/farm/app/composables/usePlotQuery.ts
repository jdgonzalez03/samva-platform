import { useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'
import { FarmQueryKey } from '../constants/query-keys'
import { farmApi } from '../utils/api/farm'
import { retryUnlessNotFound } from '#api/errors'
import { hasTokens } from '#api/tokens'

export const plotQueryOptions = (plotId: Ref<number | null>) => ({
  queryKey: [FarmQueryKey.ROOT, FarmQueryKey.PLOT, plotId] as const,
  queryFn: () => farmApi.getPlot(plotId.value!),
})

export const usePlotQuery = (plotId: Ref<number | null>) =>
  useQuery({
    ...plotQueryOptions(plotId),
    enabled: () => hasTokens() && plotId.value !== null,
    retry: retryUnlessNotFound,
  })
