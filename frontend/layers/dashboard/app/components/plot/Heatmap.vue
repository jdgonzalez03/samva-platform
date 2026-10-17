<script setup lang="ts">
import type { PlotSeries } from '../../../../farm/app/types/farm'
import { HEATMAP_DAYS } from '../../constants/plot-detail'
import { buildHeatmap, toSeriesPoints } from '../../utils/plot-series'

const props = defineProps<{ series: PlotSeries[]; now: number }>()

const { t, locale } = useI18n()

const HOUR_LABELS = [0, 6, 12, 18]
// The faintest filled cell still reads as data against the empty ones.
const MIN_INTENSITY = 12

const selectedKey = ref<string | undefined>(props.series[0]?.semantic_key)
watch(
  () => props.series,
  (series) => {
    if (!series.some((item) => item.semantic_key === selectedKey.value)) {
      selectedKey.value = series[0]?.semantic_key
    }
  },
)

const variableItems = computed(() =>
  props.series.map((item) => ({ label: item.name, value: item.semantic_key })),
)
const selected = computed(() =>
  props.series.find((item) => item.semantic_key === selectedKey.value),
)

const rows = computed(() =>
  buildHeatmap(toSeriesPoints(selected.value), HEATMAP_DAYS, props.now),
)

const extremes = computed(() => {
  let min: { value: number; day: Date; hour: number } | null = null
  let max: { value: number; day: Date; hour: number } | null = null
  for (const row of rows.value) {
    for (const cell of row.cells) {
      if (cell.value === null) continue
      const entry = { value: cell.value, day: row.day, hour: cell.hour }
      if (!min || cell.value < min.value) min = entry
      if (!max || cell.value > max.value) max = entry
    }
  }
  return min && max ? { min, max } : null
})

const dayFormat = computed(
  () =>
    new Intl.DateTimeFormat(locale.value, { weekday: 'short', day: 'numeric' }),
)
const valueFormat = computed(
  () => new Intl.NumberFormat(locale.value, { maximumFractionDigits: 1 }),
)
const withUnit = (value: number): string =>
  `${valueFormat.value.format(value)} ${selected.value?.unit ?? ''}`.trim()

const cellStyle = (value: number | null) => {
  if (value === null || !extremes.value) return undefined
  const { min, max } = extremes.value
  const ratio =
    max.value === min.value ? 1 : (value - min.value) / (max.value - min.value)
  const intensity = MIN_INTENSITY + ratio * (100 - MIN_INTENSITY)
  return {
    backgroundColor: `color-mix(in oklab, var(--ui-primary) ${intensity}%, var(--ui-bg-elevated))`,
  }
}

const cellTitle = (day: Date, hour: number, value: number | null): string => {
  const params = { day: dayFormat.value.format(day), hour }
  return value === null
    ? t('dashboard.plotDetail.heatmap.noValue', params)
    : t('dashboard.plotDetail.heatmap.cell', {
        ...params,
        value: withUnit(value),
      })
}

const summary = computed(() => {
  if (!extremes.value) return ''
  const { min, max } = extremes.value
  return t('dashboard.plotDetail.heatmap.summary', {
    value: withUnit(max.value),
    day: dayFormat.value.format(max.day),
    hour: max.hour,
    minValue: withUnit(min.value),
    minDay: dayFormat.value.format(min.day),
    minHour: min.hour,
  })
})
</script>

<template>
  <UCard variant="subtle" :ui="{ body: 'flex flex-col gap-4' }">
    <template #header>
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex flex-col gap-1">
          <h2 class="flex items-center gap-2 font-semibold text-highlighted">
            <UIcon
              name="i-lucide-grid-3x3"
              class="text-primary"
              aria-hidden="true"
            />
            {{ t('dashboard.plotDetail.heatmap.title') }}
          </h2>
          <p class="text-sm text-muted">
            {{ t('dashboard.plotDetail.heatmap.description') }}
          </p>
        </div>
        <USelect
          v-model="selectedKey"
          :items="variableItems"
          :aria-label="t('dashboard.plotDetail.heatmap.variable')"
          class="min-w-48"
        />
      </div>
    </template>

    <p v-if="!extremes" class="text-sm text-muted">
      {{ t('dashboard.plotDetail.heatmap.empty') }}
    </p>

    <template v-else>
      <div class="overflow-x-auto">
        <!-- The summary below states the extremes in text, so the grid itself
             is decorative for assistive technology. -->
        <div
          aria-hidden="true"
          class="grid min-w-[36rem] grid-cols-[4.5rem_repeat(24,minmax(0,1fr))] gap-1"
        >
          <template v-for="row in rows" :key="row.day.getTime()">
            <span
              class="self-center truncate pe-2 text-xs capitalize text-muted"
              aria-hidden="true"
            >
              {{ dayFormat.format(row.day) }}
            </span>
            <span
              v-for="cell in row.cells"
              :key="cell.hour"
              :title="cellTitle(row.day, cell.hour, cell.value)"
              :style="cellStyle(cell.value)"
              :class="
                cell.value === null ? 'border border-dashed border-default' : ''
              "
              class="aspect-square rounded-sm"
              aria-hidden="true"
            />
          </template>
          <span aria-hidden="true" />
          <span
            v-for="hour in 24"
            :key="`hour-${hour}`"
            class="text-center text-[0.65rem] text-muted"
            aria-hidden="true"
          >
            {{ HOUR_LABELS.includes(hour - 1) ? `${hour - 1}h` : '' }}
          </span>
        </div>
      </div>

      <div
        class="flex flex-wrap items-center justify-between gap-3 text-xs text-muted"
      >
        <p>{{ summary }}</p>
        <div class="flex items-center gap-2" aria-hidden="true">
          <span>{{ t('dashboard.plotDetail.heatmap.less') }}</span>
          <span
            class="h-2 w-28 rounded-full"
            style="
              background: linear-gradient(
                to right,
                color-mix(
                  in oklab,
                  var(--ui-primary) 12%,
                  var(--ui-bg-elevated)
                ),
                var(--ui-primary)
              );
            "
          />
          <span>{{ t('dashboard.plotDetail.heatmap.more') }}</span>
        </div>
      </div>
    </template>
  </UCard>
</template>
