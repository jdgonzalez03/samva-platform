<script setup lang="ts">
import type { FarmOverview } from '../../../../farm/app/types/farm'
import { plotsHeatmap } from '../../utils/farm-overview'

const props = defineProps<{ overview: FarmOverview; now: number }>()

const { t, locale } = useI18n()

const HOURS = 24
// The faintest filled cell still reads as data against the empty ones.
const MIN_INTENSITY = 12

const variableItems = computed(() =>
  props.overview.series.map((series) => ({
    label: series.name,
    value: series.semantic_key,
  })),
)
const selectedKey = ref<string | undefined>(
  props.overview.series.find(
    (series) => series.semantic_key === 'soil_moisture',
  )?.semantic_key ?? props.overview.series[0]?.semantic_key,
)
const unit = computed(
  () =>
    props.overview.series.find(
      (series) => series.semantic_key === selectedKey.value,
    )?.unit ?? '',
)

const rows = computed(() =>
  plotsHeatmap(props.overview.plots, selectedKey.value ?? '', HOURS, props.now),
)
const hourLabels = computed(() => rows.value[0]?.cells ?? [])

const extremes = computed(() => {
  let min: { value: number; plot: string; hour: number } | null = null
  let max: { value: number; plot: string; hour: number } | null = null
  for (const row of rows.value) {
    for (const cell of row.cells) {
      if (cell.value === null) continue
      const entry = { value: cell.value, plot: row.plotName, hour: cell.hour }
      if (!min || cell.value < min.value) min = entry
      if (!max || cell.value > max.value) max = entry
    }
  }
  return min && max ? { min, max } : null
})

const valueFormat = computed(
  () => new Intl.NumberFormat(locale.value, { maximumFractionDigits: 1 }),
)
const withUnit = (value: number): string =>
  `${valueFormat.value.format(value)} ${unit.value}`.trim()

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

const cellTitle = (plot: string, hour: number, value: number | null): string =>
  value === null
    ? t('dashboard.home.heatmap.noValue', { plot, hour })
    : t('dashboard.home.heatmap.cell', { plot, hour, value: withUnit(value) })

const summary = computed(() => {
  if (!extremes.value) return ''
  const { min, max } = extremes.value
  return t('dashboard.home.heatmap.summary', {
    value: withUnit(max.value),
    plot: max.plot,
    hour: max.hour,
    minValue: withUnit(min.value),
    minPlot: min.plot,
    minHour: min.hour,
  })
})
</script>

<template>
  <UCard
    variant="subtle"
    class="shrink-0"
    :ui="{ body: 'flex flex-col gap-4' }"
  >
    <template #header>
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="flex flex-col gap-1">
          <h2 class="flex items-center gap-2 font-semibold text-highlighted">
            <UIcon
              name="i-lucide-grid-3x3"
              class="text-primary"
              aria-hidden="true"
            />
            {{ t('dashboard.home.heatmap.title') }}
          </h2>
          <p class="text-sm text-muted">
            {{ t('dashboard.home.heatmap.description') }}
          </p>
        </div>
        <USelect
          v-model="selectedKey"
          :items="variableItems"
          :aria-label="t('dashboard.home.heatmap.variable')"
          class="w-52"
        />
      </div>
    </template>

    <p v-if="!extremes" class="text-sm text-muted">
      {{ t('dashboard.home.heatmap.empty') }}
    </p>

    <template v-else>
      <div class="overflow-x-auto">
        <!-- The summary below states the extremes in text, so the grid itself
             is decorative for assistive technology. -->
        <div
          aria-hidden="true"
          class="grid min-w-[40rem] grid-cols-[9rem_repeat(24,minmax(0,1fr))] gap-1"
        >
          <template v-for="row in rows" :key="row.plotId">
            <span class="self-center truncate pe-2 text-xs text-muted">
              {{ row.plotName }}
            </span>
            <span
              v-for="cell in row.cells"
              :key="cell.slot"
              :title="cellTitle(row.plotName, cell.hour, cell.value)"
              :style="cellStyle(cell.value)"
              :class="
                cell.value === null ? 'border border-dashed border-default' : ''
              "
              class="h-7 rounded-sm"
            />
          </template>
          <span />
          <span
            v-for="(cell, index) in hourLabels"
            :key="`hour-${cell.slot}`"
            class="text-center text-[0.65rem] text-muted"
          >
            {{ index % 3 === 0 ? `${cell.hour}h` : '' }}
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
            class="h-2 w-28 rounded-full bg-linear-to-r from-[color-mix(in_oklab,var(--ui-primary)_12%,var(--ui-bg-elevated))] to-primary"
          />
          <span>{{ t('dashboard.plotDetail.heatmap.more') }}</span>
        </div>
      </div>
    </template>
  </UCard>
</template>
