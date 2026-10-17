import { fetcher, type QueryParams } from '#api/fetcher'
import type {
  IrrigationDefinitions,
  IrrigationPrediction,
  IrrigationPredictionPage,
  PredictionModel,
} from '../../types/predictions'

export const predictionsApi = {
  getModels: () => fetcher.get<PredictionModel[]>('predictions/models/'),
  getIrrigationDefinitions: () =>
    fetcher.get<IrrigationDefinitions>(
      'predictions/fuzzy/irrigation/definitions/',
    ),
  getIrrigationHistory: (plotId: number, query?: QueryParams) =>
    fetcher.get<IrrigationPredictionPage>(
      `predictions/plots/${plotId}/irrigation/`,
      query,
    ),
  createIrrigationPrediction: (plotId: number, hours: number) =>
    fetcher.post<IrrigationPrediction>(
      `predictions/plots/${plotId}/irrigation/`,
      { hours },
    ),
}
