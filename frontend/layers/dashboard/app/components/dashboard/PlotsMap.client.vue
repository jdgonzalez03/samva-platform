<script setup lang="ts">
// Imported here and nowhere else: the shared entry stylesheet must not carry
// map CSS for pages that have no map.
import 'leaflet/dist/leaflet.css'
import type * as LeafletNS from 'leaflet'
import type { Farm, Plot } from '../../../../farm/app/types/farm'
import {
  BASEMAPS,
  BOUNDARY_DASH_ARRAY,
  BOUNDARY_STROKE_COLOR,
  CASING_COLOR,
  FALLBACK_LOCATION_ZOOM,
  FIT_PADDING,
  INFO_CARD_CLOSE_DELAY_MS,
  MAP_HEIGHT_CLASS,
  MAP_PANES,
  PIN_HEIGHT,
  PIN_PATH,
  PIN_WIDTH,
  PLOT_ACTIVE_WEIGHT,
  PLOT_CASING_WEIGHT,
  PLOT_CORE_WEIGHT,
  PLOT_FILL_COLORS,
  PLOT_FOCUS_CASING_WEIGHT,
  PLOT_FOCUS_COLOR,
  PLOT_FOCUS_WEIGHT,
  PLOT_STROKE_COLOR,
  type BasemapId,
} from '../../constants/map'
import type { PlotFeatureProperties } from '../../utils/plot-features'

const props = defineProps<{
  farm: Farm
  plots: Plot[]
  basemap: BasemapId
}>()

const { t } = useI18n()
const localePath = useLocalePath()

const mapEl = useTemplateRef<HTMLDivElement>('mapEl')
const infoCardId = useId()

const activePlotId = shallowRef<number | null>(null)
const isCardOpen = shallowRef(false)
const anchorX = shallowRef(0)
const anchorY = shallowRef(0)

const activePlot = computed(
  () => props.plots.find((plot) => plot.id === activePlotId.value) ?? null,
)

// Leaflet instances are deliberately kept out of the reactivity system: they are
// large, self-mutating objects and proxying them breaks identity checks inside
// the library.
let leaflet: typeof LeafletNS | null = null
let map: LeafletNS.Map | null = null
let tileLayer: LeafletNS.TileLayer | null = null
let boundaryCasingLayer: LeafletNS.GeoJSON | null = null
let boundaryCoreLayer: LeafletNS.GeoJSON | null = null
let plotsCasingLayer: LeafletNS.GeoJSON | null = null
let plotsCoreLayer: LeafletNS.GeoJSON | null = null
let plotMarkersLayer: LeafletNS.GeoJSON | null = null
let resizeObserver: ResizeObserver | null = null
let closeTimer: ReturnType<typeof setTimeout> | null = null
let highlightedPlotId: number | null = null
let focusedPlotId: number | null = null
let fittedFarmId: number | null = null
let hasFitted = false
let hasFittedWithSize = false
let lastPointerType = 'mouse'

const plotPaths = new Map<number, LeafletNS.Path>()
const plotCasingPaths = new Map<number, LeafletNS.Path>()
const plotLabelPoints = new Map<number, LeafletNS.LatLng>()

const prefersReducedMotion = (): boolean =>
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

const cancelClose = (): void => {
  if (closeTimer === null) return
  clearTimeout(closeTimer)
  closeTimer = null
}

/**
 * Focus and hover both restyle the same shape, so the style is derived from
 * both flags at once instead of each handler writing its own.
 */
const applyPlotStyle = (plotId: number): void => {
  const isFocused = focusedPlotId === plotId
  const isHighlighted = highlightedPlotId === plotId
  plotPaths.get(plotId)?.setStyle({
    color: isFocused ? PLOT_FOCUS_COLOR : PLOT_STROKE_COLOR,
    weight: isFocused
      ? PLOT_FOCUS_WEIGHT
      : isHighlighted
        ? PLOT_ACTIVE_WEIGHT
        : PLOT_CORE_WEIGHT,
    opacity: 1,
  })
  plotCasingPaths.get(plotId)?.setStyle({
    // Widened so the casing stays visible on both sides of the focus band,
    // which is what gives the band its contrast against any basemap.
    weight: isFocused ? PLOT_FOCUS_CASING_WEIGHT : PLOT_CASING_WEIGHT,
  })
}

const restyle = (previous: number | null, next: number | null): void => {
  if (previous !== null && previous !== next) applyPlotStyle(previous)
  if (next !== null) applyPlotStyle(next)
}

