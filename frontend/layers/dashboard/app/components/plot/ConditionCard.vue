<script setup lang="ts">
import type { PlotCondition } from '../../../../farm/app/types/farm'
import {
  CONDITION_ICONS,
  FALLBACK_CONDITION_ICON,
  LEVEL_COLORS,
  SPARKLINE_HEIGHT_CLASS,
} from '../../constants/plot-detail'
import type { SeriesPoint } from '../../utils/plot-series'

const props = defineProps<{
  condition: PlotCondition
  points: SeriesPoint[]
  now: number
}>()

const { t, locale } = useI18n()

const numberFormat = computed(
  () => new Intl.NumberFormat(locale.value, { maximumFractionDigits: 1 }),
)
const signedFormat = computed(
  () =>
    new Intl.NumberFormat(locale.value, {
      maximumFractionDigits: 1,
      signDisplay: 'exceptZero',
    }),
)

const icon = computed(
  () =>
    CONDITION_ICONS[props.condition.semantic_key] ?? FALLBACK_CONDITION_ICON,
)

const level = computed(() => {
  const { level: value, semantic_key: key } = props.condition
  if (!value) return null
  return {
    label: t('dashboard.plotDetail.conditions.level', {
      level: t(`dashboard.plotDetail.conditions.levels.${value}`),
    }),
    color: LEVEL_COLORS[key]?.[value] ?? 'neutral',
  }
})

const trend = computed(() => {
  const change = props.condition.change_24h
  if (change === null) return null
  const rounded = Math.round(change * 10) / 10
  const icon =
    rounded > 0
      ? 'i-lucide-trending-up'
      : rounded < 0
        ? 'i-lucide-trending-down'
        : 'i-lucide-minus'
  return {
    icon,
    label: t('dashboard.plotDetail.conditions.change', {
      value:
        `${signedFormat.value.format(rounded)} ${props.condition.unit}`.trim(),
    }),
  }
})

const recordedAt = computed(() =>
  formatRelativeTime(props.condition.recorded_at, locale.value, props.now),
)
</script>

<template>
  <UCard variant="subtle" :ui="{ body: 'flex flex-col gap-3' }">
    <div class="flex items-center justify-between gap-2">
      <div class="flex items-center gap-2 min-w-0">
        <span
          class="inline-flex size-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary"
          aria-hidden="true"
        >
          <UIcon :name="icon" class="size-4" />
        </span>
        <h3 class="truncate text-sm font-medium text-muted">
          {{ condition.name }}
        </h3>
      </div>
    </div>

    <div class="flex flex-wrap items-baseline justify-between gap-2">
      <p class="text-3xl font-semibold text-highlighted tabular-nums">
        {{ numberFormat.format(condition.value) }}
        <span class="text-base font-normal text-muted">{{
          condition.unit
        }}</span>
      </p>
      <UBadge
        v-if="level"
        :label="level.label"
        :color="level.color"
        variant="subtle"
      />
    </div>

    <div aria-hidden="true">
      <ClientOnly v-if="points.length > 1">
        <PlotSparkline :points="points" />
        <template #fallback>
          <USkeleton :class="SPARKLINE_HEIGHT_CLASS" class="w-full" />
        </template>
      </ClientOnly>
      <div v-else :class="SPARKLINE_HEIGHT_CLASS" />
    </div>

    <div class="flex flex-wrap items-center justify-between gap-2 text-xs">
      <UBadge
        v-if="trend"
        :label="trend.label"
        :icon="trend.icon"
        color="neutral"
        variant="outline"
      />
      <span v-else class="text-muted">
        {{ t('dashboard.plotDetail.conditions.noChange') }}
      </span>
      <span class="text-muted">{{ recordedAt }}</span>
    </div>
  </UCard>
</template>
