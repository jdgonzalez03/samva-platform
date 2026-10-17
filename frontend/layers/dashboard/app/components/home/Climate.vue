<script setup lang="ts">
import type { FarmOverview } from '../../../../farm/app/types/farm'
import {
  CONDITION_ICONS,
  FALLBACK_CONDITION_ICON,
  TREND_CHART_HEIGHT_CLASS,
} from '../../constants/plot-detail'
import { dailyStats } from '../../utils/farm-overview'
import { toSeriesPoints } from '../../utils/plot-series'

const props = defineProps<{ overview: FarmOverview }>()

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
    (series) => series.semantic_key === 'air_temperature',
  )?.semantic_key ?? props.overview.series[0]?.semantic_key,
)
const selected = computed(() =>
  props.overview.series.find(
    (series) => series.semantic_key === selectedKey.value,
  ),
)
const days = computed(() => dailyStats(toSeriesPoints(selected.value)))

const labels = computed(() => ({
  min: t('dashboard.home.climate.min'),
  average: t('dashboard.home.climate.average'),
  max: t('dashboard.home.climate.max'),
}))
const legend = computed(() => [
  { label: labels.value.min, color: 'var(--ui-info)' },
  { label: labels.value.average, color: 'var(--ui-primary)' },
  { label: labels.value.max, color: 'var(--ui-warning)' },
])

const alternative = computed(() => {
  const unit = selected.value?.unit ?? ''
  const value = new Intl.NumberFormat(locale.value, {
    maximumFractionDigits: 1,
  })
  const day = new Intl.DateTimeFormat(locale.value, {
    weekday: 'long',
    day: 'numeric',
  })
  return days.value.map((row) =>
    t('dashboard.home.climate.alternative', {
      day: day.format(row.day),
      min: `${value.format(row.min)} ${unit}`.trim(),
      average: `${value.format(row.average)} ${unit}`.trim(),
      max: `${value.format(row.max)} ${unit}`.trim(),
    }),
  )
})
</script>

<template>
  <UCard variant="subtle" class="shrink-0" :ui="{ body: 'flex flex-col gap-4' }">
    <template #header>
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex flex-col gap-1">
          <h2 class="flex items-center gap-2 font-semibold text-highlighted">
            <UIcon
              name="i-lucide-calendar-days"
              class="text-primary"
              aria-hidden="true"
            />
            {{ t('dashboard.home.climate.title') }}
          </h2>
          <p class="text-sm text-muted">
            {{ t('dashboard.home.climate.description') }}
          </p>
        </div>
        <USelect
          v-model="selectedKey"
          :items="variableItems"
          :aria-label="t('dashboard.home.climate.variable')"
          class="w-52"
        />
      </div>
    </template>

    <p v-if="days.length === 0" class="text-sm text-muted">
      {{ t('dashboard.home.climate.empty') }}
    </p>

    <template v-else>
      <div aria-hidden="true">
        <ClientOnly>
          <HomeClimateChart
            :days="days"
            :unit="selected?.unit ?? ''"
            :labels="labels"
          />
          <template #fallback>
            <USkeleton :class="TREND_CHART_HEIGHT_CLASS" class="w-full" />
          </template>
        </ClientOnly>
      </div>
      <ul class="flex flex-wrap gap-x-4 gap-y-1 text-sm" aria-hidden="true">
        <li
          v-for="item in legend"
          :key="item.label"
          class="flex items-center gap-2"
        >
          <span
            class="size-2.5 rounded-sm"
            :style="{ backgroundColor: item.color }"
          />
          {{ item.label }}
        </li>
      </ul>
      <ul class="sr-only">
        <li v-for="line in alternative" :key="line">{{ line }}</li>
      </ul>
    </template>
  </UCard>
</template>
