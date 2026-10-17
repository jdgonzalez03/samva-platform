<script setup lang="ts">
import type { FarmOverview, Plot } from '../../../../farm/app/types/farm'

const props = defineProps<{
  plots: Plot[]
  plotsPending: boolean
  plotsError: boolean
  overview: FarmOverview | undefined
  alertCount: number | null
}>()

const { t, locale } = useI18n()

const totalArea = computed(() => {
  const area = props.plots.reduce(
    (sum, plot) => sum + Number(plot.area_hectares ?? 0),
    0,
  )
  return t('dashboard.home.stats.areaValue', {
    value: new Intl.NumberFormat(locale.value, {
      maximumFractionDigits: 1,
    }).format(area),
  })
})

const sensorsOnline = computed(() => {
  const sensors = props.overview?.sensors ?? []
  const online = sensors.filter((sensor) => sensor.status === 'online').length
  return {
    online,
    total: sensors.length,
    percent: sensors.length ? (online / sensors.length) * 100 : 0,
  }
})
</script>

<template>
  <UPageGrid class="lg:grid-cols-4 gap-4 sm:gap-6 lg:gap-px">
    <DashboardStatCard :title="t('dashboard.stats.plots')" icon="i-lucide-map">
      <div v-if="plotsPending" aria-busy="true">
        <USkeleton class="h-8 w-16" />
      </div>
      <p v-else class="text-2xl font-semibold text-highlighted">
        {{ plotsError ? t('dashboard.stats.noData') : plots.length }}
      </p>
    </DashboardStatCard>

    <DashboardStatCard
      :title="t('dashboard.home.stats.area')"
      icon="i-lucide-ruler"
    >
      <div v-if="plotsPending" aria-busy="true">
        <USkeleton class="h-8 w-20" />
      </div>
      <p v-else class="text-2xl font-semibold text-highlighted">
        {{ plotsError ? t('dashboard.stats.noData') : totalArea }}
      </p>
    </DashboardStatCard>

    <DashboardStatCard
      :title="t('dashboard.home.stats.sensorsOnline')"
      icon="i-lucide-radio-tower"
    >
      <div v-if="!overview" aria-busy="true">
        <USkeleton class="h-8 w-20" />
      </div>
      <div v-else class="flex flex-col gap-2">
        <p class="text-2xl font-semibold text-highlighted">
          {{
            t('dashboard.home.stats.sensorsValue', {
              online: sensorsOnline.online,
              total: sensorsOnline.total,
            })
          }}
        </p>
        <UProgress
          :model-value="sensorsOnline.percent"
          :aria-label="t('dashboard.home.stats.sensorsOnline')"
          size="sm"
        />
      </div>
    </DashboardStatCard>

    <DashboardStatCard
      :title="t('dashboard.home.stats.alerts')"
      icon="i-lucide-bell-ring"
    >
      <div v-if="alertCount === null" aria-busy="true">
        <USkeleton class="h-8 w-12" />
      </div>
      <p
        v-else
        class="text-2xl font-semibold"
        :class="alertCount > 0 ? 'text-warning' : 'text-highlighted'"
      >
        {{ alertCount }}
      </p>
    </DashboardStatCard>
  </UPageGrid>
</template>
