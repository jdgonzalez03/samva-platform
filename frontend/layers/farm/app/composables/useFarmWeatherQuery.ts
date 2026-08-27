import { useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'
import { FarmQueryKey } from '../constants/query-keys'
import { farmApi } from '../utils/api/farm'
import { hasTokens } from '#api/tokens'

// The farm id belongs in the key: switching farms re-keys and refetches with no
// watcher, and keeps this query independent of the plots query.
export const farmWeatherQueryOptions = (farmId: Ref<number | null>) => ({
  queryKey: [FarmQueryKey.ROOT, FarmQueryKey.WEATHER, farmId] as const,
  queryFn: () => farmApi.getWeather(farmId.value!),
})

export const useFarmWeatherQuery = (farmId: Ref<number | null>) =>
  useQuery({
    ...farmWeatherQueryOptions(farmId),
    enabled: () => hasTokens() && farmId.value !== null,
  })
