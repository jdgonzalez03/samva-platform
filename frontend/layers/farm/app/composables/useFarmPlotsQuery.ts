import { useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'
import { FarmQueryKey } from '../constants/query-keys'
import { farmApi } from '../utils/api/farm'
import { hasTokens } from '#api/tokens'

// The farm id ref belongs in the key: Vue Query unwraps and tracks it, so
// switching farms refetches without any watcher on the consuming page.
export const farmPlotsQueryOptions = (farmId: Ref<number | null>) => ({
  queryKey: [FarmQueryKey.ROOT, FarmQueryKey.PLOTS, farmId] as const,
  queryFn: () => farmApi.getPlots(farmId.value!),
})

export const useFarmPlotsQuery = (farmId: Ref<number | null>) =>
  useQuery({
    ...farmPlotsQueryOptions(farmId),
    enabled: () => hasTokens() && farmId.value !== null,
  })
