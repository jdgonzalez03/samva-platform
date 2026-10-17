<script setup lang="ts">
import type { FarmOverview } from '../../../../farm/app/types/farm'

const props = defineProps<{
  overview: FarmOverview
  colors: Map<number, string>
}>()

const { t, locale } = useI18n()
const localePath = useLocalePath()

const numberFormat = computed(
  () => new Intl.NumberFormat(locale.value, { maximumFractionDigits: 1 }),
)

const calculated = computed(() =>
  props.overview.plots
    .filter((plot) => plot.irrigation)
    .map((plot) => ({
      id: plot.id,
      name: plot.name,
      color: props.colors.get(plot.id) ?? 'var(--ui-primary)',
      minutes: plot.irrigation!.irrigation_time_minutes,
      label: t(
        `dashboard.plotDetail.irrigation.labels.${plot.irrigation!.output_label}`,
      ),
    }))
    .sort((a, b) => b.minutes - a.minutes),
)
const pending = computed(() =>
  props.overview.plots.filter((plot) => !plot.irrigation),
)

// Bars are relative to the longest recommendation, with a floor so a
// near-zero one still shows as a sliver rather than vanishing.
const maxMinutes = computed(() =>
  Math.max(...calculated.value.map((row) => row.minutes), 1),
)
const barWidth = (minutes: number): string =>
  `${Math.max((minutes / maxMinutes.value) * 100, 2)}%`

const total = computed(() =>
  numberFormat.value.format(
    calculated.value.reduce((sum, row) => sum + row.minutes, 0),
  ),
)
const summary = computed(() =>
  t('dashboard.home.irrigation.alternative', {
    list: calculated.value
      .map((row) => `${row.name} ${numberFormat.value.format(row.minutes)} min`)
      .join(', '),
  }),
)
const calculateLink = computed(() =>
  localePath({
    path: '/dashboard/predictions/fuzzy',
    query: pending.value[0] ? { plot: String(pending.value[0].id) } : {},
  }),
)
</script>

<template>
  <UCard variant="subtle" class="h-full" :ui="{ body: 'flex flex-col gap-4' }">
    <template #header>
      <div class="flex flex-wrap items-center justify-between gap-2">
        <h2 class="flex items-center gap-2 font-semibold text-highlighted">
          <UIcon
            name="i-lucide-droplets"
            class="text-primary"
            aria-hidden="true"
          />
          {{ t('dashboard.home.irrigation.title') }}
        </h2>
        <UBadge
          v-if="calculated.length > 0"
          :label="t('dashboard.home.irrigation.total', { value: total })"
          variant="subtle"
        />
      </div>
    </template>

    <UEmpty
      v-if="calculated.length === 0"
      icon="i-lucide-droplets"
      :description="t('dashboard.home.irrigation.empty')"
      :actions="[
        {
          label: t('dashboard.home.irrigation.calculate'),
          icon: 'i-lucide-calculator',
          to: calculateLink,
        },
      ]"
      variant="naked"
    />

    <template v-else>
      <ul class="flex flex-col gap-3" aria-hidden="true">
        <li v-for="row in calculated" :key="row.id" class="flex flex-col gap-1">
          <div class="flex items-center justify-between gap-2 text-sm">
            <span class="truncate font-medium text-highlighted">{{
              row.name
            }}</span>
            <span class="shrink-0 text-muted">
              <span class="font-semibold tabular-nums text-highlighted">
                {{ numberFormat.format(row.minutes) }} min
              </span>
              · {{ row.label }}
            </span>
          </div>
          <div class="h-2.5 w-full overflow-hidden rounded-full bg-elevated">
            <div
              class="h-full rounded-full transition-[width] duration-500"
              :style="{
                width: barWidth(row.minutes),
                backgroundColor: row.color,
              }"
            />
          </div>
        </li>
      </ul>
      <p class="sr-only">{{ summary }}</p>
      <p v-if="pending.length > 0" class="text-xs text-muted">
        {{
          t('dashboard.home.irrigation.pending', {
            plots: pending.map((plot) => plot.name).join(', '),
          })
        }}
      </p>
    </template>
  </UCard>
</template>
