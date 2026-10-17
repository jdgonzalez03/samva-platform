<script setup lang="ts">
import { CurveType } from '@unovis/ts'
import {
  VisAxis,
  VisCrosshair,
  VisLine,
  VisTooltip,
  VisXYContainer,
} from '@unovis/vue'
import { TREND_CHART_HEIGHT } from '../../constants/plot-detail'
import type { SeriesPoint } from '../../utils/plot-series'

const props = defineProps<{
  points: SeriesPoint[]
  unit: string
  showDates: boolean
}>()

const { locale } = useI18n()

// Fitted to the data rather than anchored at zero, so a drift of a few points
// reads as a slope instead of a flat line near the top.
const yDomain = computed<[number, number]>(() => {
  const values = props.points.map((point) => point.value)
  const min = Math.min(...values)
  const max = Math.max(...values)
  const padding = (max - min) * 0.1 || Math.abs(max) * 0.1 || 1
  return [min - padding, max + padding]
})

const x = (point: SeriesPoint): number => point.t
const y = (point: SeriesPoint): number => point.value

const tickFormat = computed(
  () =>
    new Intl.DateTimeFormat(
      locale.value,
      props.showDates
        ? { weekday: 'short', day: 'numeric' }
        : { hour: '2-digit', minute: '2-digit' },
    ),
)
const tooltipDate = computed(
  () =>
    new Intl.DateTimeFormat(locale.value, {
      weekday: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }),
)
const valueFormat = computed(
  () => new Intl.NumberFormat(locale.value, { maximumFractionDigits: 1 }),
)

const formatTick = (tick: number | Date): string =>
  tickFormat.value.format(new Date(tick as number))
const formatValue = (tick: number | Date): string =>
  valueFormat.value.format(Number(tick))

const tooltip = (point: SeriesPoint): string =>
  point
    ? `${tooltipDate.value.format(new Date(point.t))} — ${valueFormat.value.format(point.value)} ${props.unit}`
    : ''
</script>

<template>
  <VisXYContainer
    :data="points"
    :height="TREND_CHART_HEIGHT"
    :margin="{ top: 8, right: 16, bottom: 8, left: 8 }"
    :y-domain="yDomain"
    class="w-full"
  >
    <VisLine
      :x="x"
      :y="y"
      :curve-type="CurveType.MonotoneX"
      color="var(--ui-primary)"
      :line-width="2"
    />
    <VisAxis
      type="x"
      :tick-format="formatTick"
      :grid-line="false"
      :num-ticks="6"
    />
    <VisAxis
      type="y"
      :tick-format="formatValue"
      :num-ticks="4"
      :grid-line="false"
    />
    <VisCrosshair color="var(--ui-primary)" :template="tooltip" />
    <VisTooltip />
  </VisXYContainer>
</template>
