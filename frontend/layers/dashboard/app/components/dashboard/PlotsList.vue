<script setup lang="ts">
import type { Plot } from '../../../../farm/app/types/farm'

defineProps<{
  plots: Plot[]
}>()

const { t, locale } = useI18n()
const localePath = useLocalePath()

const formatArea = (areaHectares: string | null): string => {
  if (areaHectares === null) return '—'

  const value = Number(areaHectares)
  if (Number.isNaN(value)) return '—'

  return t('dashboard.plots.area', {
    value: new Intl.NumberFormat(locale.value, {
      maximumFractionDigits: 2,
    }).format(value),
  })
}
</script>

<template>
  <UPageList divide :aria-label="t('dashboard.plots.listLabel')">
    <div v-for="plot in plots" :key="plot.id" role="listitem">
      <ULink
        :to="localePath(`/dashboard/plots/${plot.id}`)"
        :aria-label="plot.name"
        :aria-describedby="`plot-row-${plot.id}`"
        class="flex flex-wrap items-center gap-x-4 gap-y-1 px-3 py-3 min-h-11 w-full rounded-md hover:bg-elevated/50"
      >
        <span class="font-medium text-highlighted">{{ plot.name }}</span>

        <span
          :id="`plot-row-${plot.id}`"
          class="flex flex-wrap items-center gap-x-4 gap-y-1 grow"
        >
          <span class="text-sm text-muted">
            {{ plot.description || t('dashboard.plots.noDescription') }}
          </span>
          <span class="text-sm text-muted">
            {{ formatArea(plot.area_hectares) }}
          </span>
          <UBadge
            variant="subtle"
            color="neutral"
            icon="i-lucide-radio-tower"
            class="ms-auto"
          >
            {{ t('dashboard.plots.sensors', plot.sensor_count) }}
          </UBadge>
        </span>
      </ULink>
    </div>
  </UPageList>
</template>
