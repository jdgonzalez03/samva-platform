import { useQuery } from '@tanstack/vue-query'
import { PredictionsQueryKey } from '../constants/query-keys'
import { predictionsApi } from '../utils/api/predictions'
import { hasTokens } from '#api/tokens'

export const irrigationDefinitionsQueryOptions = () => ({
  queryKey: [
    PredictionsQueryKey.ROOT,
    PredictionsQueryKey.IRRIGATION,
    PredictionsQueryKey.DEFINITIONS,
  ] as const,
  queryFn: () => predictionsApi.getIrrigationDefinitions(),
})

// The membership functions are part of the model, not of any prediction: they
// only change with a deploy, so the cache never needs to refresh them.
export const useIrrigationDefinitionsQuery = () =>
  useQuery({
    ...irrigationDefinitionsQueryOptions(),
    staleTime: Number.POSITIVE_INFINITY,
    enabled: () => hasTokens(),
  })
