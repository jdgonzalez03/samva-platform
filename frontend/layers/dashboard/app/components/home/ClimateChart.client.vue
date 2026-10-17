<script setup lang="ts">
import { GroupedBar } from '@unovis/ts'
import { VisAxis, VisGroupedBar, VisTooltip, VisXYContainer } from '@unovis/vue'
import { TREND_CHART_HEIGHT } from '../../constants/plot-detail'
import type { DailyStats } from '../../utils/farm-overview'

const props = defineProps<{
  days: DailyStats[]
  unit: string
  labels: { min: string; average: string; max: string }
}>()

const { locale } = useI18n()

const COLORS = ['var(--ui-info)', 'var(--ui-primary)', 'var(--ui-warning)']

const x = (_: DailyStats, index: number): number => index
const y = [
  (day: DailyStats) => day.min,
  (day: DailyStats) => day.average,
  (day: DailyStats) => day.max,
]

const dayFormat = computed(
  () =>
    new Intl.DateTimeFormat(locale.value, { weekday: 'short', day: 'numeric' }),
)
const valueFormat = computed(
  () => new Intl.NumberFormat(locale.value, { maximumFractionDigits: 1 }),
)
const formatTick = (tick: number | Date): string => {
  const day = props.days[Number(tick)]
  return day ? dayFormat.value.format(day.day) : ''
}
const formatValue = (tick: number | Date): string =>
  valueFormat.value.format(Number(tick))

// Keyed on the bar's own class: a crosshair assumes a continuous x axis and
// does nothing over bars.
const triggers = computed(() => ({
  [GroupedBar.selectors.bar]: (day: DailyStats): HTMLElement | null => {
    if (!day) return null
    const root = document.createElement('div')
    const header = document.createElement('div')
    header.className = 'font-medium mb-1'
    header.textContent = dayFormat.value.format(day.day)
    root.append(header)
    for (const [label, value] of [
      [props.labels.max, day.max],
      [props.labels.average, day.average],
      [props.labels.min, day.min],
    ] as const) {
      const row = document.createElement('div')
      row.textContent = `${label}: ${valueFormat.value.format(value)} ${props.unit}`
      root.append(row)
    }
    return root
  },
}))
</script>

<template>
  <VisXYContainer
    :data="days"
    :height="TREND_CHART_HEIGHT"
    :margin="{ top: 8, right: 16, bottom: 8, left: 8 }"
    class="w-full"
  >
    <VisGroupedBar
      :x="x"
      :y="y"
      :color="COLORS"
      :rounded-corners="4"
      :group-padding="0.25"
    />
    <VisAxis
      type="x"
      :tick-format="formatTick"
      :num-ticks="days.length"
      :grid-line="false"
    />
    <VisAxis
      type="y"
      :tick-format="formatValue"
      :num-ticks="4"
      :grid-line="false"
    />
    <VisTooltip :triggers="triggers" />
  </VisXYContainer>
</template>
