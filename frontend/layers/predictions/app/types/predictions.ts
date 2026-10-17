export interface PredictionModel {
  key: string
  technique: string
  target: string
}

export type IrrigationInput = 'moisture' | 'temperature' | 'radiation'
export type IrrigationVariable = IrrigationInput | 'irrigation_time'
export type IrrigationLabel =
  'nothing' | 'very_little' | 'little' | 'long' | 'very_long'

export interface MembershipFunction {
  shape: 'trap' | 'tri'
  points: number[]
}

export interface FuzzyVariableDefinition {
  unit: string
  bounds: [number, number]
  terms: Record<string, MembershipFunction>
}

export type IrrigationDefinitions = Record<
  IrrigationVariable,
  FuzzyVariableDefinition
>

// Each source's mean over the window, or null when it had no readings.
export interface InputSource {
  field: number | null
  station: number | null
}

export interface IrrigationPrediction {
  id: number
  plot: number
  avg_moisture: number
  avg_temperature: number
  avg_radiation: number
  avg_period_hours: number
  irrigation_time_minutes: number
  output_label: IrrigationLabel
  input_memberships: Record<IrrigationInput, Record<string, number>>
  output_activation: Record<IrrigationLabel, number>
  clipped_inputs: IrrigationInput[]
  // `{}` on predictions made before the breakdown was recorded.
  input_sources: Partial<Record<IrrigationInput, InputSource>>
  requested_at: string
}

export interface IrrigationPredictionPage {
  count: number
  page: number
  page_size: number
  results: IrrigationPrediction[]
}

// Body of the 422 answered when the plot lacks recent readings.
export interface MissingSensorData {
  detail: string
  missing: string[]
}