const setHighlight = (plotId: number | null): void => {
  const previous = highlightedPlotId
  highlightedPlotId = plotId
  restyle(previous, plotId)
}

const setFocused = (plotId: number | null): void => {
  const previous = focusedPlotId
  focusedPlotId = plotId
  restyle(previous, plotId)
}

const updateAnchor = (): void => {
  const plotId = activePlotId.value
  const path = plotId === null ? undefined : plotPaths.get(plotId)
  if (!map || plotId === null || !path) return

  // The card hangs off the same anchor as the pin. The bounds centre is only a
  // last resort for a plot the backend sent no label point for: it can fall
  // outside a concave shape, which is why it anchors nothing permanent.
  const labelPoint = plotLabelPoints.get(plotId)
  const anchor =
    labelPoint ?? (path as LeafletNS.Polygon).getBounds().getCenter()
  const point = map.latLngToContainerPoint(anchor)
  anchorX.value = point.x
  // Raised to the pin's head so the card opens above the pin instead of over
  // it, which would put the card between the pointer and the shape.
  anchorY.value = labelPoint ? point.y - PIN_HEIGHT : point.y
}

const openCard = (plotId: number): void => {
  cancelClose()
  activePlotId.value = plotId
  isCardOpen.value = true
  setHighlight(plotId)
  updateAnchor()
}

const closeCard = (): void => {
  cancelClose()
  isCardOpen.value = false
  activePlotId.value = null
  setHighlight(null)
}

const scheduleClose = (): void => {
  cancelClose()
  // The delay is what lets the pointer travel from the shape onto the card
  // without the card vanishing under it (WCAG 1.4.13).
  closeTimer = setTimeout(closeCard, INFO_CARD_CLOSE_DELAY_MS)
}

const schedulePointerClose = (): void => {
  // A tap leaves nothing hovering, and the browser still emits a synthetic
  // mouseout for it — obeying that would snatch the card away from a touch user
  // before they can reach its "Ver lote" action. Their card closes on blur.
  if (lastPointerType === 'touch') return
  scheduleClose()
}

const goToPlot = (plotId: number): void => {
  void navigateTo(localePath(`/dashboard/plots/${plotId}`))
}

const preventAutoFocus = (event: Event): void => {
  event.preventDefault()
}

const createTileLayer = (
  library: typeof LeafletNS,
  id: BasemapId,
): LeafletNS.TileLayer => {
  const definition = BASEMAPS[id]
  return library.tileLayer(definition.url, {
    attribution: definition.attribution,
    maxZoom: definition.maxZoom,
  })
}

const SVG_NAMESPACE = 'http://www.w3.org/2000/svg'

/**
 * Pin and name label share one marker, so a plot has a single anchor and the
 * label cannot drift away from the pin. `textContent` keeps a plot name that
 * came off the wire out of `innerHTML`.
 */
const createPlotMarkerContent = (
  properties: PlotFeatureProperties,
): HTMLElement => {
  const root = document.createElement('div')

  const pin = document.createElementNS(SVG_NAMESPACE, 'svg')
  pin.setAttribute('class', 'samva-plot-pin')
  pin.setAttribute('viewBox', '0 0 24 36')
  pin.setAttribute('width', String(PIN_WIDTH))
  pin.setAttribute('height', String(PIN_HEIGHT))
  pin.setAttribute('focusable', 'false')

  const body = document.createElementNS(SVG_NAMESPACE, 'path')
  body.setAttribute('d', PIN_PATH)
  body.setAttribute(
    'fill',
    PLOT_FILL_COLORS[properties.colorIndex % PLOT_FILL_COLORS.length] as string,
  )
  // Same casing/core pairing as the shapes: a dark outline and a light centre
  // hold their edges against both street tiles and satellite imagery.
  body.setAttribute('stroke', CASING_COLOR)
  body.setAttribute('stroke-width', '2')

  const hole = document.createElementNS(SVG_NAMESPACE, 'circle')
  hole.setAttribute('cx', '12')
  hole.setAttribute('cy', '11.5')
  hole.setAttribute('r', '4')
  hole.setAttribute('fill', PLOT_STROKE_COLOR)

  pin.append(body, hole)

  const label = document.createElement('span')
  label.className = 'samva-plot-label'
  label.textContent = properties.name

  root.append(pin, label)
  return root
}

