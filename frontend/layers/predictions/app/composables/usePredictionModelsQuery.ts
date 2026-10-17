import { useQuery } from '@tanstack/vue-query'
import { PredictionsQueryKey } from '../constants/query-keys'
import { predictionsApi } from '../utils/api/predictions'
import { hasTokens } from '#api/tokens'

export const predictionModelsQueryOptions = () => ({
  queryKey: [PredictionsQueryKey.ROOT, PredictionsQueryKey.MODELS] as const,
  queryFn: () => predictionsApi.getModels(),
})

export const usePredictionModelsQuery = () =>
  useQuery({
    ...predictionModelsQueryOptions(),
    enabled: () => hasTokens(),
  })
