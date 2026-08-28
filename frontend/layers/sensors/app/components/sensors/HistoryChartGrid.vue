<script setup lang="ts">
import { CHART_HEIGHT_CLASS, VARIABLE_ICONS } from '../../constants/history'
import type { HistorySeries } from '../../types/sensors'
import { fillBuckets, summariseSeries } from '../../utils/history-chart'

const props = defineProps<{
  series: HistorySeries[]
  rangeFrom: string
  rangeTo: string
}>()

const { t, locale } = useI18n()

const fromMs = computed(() => Date.parse(props.rangeFrom))
const toMs = computed(() => Date.parse(props.rangeTo))

const numberFormatter = computed(
  () => new Intl.NumberFormat(locale.value, { maximumFractionDigits: 2 }),
)

const dateTimeFormatter = computed(
  () =>
    new Intl.DateTimeFormat(locale.value, {
      dateStyle: 'short',
      timeStyle: 'short',
    }),
)

// Identity is `variable_id`, never `semantic_key`: two variables may share a
// key, and folding them together would merge unrelated series.
const charts = computed(() =>
  props.series.map((series) => {
    const summary = summariseSeries(series.points)
    return {
      id: series.variable_id,
      name: series.name,
      unit: series.unit,
      semanticKey: series.semantic_key,
      icon: VARIABLE_ICONS[series.semantic_key] ?? VARIABLE_ICONS.other,
      hasData: summary !== null,
      points: fillBuckets(
        series.points,
        fromMs.value,
        toMs.value,
        series.bucket_seconds,
      ),
      summary: summary
        ? t('sensors.history.charts.summary', {
            name: series.name,
            unit: series.unit,
            readings: numberFormatter.value.format(summary.readingCount),
            from: dateTimeFormatter.value.format(new Date(summary.firstAt)),
            to: dateTimeFormatter.value.format(new Date(summary.lastAt)),
            min: numberFormatter.value.format(summary.min),
            max: numberFormatter.value.format(summary.max),
            average: numberFormatter.value.format(summary.average),
          })
        : t('sensors.history.charts.noData', { name: series.name }),
    }
  }),
)
</script>

<template>
  <section
    :aria-label="t('sensors.history.charts.label')"
    class="flex flex-col gap-3"
  >
    <!-- Visible, not sr-only: everyone benefits from being told where the same
         numbers live in readable form (1.1.1). -->
    <p class="text-sm text-muted">
      {{ t('sensors.history.charts.alternative') }}
    </p>

    <div class="grid gap-4 sm:grid-cols-2">
      <SensorsHistoryChartFigure
        v-for="chart in charts"
        :key="chart.id"
        :title="chart.name"
        :unit="chart.unit"
        :icon="chart.icon"
        :summary="chart.summary"
      >
        <UEmpty
          v-if="!chart.hasData"
          icon="i-lucide-chart-line"
          size="sm"
          :description="t('sensors.history.table.empty')"
        />
        <ClientOnly v-else>
          <LazySensorsHistoryLineChart
            :points="chart.points"
            :semantic-key="chart.semanticKey"
            :unit="chart.unit"
          />
          <template #fallback>
            <USkeleton :class="CHART_HEIGHT_CLASS" class="w-full" />
          </template>
        </ClientOnly>
      </SensorsHistoryChartFigure>
    </div>
  </section>
</template>
