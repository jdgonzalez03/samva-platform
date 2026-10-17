/** GeoJSON (RFC 7946) coordinates are `[longitude, latitude]` — the reverse of Leaflet's LatLng. */
export interface GeoJSONPolygon {
  type: 'Polygon'
  coordinates: [number, number][][]
}

export interface GeoJSONPoint {
  type: 'Point'
  coordinates: [number, number]
}

export interface Farm {
  id: number
  name: string
  address: string
  location: GeoJSONPoint | null
  boundary: GeoJSONPolygon | null
  created_at: string
}

export interface Plot {
  id: number
  name: string
  description: string
  geometry: GeoJSONPolygon | null
  centroid: GeoJSONPoint | null
  /**
   * Backend-derived anchor guaranteed to lie inside `geometry` (`null` exactly
   * when `geometry` is). A centroid — and a bounding-box centre — falls outside
   * a concave polygon (an L, a U, a crescent), so neither may anchor anything
   * that has to sit on the plot.
   */
  label_point: GeoJSONPoint | null
  // DRF serializes DecimalField as a string.
  area_hectares: string | null
  sensor_count: number
}

export interface PlotDetail extends Plot {
  farm: { id: number; name: string }
  created_at: string
  updated_at: string
}

export type WeatherStationStatus =
  'online' | 'stale' | 'never_seen' | 'inactive'

export interface WeatherStationLatest {
  variable_id: number
  semantic_key: string
  name: string
  unit: string
  value: number
  recorded_at: string
}

export interface WeatherStationSparkline {
  semantic_key: string
  unit: string
  // Hourly averages over the last 24 h; empty hours are absent.
  points: { t: string; value: number }[]
}

export interface WeatherStation {
  id: number
  farm_id: number
  name: string
  provider: string
  is_active: boolean
  status: WeatherStationStatus
  last_reading_at: string | null
  // Only variables with data: one without any reading is absent, never null.
  latest: WeatherStationLatest[]
  // `null` when the station measures no air temperature.
  sparkline: WeatherStationSparkline | null
}

export type ConditionLevel = 'low' | 'medium' | 'high'

export interface PlotCondition {
  semantic_key: string
  name: string
  unit: string
  value: number
  recorded_at: string
  // Latest value minus the reading from ~24 h earlier; null without one.
  change_24h: number | null
  // Fuzzy-model term the reading belongs to most; null for variables the
  // irrigation model does not use.
  level: ConditionLevel | null
  level_degrees: Record<ConditionLevel, number> | null
}

export interface PlotSeriesPoint {
  t: string
  value: number
  sample_count: number
}

export interface PlotSeries {
  variable_id: number
  semantic_key: string
  name: string
  unit: string
  bucket_seconds: number
  points: PlotSeriesPoint[]
}

export type PlotSensorStatus = 'online' | 'offline' | 'never_seen' | 'inactive'

export interface PlotSensor {
  id: number
  name: string
  serial_number: string
  is_active: boolean
  installed_at: string | null
  last_seen_at: string | null
  status: PlotSensorStatus
  variables: { semantic_key: string; name: string; unit: string }[]
}

export interface PlotIrrigation {
  id: number
  irrigation_time_minutes: number
  output_label: string
  avg_period_hours: number
  requested_at: string
}

export interface PlotOverview {
  generated_at: string
  conditions: PlotCondition[]
  // Hourly averages over the last 7 days; empty hours are absent.
  series: PlotSeries[]
  sensors: PlotSensor[]
  irrigation: PlotIrrigation | null
}

export interface FarmPlotSummary {
  id: number
  name: string
  latest_reading_at: string | null
  conditions: PlotCondition[]
  // Hourly averages per variable over the last 7 days.
  series: { semantic_key: string; points: { t: string; value: number }[] }[]
  irrigation: PlotIrrigation | null
}

export interface FarmOverview {
  generated_at: string
  // Each variable averaged over the plots that measure it.
  conditions: PlotCondition[]
  series: PlotSeries[]
  plots: FarmPlotSummary[]
  sensors: (PlotSensor & { plot_id: number; plot_name: string })[]
}

// A row of "Mis lotes": one plot of any of the user's farms.
export interface PlotSummary {
  id: number
  name: string
  description: string
  area_hectares: string | null
  sensor_count: number
  has_geometry: boolean
  farm: { id: number; name: string }
  latest_reading_at: string | null
  conditions: PlotCondition[]
  irrigation: PlotIrrigation | null
}
