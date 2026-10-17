<script setup lang="ts">
import type { FarmOverview } from '../../../../farm/app/types/farm'
import { LEVEL_COLORS } from '../../constants/plot-detail'
import { plotSeriesPoints } from '../../utils/farm-overview'
import { pointsWithinHours } from '../../utils/plot-series'

const props = defineProps<{
  overview: FarmOverview
  colors: Map<number, string>
  now: number
}>()

const { t, locale } = useI18n()
const localePath = useLocalePath()

const rows = computed(() => {
  const format = new Intl.NumberFormat(locale.value, {
    maximumFractionDigits: 1,
  })
  return props.overview.plots
    .map((plot) => {
      const moisture = plot.conditions.find(
        (condition) => condition.semantic_key === 'soil_moisture',
      )
      return {
        id: plot.id,
        name: plot.name,
        color: props.colors.get(plot.id) ?? 'var(--ui-primary)',
        to: localePath(`/dashboard/plots/${plot.id}`),
        moisture: moisture?.value ?? null,
        moistureText: moisture
          ? `${format.format(moisture.value)} ${moisture.unit}`
          : t('dashboard.home.ranking.noData'),
        level: moisture?.level
          ? {
              label: t(
                `dashboard.plotDetail.conditions.levels.${moisture.level}`,
              ),
              color: LEVEL_COLORS.soil_moisture![moisture.level],
            }
          : null,
        irrigation: plot.irrigation
          ? t('dashboard.home.ranking.irrigation', {
              value: format.format(plot.irrigation.irrigation_time_minutes),
            })
          : t('dashboard.home.ranking.noIrrigation'),
        points: pointsWithinHours(
          plotSeriesPoints(plot, 'soil_moisture'),
          24,
          props.now,
        ),
      }
    })
    .sort(
      (a, b) =>
        (a.moisture ?? Number.POSITIVE_INFINITY) -
        (b.moisture ?? Number.POSITIVE_INFINITY),
    )
})
</script>

<template>
  <UCard variant="subtle" class="h-full">
    <template #header>
      <div class="flex flex-col gap-0.5">
        <h2 class="flex items-center gap-2 font-semibold text-highlighted">
          <UIcon
            name="i-lucide-list-ordered"
            class="text-primary"
            aria-hidden="true"
          />
          {{ t('dashboard.home.ranking.title') }}
        </h2>
        <p class="text-xs text-muted">
          {{ t('dashboard.home.ranking.subtitle') }}
        </p>
      </div>
    </template>

    <ul class="flex flex-col gap-1">
      <li v-for="row in rows" :key="row.id">
        <ULink
          :to="row.to"
          class="grid grid-cols-[auto_1fr_auto] items-center gap-3 rounded-lg p-2 -mx-2 hover:bg-elevated/60 focus-visible:outline-2 focus-visible:outline-primary"
        >
          <span
            class="size-3 rounded-full ring-2 ring-default"
            :style="{ backgroundColor: row.color }"
            aria-hidden="true"
          />
          <span class="flex min-w-0 flex-col">
            <span class="truncate font-medium text-highlighted">{{
              row.name
            }}</span>
            <span class="text-xs text-muted">{{ row.irrigation }}</span>
          </span>
          <span class="flex items-center gap-3">
            <span class="hidden w-20 sm:block" aria-hidden="true">
              <ClientOnly v-if="row.points.length > 1">
                <PlotSparkline :points="row.points" />
              </ClientOnly>
            </span>
            <span class="flex flex-col items-end gap-1">
              <span class="font-semibold tabular-nums text-highlighted">
                {{ row.moistureText }}
              </span>
              <UBadge
                v-if="row.level"
                :label="row.level.label"
                :color="row.level.color"
                variant="subtle"
                size="sm"
              />
            </span>
          </span>
        </ULink>
      </li>
    </ul>
  </UCard>
</template>
