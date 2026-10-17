<script setup lang="ts">
import type { TabsItem } from '@nuxt/ui'
import type { PlotSeries } from '../../../../farm/app/types/farm'
import {
  CONDITION_ICONS,
  FALLBACK_CONDITION_ICON,
  TREND_CHART_HEIGHT_CLASS,
  TREND_RANGE_HOURS,
  TREND_RANGES,
  type TrendRange,
} from '../../constants/plot-detail'
import {
  pointsWithinHours,
  seriesStats,
  toSeriesPoints,
} from '../../utils/plot-series'

const props = defineProps<{ series: PlotSeries[]; now: number }>()

const { t, locale } = useI18n()

const selectedKey = ref<string | undefined>(props.series[0]?.semantic_key)
const range = ref<TrendRange>('24h')

watch(
  () => props.series,
  (series) => {
    if (!series.some((item) => item.semantic_key === selectedKey.value)) {
      selectedKey.value = series[0]?.semantic_key
    }
  },
)

const variableItems = computed(() =>
  props.series.map((item) => ({
    label: item.name,
    value: item.semantic_key,
    icon: CONDITION_ICONS[item.semantic_key] ?? FALLBACK_CONDITION_ICON,
  })),
)
const rangeItems = computed<TabsItem[]>(() =>
  TREND_RANGES.map((value) => ({
    label: t(`dashboard.plotDetail.trend.ranges.${value}`),
    value,
  })),
)

const selected = computed(() =>
  props.series.find((item) => item.semantic_key === selectedKey.value),
)
const points = computed(() =>
  pointsWithinHours(
    toSeriesPoints(selected.value),
    TREND_RANGE_HOURS[range.value],
    props.now,
  ),
)
const stats = computed(() => seriesStats(points.value))

const statItems = computed(() => {
  if (!stats.value || !selected.value) return []
  const format = new Intl.NumberFormat(locale.value, {
    maximumFractionDigits: 1,
  })
  const unit = selected.value.unit
  return (['min', 'average', 'max'] as const).map((key) => ({
    key,
    label: t(`dashboard.plotDetail.trend.${key}`),
    value: `${format.format(stats.value![key])} ${unit}`.trim(),
  }))
})

const setVariable = (value: string | number): void => {
  selectedKey.value = String(value)
}
const setRange = (value: string | number): void => {
  range.value = value as TrendRange
}
</script>

<template>
  <UCard variant="subtle" :ui="{ body: 'flex flex-col gap-4' }">
    <template #header>
      <div class="flex flex-wrap items-center justify-between gap-3">
        <h2 class="flex items-center gap-2 font-semibold text-highlighted">
          <UIcon
            name="i-lucide-chart-spline"
            class="text-primary"
            aria-hidden="true"
          />
          {{ t('dashboard.plotDetail.trend.title') }}
        </h2>
        <UTabs
          :items="rangeItems"
          :model-value="range"
          :content="false"
          size="xs"
          :aria-label="t('dashboard.plotDetail.trend.range')"
          @update:model-value="setRange"
        />
      </div>
    </template>

    <USelect
      :model-value="selectedKey"
      :items="variableItems"
      :aria-label="t('dashboard.plotDetail.trend.variable')"
      class="w-full sm:w-64"
      @update:model-value="setVariable"
    />

    <p v-if="points.length === 0" class="text-sm text-muted">
      {{ t('dashboard.plotDetail.trend.empty') }}
    </p>

    <template v-else>
      <ClientOnly>
        <PlotTrendChart
          :points="points"
          :unit="selected?.unit ?? ''"
          :show-dates="range === '7d'"
        />
        <template #fallback>
          <USkeleton :class="TREND_CHART_HEIGHT_CLASS" class="w-full" />
        </template>
      </ClientOnly>

      <dl class="grid grid-cols-3 gap-3">
        <div
          v-for="stat in statItems"
          :key="stat.key"
          class="rounded-lg bg-elevated/50 p-3"
        >
          <dt class="text-xs text-muted">{{ stat.label }}</dt>
          <dd class="text-lg font-semibold text-highlighted tabular-nums">
            {{ stat.value }}
          </dd>
        </div>
      </dl>
    </template>
  </UCard>
</template>