const stampPaths = (layer: LeafletNS.GeoJSON | null, role: string): void => {
  layer?.eachLayer((child) => {
    const path = child as LeafletNS.Path & {
      feature?: { properties: PlotFeatureProperties }
    }
    const element = path.getElement()
    if (!element) return
    element.setAttribute('data-role', role)
    element.setAttribute('aria-hidden', 'true')

    const plotId = path.feature?.properties?.plotId
    if (role === 'plot-casing' && plotId !== undefined) {
      plotCasingPaths.set(plotId, path)
    }
  })
}

/**
 * The polygon already carries the plot's name in its accessible name, so the
 * pin and its label must stay out of the accessibility tree — otherwise a
 * screen reader announces every plot twice.
 */
const stampMarkers = (): void => {
  plotMarkersLayer?.eachLayer((child) => {
    const element = (child as LeafletNS.Marker).getElement()
    if (!element) return
    element.setAttribute('data-role', 'plot-marker')
    element.setAttribute('aria-hidden', 'true')
  })
}

const decoratePlotPaths = (): void => {
  plotPaths.clear()

  plotsCoreLayer?.eachLayer((child) => {
    const path = child as LeafletNS.Path & {
      feature?: { properties: PlotFeatureProperties }
    }
    const properties = path.feature?.properties
    const element = path.getElement()
    if (!properties || !element) return

    plotPaths.set(properties.plotId, path)

    element.setAttribute('data-plot-id', String(properties.plotId))
    element.setAttribute('data-role', 'plot')
    element.setAttribute('role', 'link')
    element.setAttribute('tabindex', '0')
    element.setAttribute(
      'aria-label',
      t('dashboard.map.plotLabel', {
        name: properties.name,
        description:
          properties.description || t('dashboard.plots.noDescription'),
        // Composed from the pluralised key rather than repeating the noun, so
        // the name never reads "1 sensores".
        sensors: t('dashboard.plots.sensors', properties.sensorCount),
      }),
    )
    element.setAttribute(
      'aria-describedby',
      `${infoCardId}-${properties.plotId}`,
    )

    element.addEventListener('focus', () => {
      // Mouse focus lands here too (the mousedown handler below focuses the
      // shape), and a ring the pointer user never asked for is noise.
      if (element.matches(':focus-visible')) setFocused(properties.plotId)
      openCard(properties.plotId)
    })
    element.addEventListener('blur', () => {
      setFocused(null)
      scheduleClose()
    })
    // The browser scrolls a freshly focused shape fully into view, which moves
    // it out from under the pointer between press and release and swallows the
    // click. Preventing the default focus and focusing without the scroll keeps
    // both the pointer and the keyboard paths working.
    element.addEventListener('mousedown', (event) => {
      event.preventDefault()
      ;(element as SVGElement).focus({ preventScroll: true })
    })
    element.addEventListener('keydown', (event) => {
      const keyboardEvent = event as KeyboardEvent
      if (keyboardEvent.key === 'Enter' || keyboardEvent.key === ' ') {
        keyboardEvent.preventDefault()
        goToPlot(properties.plotId)
        return
      }
      if (keyboardEvent.key === 'Escape') {
        // Stop, do not blur: Escape dismisses the card and leaves focus put.
        keyboardEvent.stopPropagation()
        closeCard()
      }
    })

    path.on('mouseover', () => openCard(properties.plotId))
    path.on('mouseout', schedulePointerClose)
    path.on('click', () => {
      openCard(properties.plotId)
      // On touch the first tap only opens the card; its "Ver lote" link is the
      // navigation path, so a tap can never navigate by accident.
      if (lastPointerType === 'touch') return
      goToPlot(properties.plotId)
    })
  })
}

const clearVectors = (): void => {
  for (const layer of [
    boundaryCasingLayer,
    boundaryCoreLayer,
    plotsCasingLayer,
    plotsCoreLayer,
    plotMarkersLayer,
  ]) {
    layer?.remove()
  }
  boundaryCasingLayer = null
  boundaryCoreLayer = null
  plotsCasingLayer = null
  plotsCoreLayer = null
  plotMarkersLayer = null
  plotPaths.clear()
  plotCasingPaths.clear()
  plotLabelPoints.clear()
  highlightedPlotId = null
  focusedPlotId = null
}

