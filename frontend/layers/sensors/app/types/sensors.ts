import type { WeatherStation } from '../../../farm/app/types/farm'

/**
 * The choices `?variable=` accepts. `semantic_key` is a *presentation* key: it
 * is not unique in the backend's variable table, so it can never identify a
 * series — `variable_id` does that.
 */
export type SensorSemanticKey =
  | 'soil_moisture'
  | 'air_temperature'
  | 'solar_radiation'
  | 'relative_humidity'
  | 'leaf_temperature'
  | 'soil_temperature'
  | 'soil_water_tension'
  | 'co2'
  | 'battery_voltage'
  | 'battery_current'
  | 'solar_panel_voltage'
  | 'solar_panel_current'
  | 'other'

export interface HistoryVariable {
  variable_id: number
  semantic_key: SensorSemanticKey
  name: string
  unit: string
}

export interface SensorReading {
  id: number
  /** ISO 8601 UTC, always ending in `Z`. */
  recorded_at: string
  plot_id: number
  plot_name: string
  sensor_id: number
  sensor_name: string
  variable_id: number
  semantic_key: SensorSemanticKey
  variable_name: string
  /** A JSON number, not a DRF decimal string. */
  value: number
  unit: string
}

/** `next`/`previous` are deliberately absent — see the feature contract. */
export interface ReadingsPage {
  count: number
  page: number
  page_size: number
  results: SensorReading[]
}

export interface SeriesPoint {
  /** ISO 8601 UTC, start of the bucket. */
  t: string
  /** Bucket average, not a raw reading. */
  value: number
  sample_count: number
}

export interface HistorySeries {
  variable_id: number
  semantic_key: SensorSemanticKey
  name: string
  unit: string
  /**
   * Bucket width the backend used. Empty buckets are omitted from `points`, so
   * the client needs this to know where the holes are and break the line.
   */
  bucket_seconds: number
  points: SeriesPoint[]
}

// The series plus the window they were requested for, which a live poll slides.
export interface HistorySeriesResult {
  date_from: string
  date_to: string
  series: HistorySeries[]
}

export interface PlotAverage {
  plot_id: number
  plot_name: string
  variable_id: number
  semantic_key: SensorSemanticKey
  variable_name: string
  unit: string
  average: number
  sample_count: number
}

/**
 * The query params every history endpoint shares. `plot`/`variable` are absent
 * (never `null`) when the filter is "all", which is what the backend reads as
 * unfiltered.
 */
export interface HistoryQueryFilters {
  plot?: number
  variable?: SensorSemanticKey
  date_from: string
  date_to: string
}

export type ExportFormat = 'csv' | 'json'

/** The 400 body the export endpoints return when the row cap is exceeded. */
export interface ExportErrorPayload {
  detail?: string
  code?: string
  count?: number
  limit?: number
}

export type FieldSensorStatus = 'online' | 'offline' | 'never_seen' | 'inactive'

export interface FieldSensorVariable {
  semantic_key: SensorSemanticKey
  name: string
  unit: string
}

export interface FieldSensor {
  id: number
  name: string
  // Empty when the sensor has not been registered with its hardware serial yet.
  serial_number: string
  plot_id: number
  plot_name: string
  is_active: boolean
  installed_at: string | null
  last_seen_at: string | null
  status: FieldSensorStatus
  variables: FieldSensorVariable[]
}

export interface WeatherStationVariable {
  variable_id: number
  semantic_key: SensorSemanticKey
  name: string
  unit: string
}

export interface WeatherStationDetail extends WeatherStation {
  variables: WeatherStationVariable[]
}

// A station reading: the history row minus the plot and sensor it came from.
export type StationReading = Omit<
  SensorReading,
  'plot_id' | 'plot_name' | 'sensor_id' | 'sensor_name'
>

export interface StationReadingsPage {
  count: number
  page: number
  page_size: number
  results: StationReading[]
}

// The station endpoints take the history range without a plot.
export type StationQueryFilters = Omit<HistoryQueryFilters, 'plot'>
