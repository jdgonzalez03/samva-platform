<script setup lang="ts">
import 'leaflet/dist/leaflet.css'
import type * as LeafletNS from 'leaflet'
import type { GeoJSONPolygon } from '../../../../farm/app/types/farm'
import {
  BASEMAPS,
  CASING_COLOR,
  FIT_PADDING,
  PLOT_CASING_WEIGHT,
  PLOT_CORE_WEIGHT,
  PLOT_FILL_COLORS,
  PLOT_STROKE_COLOR,
} from '../../constants/map'
import { MINI_MAP_HEIGHT_CLASS } from '../../constants/plot-detail'

const props = defineProps<{ geometry: GeoJSONPolygon }>()

const PLOT_PANE = 'plot'

const mapEl = ref<HTMLElement | null>(null)
// Leaflet objects stay out of Vue's reactivity: proxying them breaks Leaflet's
// internal identity checks.
let map: LeafletNS.Map | null = null
let resizeObserver: ResizeObserver | null = null

onMounted(async () => {
  const library = await import('leaflet')
  if (!mapEl.value) return

  // A static picture of the plot: every interaction is off, so the page scroll
  // and the keyboard never get trapped inside the map.
  map = library.map(mapEl.value, {
    dragging: false,
    touchZoom: false,
    scrollWheelZoom: false,
    doubleClickZoom: false,
    boxZoom: false,
    keyboard: false,
    zoomControl: false,
  })

  // An explicit pane, as on the dashboard map: the default overlay pane ends up
  // stacked under the tiles here, hiding the outline.
  map.createPane(PLOT_PANE).style.zIndex = '400'

  const satellite = BASEMAPS.satellite
  library
    .tileLayer(satellite.url, {
      attribution: satellite.attribution,
      maxZoom: satellite.maxZoom,
    })
    .addTo(map)

  // Casing below and core on top, as on the dashboard map, so the outline holds
  // its contrast on any imagery.
  library
    .geoJSON(props.geometry, {
      style: { color: CASING_COLOR, weight: PLOT_CASING_WEIGHT, fill: false },
      interactive: false,
      pane: PLOT_PANE,
    })
    .addTo(map)
  const core = library
    .geoJSON(props.geometry, {
      style: {
        color: PLOT_STROKE_COLOR,
        weight: PLOT_CORE_WEIGHT,
        fillColor: PLOT_FILL_COLORS[0],
        fillOpacity: 0.25,
      },
      interactive: false,
      pane: PLOT_PANE,
    })
    .addTo(map)

  const fit = (): void => {
    map?.fitBounds(core.getBounds(), { padding: FIT_PADDING })
  }
  fit()

  resizeObserver = new ResizeObserver(() => {
    map?.invalidateSize({ animate: false })
    fit()
  })
  resizeObserver.observe(mapEl.value)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
  map?.remove()
  map = null
})
</script>

<template>
  <div
    ref="mapEl"
    :class="MINI_MAP_HEIGHT_CLASS"
    class="isolate w-full rounded-lg overflow-hidden bg-elevated"
  />
</template>
