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

export interface ComparisonLine {
  plotId: number
  name: string
  color: string
  points: { t: number; value: number }[]
}

const props = defineProps<{
  lines: ComparisonLine[]
  unit: string
  showDates: boolean
}>()

const { locale } = useI18n()

interface Row {
  t: number
  values: Map<number, number>
}

// One row per timestamp with every plot's value, since an XY container takes a
// single data array for all its lines.
const rows = computed<Row[]>(() => {
  const byTime = new Map<number, Map<number, number>>()
  for (const line of props.lines) {
    for (const point of line.points) {
      const values = byTime.get(point.t) ?? new Map<number, number>()
      values.set(line.plotId, point.value)
      byTime.set(point.t, values)
    }
  }
  return [...byTime.entries()]
    .sort(([a], [b]) => a - b)
    .map(([t, values]) => ({ t, values }))
})

const x = (row: Row): number => row.t
// `NaN`, never `null`: Unovis reads `null` as 0 and would draw a false reading
// where a plot simply has no data for that hour.
const yAccessors = computed(() =>
  props.lines.map(
    (line) => (row: Row) => row.values.get(line.plotId) ?? Number.NaN,
  ),
)
const colors = computed(() => props.lines.map((line) => line.color))

const tickFormat = computed(
  () =>
    new Intl.DateTimeFormat(
      locale.value,
      props.showDates
        ? { weekday: 'short', day: 'numeric' }
        : { hour: '2-digit', minute: '2-digit' },
    ),
)
const valueFormat = computed(
  () => new Intl.NumberFormat(locale.value, { maximumFractionDigits: 1 }),
)
const formatTick = (tick: number | Date): string =>
  tickFormat.value.format(new Date(tick as number))
const formatValue = (tick: number | Date): string =>
  valueFormat.value.format(Number(tick))

// Built as DOM with `textContent`, not an HTML string: plot names are text the
// farmer typed, and nothing in them should be parsed as markup.
const tooltip = (row: Row): HTMLElement | string => {
  if (!row) return ''
  const root = document.createElement('div')

  const header = document.createElement('div')
  header.className = 'font-medium mb-1'
  header.textContent = new Intl.DateTimeFormat(locale.value, {
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(row.t))
  root.append(header)

  for (const line of props.lines) {
    const value = row.values.get(line.plotId)
    if (value === undefined) continue
    const item = document.createElement('div')
    item.className = 'flex items-center gap-1.5'
    const dot = document.createElement('span')
    dot.className = 'inline-block size-2 rounded-full'
    dot.style.backgroundColor = line.color
    const text = document.createElement('span')
    text.textContent = `${line.name}: ${valueFormat.value.format(value)} ${props.unit}`
    item.append(dot, text)
    root.append(item)
  }
  return root
}
</script>

<template>
  <VisXYContainer
    :data="rows"
    :height="TREND_CHART_HEIGHT"
    :margin="{ top: 8, right: 16, bottom: 8, left: 8 }"
    class="w-full"
  >
    <VisLine
      :x="x"
      :y="yAccessors"
      :color="colors"
      :curve-type="CurveType.MonotoneX"
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
    <VisCrosshair color="var(--ui-text-muted)" :template="tooltip" />
    <VisTooltip />
  </VisXYContainer>
</template>