const renderVectors = (): void => {
  if (!map || !leaflet) return
  const library = leaflet
  const currentMap = map

  clearVectors()

  if (props.farm.boundary) {
    const boundaryShape = { ...props.farm.boundary }
    boundaryCasingLayer = library
      .geoJSON(boundaryShape, {
        pane: MAP_PANES.casing.name,
        interactive: false,
        style: {
          color: CASING_COLOR,
          weight: 9,
          opacity: 0.9,
          fill: false,
          dashArray: BOUNDARY_DASH_ARRAY,
        },
      })
      .addTo(currentMap)
    boundaryCoreLayer = library
      .geoJSON(boundaryShape, {
        pane: MAP_PANES.core.name,
        interactive: false,
        style: {
          color: BOUNDARY_STROKE_COLOR,
          weight: 3,
          opacity: 1,
          fill: false,
          dashArray: BOUNDARY_DASH_ARRAY,
        },
      })
      .addTo(currentMap)
  }

  const collection = toPlotFeatureCollection(props.plots)
  if (collection.features.length === 0) return

  plotsCasingLayer = library
    .geoJSON(collection, {
      pane: MAP_PANES.casing.name,
      interactive: false,
      style: {
        color: CASING_COLOR,
        weight: PLOT_CASING_WEIGHT,
        opacity: 1,
        fill: false,
      },
    })
    .addTo(currentMap)

  plotsCoreLayer = library
    .geoJSON(collection, {
      pane: MAP_PANES.core.name,
      style: (feature) => ({
        color: PLOT_STROKE_COLOR,
        weight: PLOT_CORE_WEIGHT,
        opacity: 1,
        fillColor:
          PLOT_FILL_COLORS[
            ((feature?.properties as PlotFeatureProperties | undefined)
              ?.colorIndex ?? 0) % PLOT_FILL_COLORS.length
          ],
        fillOpacity: 0.22,
      }),
    })
    .addTo(currentMap)

  plotMarkersLayer = library
    .geoJSON(toPlotLabelFeatureCollection(props.plots), {
      pane: MAP_PANES.labels.name,
      // `L.geoJSON` does the [lng, lat] → LatLng swap, so the pin lands on the
      // point the backend guaranteed is inside the polygon.
      pointToLayer: (feature, latlng) => {
        const properties = feature.properties as PlotFeatureProperties
        plotLabelPoints.set(properties.plotId, latlng)
        return library.marker(latlng, {
          pane: MAP_PANES.labels.name,
          // Decorative twin of the polygon: without both of these the plot
          // would answer to two tab stops and be announced twice, and the pin
          // would swallow the click meant for the shape underneath it.
          interactive: false,
          keyboard: false,
          icon: library.divIcon({
            className: 'samva-plot-marker',
            html: createPlotMarkerContent(properties),
            iconSize: [0, 0],
          }),
        })
      },
    })
    .addTo(currentMap)
}

const fitTarget = (): void => {
  if (!map) return
  // The first fit moves off the placeholder view the map is created with, so
  // animating it would pan across the globe.
  const animate = hasFitted && !prefersReducedMotion()
  hasFitted = true

  if (boundaryCoreLayer && boundaryCoreLayer.getLayers().length > 0) {
    map.fitBounds(boundaryCoreLayer.getBounds(), {
      padding: FIT_PADDING,
      animate,
    })
    return
  }
  if (plotsCoreLayer && plotsCoreLayer.getLayers().length > 0) {
    map.fitBounds(plotsCoreLayer.getBounds(), { padding: FIT_PADDING, animate })
    return
  }
  if (props.farm.location) {
    // The one hand-written swap in this component: GeoJSON is [lng, lat],
    // Leaflet's setView takes [lat, lng].
    const [longitude, latitude] = props.farm.location.coordinates
    map.setView([latitude, longitude], FALLBACK_LOCATION_ZOOM, { animate })
  }
}

const syncMap = (): void => {
  closeCard()
  renderVectors()
  if (fittedFarmId !== props.farm.id) {
    fitTarget()
    fittedFarmId = props.farm.id
  }

  // Leaflet only realises a layer once the map has a view, so the SVG elements
  // do not exist until the fit above has run — stamping any earlier silently
  // does nothing.
  stampPaths(boundaryCasingLayer, 'boundary-casing')
  stampPaths(boundaryCoreLayer, 'boundary')
  stampPaths(plotsCasingLayer, 'plot-casing')
  stampMarkers()
  decoratePlotPaths()
}

