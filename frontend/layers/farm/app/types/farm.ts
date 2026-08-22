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

export interface WeatherReading {
  value: number
  unit: string
  recorded_at: string
}

export type WeatherSemanticKey = 'air_temperature' | 'solar_radiation'

/**
 * Absence is the only "no data" signal: a key with no usable reading is omitted,
 * never sent as `null` or `0`. Keys the UI does not render are ignored.
 */
export type FarmWeather = Partial<Record<string, WeatherReading>>
