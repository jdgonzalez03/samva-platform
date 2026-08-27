import type { Feature, FeatureCollection, Point, Polygon } from 'geojson'
import type { Farm, GeoJSONPolygon, Plot } from '../../../farm/app/types/farm'

export interface PlotFeatureProperties {
  plotId: number
  name: string
  description: string
  sensorCount: number
  colorIndex: number
}

export type PlotFeature = Feature<Polygon, PlotFeatureProperties>
export type PlotLabelFeature = Feature<Point, PlotFeatureProperties>

// A plot the backend drew a polygon for; only these reach the map.
export type MappedPlot = Plot & { geometry: GeoJSONPolygon }

const hasGeometry = (plot: Plot): plot is MappedPlot => plot.geometry !== null

export const getMappedPlots = (plots: Plot[]): MappedPlot[] =>
  plots.filter(hasGeometry)

export const getUnmappedPlots = (plots: Plot[]): Plot[] =>
  plots.filter((plot) => !hasGeometry(plot))

// `colorIndex` counts mapped plots only, so a plot's pin and shape share a hue.
const toPlotFeatureProperties = (
  plot: MappedPlot,
  index: number,
): PlotFeatureProperties => ({
  plotId: plot.id,
  name: plot.name,
  description: plot.description,
  sensorCount: plot.sensor_count,
  colorIndex: index,
})

// The backend's GeoJSON passes straight through so `[lng, lat]` reaches
// `L.geoJSON()` in the order it expects. Plots without geometry are dropped here
// and surfaced by `getUnmappedPlots` instead.
export const toPlotFeatureCollection = (
  plots: Plot[],
): FeatureCollection<Polygon, PlotFeatureProperties> => ({
  type: 'FeatureCollection',
  features: getMappedPlots(plots).map((plot, index): PlotFeature => ({
    type: 'Feature',
    geometry: plot.geometry,
    properties: toPlotFeatureProperties(plot, index),
  })),
})

// Pins and name labels anchor on `label_point`, the only point guaranteed to lie
// inside the shape (see `Plot.label_point`). A mapped plot without one gets no
// pin and no label rather than a client-side guess that may fall outside it.
export const toPlotLabelFeatureCollection = (
  plots: Plot[],
): FeatureCollection<Point, PlotFeatureProperties> => ({
  type: 'FeatureCollection',
  features: getMappedPlots(plots).flatMap((plot, index): PlotLabelFeature[] =>
    plot.label_point
      ? [
          {
            type: 'Feature',
            geometry: plot.label_point,
            properties: toPlotFeatureProperties(plot, index),
          },
        ]
      : [],
  ),
})

// Without one of these the map has nothing to centre on and must not be drawn.
export const hasMapTarget = (farm: Farm, plots: Plot[]): boolean =>
  farm.boundary !== null ||
  farm.location !== null ||
  getMappedPlots(plots).length > 0
