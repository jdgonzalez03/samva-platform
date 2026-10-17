import { useQuery } from '@tanstack/vue-query'
import type { Ref } from 'vue'
import { SensorsQueryKey } from '../constants/query-keys'
import type { FieldSensor } from '../types/sensors'
import { sensorsApi } from '../utils/api/sensors'
import { hasTokens } from '#api/tokens'

export const farmSensorsQueryOptions = (farmId: Ref<number | null>) => ({
  queryKey: [SensorsQueryKey.ROOT, SensorsQueryKey.DEVICES, farmId] as const,
  queryFn: (): Promise<FieldSensor[]> =>
    sensorsApi.getFarmSensors(farmId.value!),
})

export const useFarmSensorsQuery = (farmId: Ref<number | null>) =>
  useQuery({
    ...farmSensorsQueryOptions(farmId),
    enabled: () => hasTokens() && farmId.value !== null,
    // The status is computed by the server against its own clock, so it only
    // moves when the list is fetched again.
    refetchInterval: LIVE_REFRESH_INTERVAL_MS,
  })
