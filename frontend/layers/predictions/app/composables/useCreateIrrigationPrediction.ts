import { useMutation, useQueryClient } from '@tanstack/vue-query'
import { PredictionsQueryKey } from '../constants/query-keys'
import { predictionsApi } from '../utils/api/predictions'

export const useCreateIrrigationPrediction = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ plotId, hours }: { plotId: number; hours: number }) =>
      predictionsApi.createIrrigationPrediction(plotId, hours),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: [PredictionsQueryKey.ROOT] }),
  })
}
