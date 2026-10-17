import { useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'
import { FarmQueryKey } from '../constants/query-keys'
import { farmApi } from '../utils/api/farm'
import { hasTokens } from '#api/tokens'

export const farmStationsQueryOptions = (farmId: Ref<number | null>) => ({
  queryKey: [FarmQueryKey.ROOT, FarmQueryKey.STATIONS, farmId] as const,
  queryFn: () => farmApi.getStations(farmId.value!),
})

export const useFarmStationsQuery = (farmId: Ref<number | null>) =>
  useQuery({
    ...farmStationsQueryOptions(farmId),
    enabled: () => hasTokens() && farmId.value !== null,
    // Status and latest values are computed by the server against its own
    // clock, so they only move when the list is fetched again.
    refetchInterval: LIVE_REFRESH_INTERVAL_MS,
  })
