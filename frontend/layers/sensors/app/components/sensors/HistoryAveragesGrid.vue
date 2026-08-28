<script setup lang="ts">
import type { Plot } from '../../../../farm/app/types/farm'
import { CHART_HEIGHT_CLASS, VARIABLE_ICONS } from '../../constants/history'
import type { PlotAverage } from '../../types/sensors'
import { groupAveragesByVariable } from '../../utils/history-chart'

const props = defineProps<{
  averages: PlotAverage[]
  plots: Plot[]
}>()

const { t, locale } = useI18n()

const numberFormatter = computed(
  () => new Intl.NumberFormat(locale.value, { maximumFractionDigits: 2 }),
)

const charts = computed(() =>
  groupAveragesByVariable(props.averages).map((group) => ({
    ...group,
    icon: VARIABLE_ICONS[group.semanticKey] ?? VARIABLE_ICONS.other,
    summary: t('sensors.history.averages.summary', {
      name: group.name,
      unit: group.unit,
      detail: group.bars
        .map(
          (bar) => `${bar.label}: ${numberFormatter.value.format(bar.value)}`,
        )
        .join('; '),
    }),
  })),
)

// The endpoint omits a plot that reported nothing rather than sending a null
// average, so the gap is filled here from the plot list the page already has.
const plotsWithoutData = computed(() => {
  const withData = new Set(props.averages.map((average) => average.plot_id))
  return props.plots.filter((plot) => !withData.has(plot.id))
})
</script>

<template>
  <section
    :aria-label="t('sensors.history.averages.label')"
    class="flex flex-col gap-3"
  >
    <p class="text-sm text-muted">
      {{ t('sensors.history.charts.alternative') }}
    </p>

    <div class="grid gap-4 sm:grid-cols-2">
      <SensorsHistoryChartFigure
        v-for="chart in charts"
        :key="chart.variableId"
        :title="chart.name"
        :unit="chart.unit"
        :icon="chart.icon"
        :summary="chart.summary"
      >
        <ClientOnly>
          <LazySensorsHistoryBarChart
            :bars="chart.bars"
            :semantic-key="chart.semanticKey"
            :unit="chart.unit"
          />
          <template #fallback>
            <USkeleton :class="CHART_HEIGHT_CLASS" class="w-full" />
          </template>
        </ClientOnly>
      </SensorsHistoryChartFigure>
    </div>

    <p v-if="plotsWithoutData.length" class="text-sm text-muted">
      {{
        t('sensors.history.averages.noPlotData', {
          plots: plotsWithoutData.map((plot) => plot.name).join(', '),
        })
      }}
    </p>
  </section>
</template>
