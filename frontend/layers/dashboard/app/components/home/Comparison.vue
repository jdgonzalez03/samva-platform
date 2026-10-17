<script setup lang="ts">
import type { TabsItem } from '@nuxt/ui'
import type { FarmOverview } from '../../../../farm/app/types/farm'
import {
  CONDITION_ICONS,
  FALLBACK_CONDITION_ICON,
  TREND_CHART_HEIGHT_CLASS,
  TREND_RANGE_HOURS,
  TREND_RANGES,
  type TrendRange,
} from '../../constants/plot-detail'
import { plotSeriesPoints } from '../../utils/farm-overview'
import { pointsWithinHours } from '../../utils/plot-series'
import type { ComparisonLine } from './ComparisonChart.client.vue'

const props = defineProps<{
  overview: FarmOverview
  colors: Map<number, string>
  now: number
}>()

const { t, locale } = useI18n()

const variableItems = computed(() =>
  props.overview.series.map((series) => ({
    label: series.name,
    value: series.semantic_key,
    icon: CONDITION_ICONS[series.semantic_key] ?? FALLBACK_CONDITION_ICON,
  })),
)
const selectedKey = ref<string | undefined>(
  props.overview.series.find(
    (series) => series.semantic_key === 'soil_moisture',
  )?.semantic_key ?? props.overview.series[0]?.semantic_key,
)
const range = ref<TrendRange>('24h')

const rangeItems = computed<TabsItem[]>(() =>
  TREND_RANGES.map((value) => ({
    label: t(`dashboard.plotDetail.trend.ranges.${value}`),
    value,
  })),
)

const unit = computed(
  () =>
    props.overview.series.find(
      (series) => series.semantic_key === selectedKey.value,
    )?.unit ?? '',
)

const lines = computed<ComparisonLine[]>(() =>
  props.overview.plots
    .map((plot) => ({
      plotId: plot.id,
      name: plot.name,
      color: props.colors.get(plot.id) ?? 'var(--ui-primary)',
      points: pointsWithinHours(
        plotSeriesPoints(plot, selectedKey.value ?? ''),
        TREND_RANGE_HOURS[range.value],
        props.now,
      ),
    }))
    .filter((line) => line.points.length > 0),
)

const summary = computed(() => {
  const format = new Intl.NumberFormat(locale.value, {
    maximumFractionDigits: 1,
  })
  const list = lines.value
    .map((line) =>
      `${line.name} ${format.format(line.points.at(-1)!.value)} ${unit.value}`.trim(),
    )
    .join(', ')
  return t('dashboard.home.comparison.alternative', { list })
})

const setVariable = (value: string | number): void => {
  selectedKey.value = String(value)
}
const setRange = (value: string | number): void => {
  range.value = value as TrendRange
}
</script>

<template>
  <UCard variant="subtle" class="h-full" :ui="{ body: 'flex flex-col gap-4' }">
    <template #header>
      <div class="flex flex-wrap items-center justify-between gap-3">
        <h2 class="flex items-center gap-2 font-semibold text-highlighted">
          <UIcon
            name="i-lucide-chart-spline"
            class="text-primary"
            aria-hidden="true"
          />
          {{ t('dashboard.home.comparison.title') }}
        </h2>
        <div class="flex flex-wrap items-center gap-2">
          <USelect
            :model-value="selectedKey"
            :items="variableItems"
            :aria-label="t('dashboard.home.comparison.variable')"
            class="w-52"
            @update:model-value="setVariable"
          />
          <UTabs
            :items="rangeItems"
            :model-value="range"
            :content="false"
            size="xs"
            :aria-label="t('dashboard.home.comparison.range')"
            @update:model-value="setRange"
          />
        </div>
      </div>
    </template>

    <p v-if="lines.length === 0" class="text-sm text-muted">
      {{ t('dashboard.home.comparison.empty') }}
    </p>

    <template v-else>
      <div aria-hidden="true">
        <ClientOnly>
          <HomeComparisonChart
            :lines="lines"
            :unit="unit"
            :show-dates="range === '7d'"
          />
          <template #fallback>
            <USkeleton :class="TREND_CHART_HEIGHT_CLASS" class="w-full" />
          </template>
        </ClientOnly>
      </div>
      <ul class="flex flex-wrap gap-x-4 gap-y-1 text-sm" aria-hidden="true">
        <li
          v-for="line in lines"
          :key="line.plotId"
          class="flex items-center gap-2"
        >
          <span
            class="size-2.5 rounded-full"
            :style="{ backgroundColor: line.color }"
          />
          {{ line.name }}
        </li>
      </ul>
      <p class="sr-only">{{ summary }}</p>
    </template>
  </UCard>
</template>
