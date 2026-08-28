<script setup lang="ts">
import { GroupedBar } from '@unovis/ts'
import { VisAxis, VisGroupedBar, VisTooltip, VisXYContainer } from '@unovis/vue'
import { CHART_HEIGHT, CHART_MARGIN } from '../../constants/history'
import type { SensorSemanticKey } from '../../types/sensors'
import type { BarPoint } from '../../utils/history-chart'

const props = defineProps<{
  bars: BarPoint[]
  semanticKey: SensorSemanticKey
  unit: string
}>()

const { t, locale } = useI18n()
const color = useVariableColor(() => props.semanticKey)

// Bars, not a line: the x axis here is plots, a category. A line across three
// plots would suggest a continuity between them that does not exist.
const xAccessor = (bar: BarPoint): number => bar.index
const yAccessor = (bar: BarPoint): number => bar.value

const valueFormatter = computed(
  () => new Intl.NumberFormat(locale.value, { maximumFractionDigits: 2 }),
)

const formatValue = (tick: number | Date): string =>
  valueFormatter.value.format(Number(tick))

const formatPlot = (tick: number | Date): string =>
  props.bars[Number(tick)]?.label ?? ''

// Hovering a bar, not the x position: a `VisCrosshair` — what the line chart
// uses — snaps to the nearest x on a continuous axis, and this axis is a list of
// plots. The trigger is keyed to the bar's own class, so the reading always
// belongs to the bar under the pointer.
//
// Built as DOM with `textContent` rather than an HTML string: the plot name is
// text the farmer typed, and nothing in it should be parsed as markup.
const tooltipTriggers = computed(() => ({
  [GroupedBar.selectors.bar]: (bar: BarPoint): HTMLElement | null => {
    if (!bar) return null

    const root = document.createElement('div')

    const name = document.createElement('div')
    name.className = 'font-medium'
    name.textContent = bar.label

    const value = document.createElement('div')
    value.textContent = `${valueFormatter.value.format(bar.value)} ${props.unit}`

    root.append(name, value)

    // The average alone hides how thin it might be: 12 readings and 2.880 make
    // the same bar.
    if (bar.sampleCount > 0) {
      const samples = document.createElement('div')
      samples.className = 'text-dimmed'
      samples.textContent = t(
        'sensors.history.charts.samples',
        { count: valueFormatter.value.format(bar.sampleCount) },
        bar.sampleCount,
      )
      root.append(samples)
    }

    return root
  },
}))
</script>

<template>
  <VisXYContainer
    :data="bars"
    :height="CHART_HEIGHT"
    :margin="CHART_MARGIN"
    class="w-full"
  >
    <VisGroupedBar :x="xAccessor" :y="yAccessor" :color="color" />
    <VisAxis
      type="x"
      :tick-format="formatPlot"
      :num-ticks="bars.length"
      :grid-line="false"
      :tick-text-width="96"
    />
    <VisAxis type="y" :tick-format="formatValue" :num-ticks="4" />
    <VisTooltip :triggers="tooltipTriggers" />
  </VisXYContainer>
</template>
