// The map and its `<ClientOnly>` placeholder must use the same height. If the
// placeholder is a different size, the page "jumps" when the map loads.
// Do not use `100vh`: on mobile, the browser bars make it taller than the screen.
export const MAP_HEIGHT_CLASS = 'h-[60vh] min-h-80 lg:h-[520px]'

export type BasemapId = 'street' | 'satellite'

export interface BasemapDefinition {
  id: BasemapId
  url: string
  attribution: string
  maxZoom: number
}

// The license of both map providers requires showing this attribution text.
export const BASEMAPS: Record<BasemapId, BasemapDefinition> = {
  street: {
    id: 'street',
    url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
    attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
    maxZoom: 20,
  },
  satellite: {
    id: 'satellite',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution:
      'Tiles &copy; Esri — Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
    maxZoom: 19,
  },
}

export const DEFAULT_BASEMAP: BasemapId = 'street'

// One line colour cannot have enough contrast (3:1) on both the light street map
// and the satellite photos. So every shape is drawn two times: a dark, wider
// line below (the "casing") and a light, thinner line on top (the "core").
// Whatever the map looks like, one of the two lines is visible, and the two
// lines always contrast with each other.
export const MAP_PANES = {
  casing: { name: 'casing', zIndex: 400 },
  core: { name: 'core', zIndex: 410 },
  labels: { name: 'labels', zIndex: 420 },
} as const

export const CASING_COLOR = '#0a0a0a'
export const PLOT_STROKE_COLOR = '#f8fafc'
// Each plot gets a different colour to help tell them apart, but colour is never
// the only way to identify a plot (see the pins and name labels).
export const PLOT_FILL_COLORS = [
  '#38bdf8',
  '#a3e635',
  '#f472b6',
  '#fbbf24',
  '#c084fc',
  '#2dd4bf',
]
export const BOUNDARY_STROKE_COLOR = '#fde68a'
// The farm boundary uses a dashed line, not only a different colour, so it is
// still different from the plots when the map is seen in greyscale.
export const BOUNDARY_DASH_ARRAY = '10 6'

export const PLOT_CORE_WEIGHT = 3
export const PLOT_ACTIVE_WEIGHT = 5
export const PLOT_CASING_WEIGHT = 7

// The keyboard focus ring uses the same casing/core idea as the shapes: a bright
// line with a dark line on both sides always has enough contrast (3:1), no
// matter what the map looks like. A CSS `outline` cannot do this, because
// `filter: drop-shadow` does not apply to the outline of an SVG element; the
// outline alone only reaches 1.19:1 on the street map.
export const PLOT_FOCUS_COLOR = '#facc15'
export const PLOT_FOCUS_WEIGHT = 5
export const PLOT_FOCUS_CASING_WEIGHT = 13

export const FALLBACK_LOCATION_ZOOM = 14
export const FIT_PADDING: [number, number] = [24, 24]
export const INFO_CARD_CLOSE_DELAY_MS = 150

// A "teardrop" pin like the one in Google Maps. It is drawn in a 24×36 box with
// the sharp tip at the bottom edge, so the marker points to the exact location
// with its tip, not with its centre.
export const PIN_PATH =
  'M12 1C6.201 1 1.5 5.701 1.5 11.5c0 7.875 10.5 23.5 10.5 23.5s10.5-15.625 10.5-23.5C22.5 5.701 17.799 1 12 1z'
export const PIN_WIDTH = 20
export const PIN_HEIGHT = 30