onMounted(async () => {
  const library = await import('leaflet')
  if (!mapEl.value) return
  leaflet = library

  // A view is required before any layer is added: Leaflet defers realising a
  // layer (and creating its SVG element) until the map is loaded, and computing
  // a fit needs a current zoom to work from.
  map = library.map(mapEl.value, { keyboard: true, center: [0, 0], zoom: 2 })

  for (const pane of Object.values(MAP_PANES)) {
    map.createPane(pane.name).style.zIndex = String(pane.zIndex)
  }

  tileLayer = createTileLayer(library, props.basemap).addTo(map)

  syncMap()

  map.on('move zoom', updateAnchor)
  mapEl.value.addEventListener(
    'pointerdown',
    (event) => {
      lastPointerType = event.pointerType
    },
    true,
  )

  // The tab panel keeps this component mounted while it is hidden, so Leaflet's
  // cached dimensions go stale; re-measuring whenever the box regains a size is
  // what prevents the grey-tiles-after-a-tab-switch bug, and it covers the
  // sidebar collapsing too.
  resizeObserver = new ResizeObserver(([entry]) => {
    if (!map || !entry) return
    const { width, height } = entry.contentRect
    if (width === 0 || height === 0) return

    map.invalidateSize({ animate: false })
    if (!hasFittedWithSize) {
      hasFittedWithSize = true
      fitTarget()
    }
  })
  resizeObserver.observe(mapEl.value)
})

watch(
  [() => props.farm, () => props.plots],
  () => {
    syncMap()
  },
  { deep: false },
)

watch(
  () => props.basemap,
  (next) => {
    if (!map || !leaflet) return
    // The vector layers live in their own panes, so removing a tile layer can
    // never take a plot outline with it.
    tileLayer?.remove()
    tileLayer = createTileLayer(leaflet, next).addTo(map)
  },
)

onBeforeUnmount(() => {
  cancelClose()
  resizeObserver?.disconnect()
  resizeObserver = null
  map?.remove()
  map = null
  leaflet = null
  plotPaths.clear()
})
</script>

<template>
  <div class="relative isolate w-full">
    <div
      ref="mapEl"
      :class="MAP_HEIGHT_CLASS"
      class="w-full rounded-lg overflow-hidden bg-elevated"
    />

    <!-- One description per plot, always in the DOM: the aria-describedby on
         each path can never dangle and never lags a focus change. -->
    <div class="sr-only">
      <p v-for="plot in plots" :id="`${infoCardId}-${plot.id}`" :key="plot.id">
        {{ plot.description || t('dashboard.plots.noDescription') }},
        {{ t('dashboard.plots.sensors', plot.sensor_count) }}
      </p>
    </div>

    <UPopover
      :open="isCardOpen && activePlot !== null"
      :dismissible="false"
      :content="{
        side: 'top',
        align: 'center',
        onOpenAutoFocus: preventAutoFocus,
        onCloseAutoFocus: preventAutoFocus,
      }"
    >
      <template #anchor>
        <div
          class="absolute size-0 pointer-events-none"
          :style="{ left: `${anchorX}px`, top: `${anchorY}px` }"
          aria-hidden="true"
        />
      </template>

      <template #content>
        <div @mouseenter="cancelClose" @mouseleave="schedulePointerClose">
          <DashboardPlotInfoCard
            v-if="activePlot"
            :plot="activePlot"
            @navigate="closeCard"
          />
        </div>
      </template>
    </UPopover>
  </div>
</template>

<style scoped>
/* Leaflet builds these nodes itself, so they carry no scope attribute. */
:deep(path[data-role='plot']) {
  cursor: pointer;
}

/* The focus indicator is drawn in SVG (see `applyPlotStyle`), not with an
   outline: a CSS outline takes no casing — `filter: drop-shadow` does not reach
   it — so on street tiles it measures 1.19:1, and at `outline-offset` it paints
   over the dark casing that carries the contrast. */
:deep(path[data-role='plot']:focus) {
  outline: none;
}

/* Zero-sized box anchored on the plot's label point: the pin hangs above it so
   its tip marks the point, the name sits directly below. */
:deep(.samva-plot-marker) {
  width: 0;
  height: 0;
  /* The polygon underneath must stay the only click target. */
  pointer-events: none;
}

:deep(.samva-plot-pin) {
  position: absolute;
  bottom: 0;
  left: 0;
  display: block;
  transform: translateX(-50%);
}

:deep(.samva-plot-label) {
  position: absolute;
  top: 2px;
  left: 0;
  transform: translateX(-50%);
  color: #ffffff;
  font-size: 0.75rem;
  font-weight: 600;
  text-shadow:
    0 0 3px #0a0a0a,
    0 0 2px #0a0a0a,
    0 1px 2px #0a0a0a;
  white-space: nowrap;
}
</style>
