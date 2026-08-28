<script setup lang="ts">
// No stylesheet import, unlike the Leaflet map: `@unovis/ts` ships no CSS for
// the XY components — their styles are injected at runtime.
import { CurveType } from '@unovis/ts'
import {
  VisAxis,
  VisCrosshair,
  VisLine,
  VisScatter,
  VisTooltip,
  VisXYContainer,
} from '@unovis/vue'
import {
  CHART_HEIGHT,
  CHART_MARGIN,
  SPARSE_POINT_THRESHOLD,
} from '../../constants/history'
import type { SensorSemanticKey } from '../../types/sensors'
import type { ChartPoint } from '../../utils/history-chart'

const props = defineProps<{
  points: ChartPoint[]
  semanticKey: SensorSemanticKey
  unit: string
}>()

const { locale } = useI18n()
const color = useVariableColor(() => props.semanticKey)

const xAccessor = (point: ChartPoint): number => point.t
// `NaN`, never `null`: `isFinite(null)` is `true` in JS, so Unovis would keep a
// missing bucket `defined` and draw it at `yScale(0)` — a flat line along zero
// that reads as "the sensor measured nothing". A non-finite value falls to the
// component's `fallbackValue` (`undefined` for `VisLine`) and leaves the point
// undefined, which is what actually breaks the path over the gap.
const yAccessor = (point: ChartPoint): number => point.value ?? Number.NaN

const drawnPoints = computed(() =>
  props.points.filter((point) => point.value !== null),
)

// A `VisLine` through one or two points renders nothing visible, so the marks
// have to carry the data themselves.
const isSparse = computed(
  () => drawnPoints.value.length < SPARSE_POINT_THRESHOLD,
)

const tickFormatter = computed(
  () =>
    new Intl.DateTimeFormat(locale.value, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }),
)

const valueFormatter = computed(
  () => new Intl.NumberFormat(locale.value, { maximumFractionDigits: 2 }),
)

const formatTick = (tick: number | Date): string =>
  tickFormatter.value.format(new Date(tick as number))

const formatValue = (tick: number | Date): string =>
  valueFormatter.value.format(Number(tick))

const tooltipTemplate = (point: ChartPoint): string => {
  if (!point || point.value === null) return ''
  return `${formatTick(point.t)} — ${valueFormatter.value.format(point.value)} ${props.unit}`
}
</script>

<template>
  <VisXYContainer
    :data="points"
    :height="CHART_HEIGHT"
    :margin="CHART_MARGIN"
    class="w-full"
  >
    <VisLine
      :x="xAccessor"
      :y="yAccessor"
      :curve-type="CurveType.MonotoneX"
      :color="color"
    />
    <VisScatter
      v-if="isSparse"
      :data="drawnPoints"
      :x="xAccessor"
      :y="yAccessor"
      :color="color"
      :size="8"
    />
    <VisAxis
      type="x"
      :tick-format="formatTick"
      :num-ticks="4"
      :grid-line="false"
    />
    <VisAxis type="y" :label="unit" :tick-format="formatValue" :num-ticks="4" />
    <VisCrosshair :template="tooltipTemplate" :color="color" />
    <VisTooltip />
  </VisXYContainer>
</template>
