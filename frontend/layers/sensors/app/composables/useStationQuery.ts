import { useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'
import { SensorsQueryKey } from '../constants/query-keys'
import type { WeatherStationDetail } from '../types/sensors'
import { sensorsApi } from '../utils/api/sensors'
import { pollUnlessNotFound, retryUnlessNotFound } from '#api/errors'
import { hasTokens } from '#api/tokens'

export const stationQueryOptions = (stationId: Ref<number | null>) => ({
  queryKey: [SensorsQueryKey.ROOT, SensorsQueryKey.STATION, stationId] as const,
  queryFn: (): Promise<WeatherStationDetail> =>
    sensorsApi.getStation(stationId.value!),
})

// An unknown station and another farmer's station are the same 404, and both
// are final: no retry, and the poll stops there.
export const useStationQuery = (stationId: Ref<number | null>) =>
  useQuery({
    ...stationQueryOptions(stationId),
    enabled: () => hasTokens() && stationId.value !== null,
    retry: retryUnlessNotFound,
    refetchInterval: pollUnlessNotFound(LIVE_REFRESH_INTERVAL_MS),
  })
