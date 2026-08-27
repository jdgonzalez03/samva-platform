<script setup lang="ts">
import type { FarmWeather } from '../../../../farm/app/types/farm'
import { WEATHER_TICK_MS } from '../../constants/weather'

const props = defineProps<{
  plotCount: number
  sensorCount: number
  countsPending: boolean
  countsError: boolean
  weather: FarmWeather | undefined
  weatherPending: boolean
  weatherError: boolean
}>()

const emit = defineEmits<{ retryWeather: [] }>()

const { t, locale } = useI18n()
const now = useNow(WEATHER_TICK_MS)

const formatCount = (value: number) =>
  new Intl.NumberFormat(locale.value).format(value)

const counts = computed(() => [
  {
    key: 'plots',
    title: t('dashboard.stats.plots'),
    icon: 'i-lucide-map',
    value: formatCount(props.plotCount),
  },
  {
    key: 'sensors',
    title: t('dashboard.stats.sensors'),
    icon: 'i-lucide-radio-tower',
    value: formatCount(props.sensorCount),
  },
])
</script>

<template>
  <UPageGrid class="lg:grid-cols-4 gap-4 sm:gap-6 lg:gap-px">
    <DashboardStatCard
      v-for="count in counts"
      :key="count.key"
      :title="count.title"
      :icon="count.icon"
    >
      <div v-if="countsPending" aria-busy="true">
        <USkeleton class="h-8 w-16" />
      </div>
      <p v-else class="text-2xl font-semibold text-highlighted">
        {{ countsError ? t('dashboard.stats.noData') : count.value }}
      </p>
    </DashboardStatCard>

    <DashboardWeatherStatCard
      :title="t('dashboard.stats.temperature')"
      icon="i-lucide-thermometer"
      :reading="weather?.air_temperature"
      :pending="weatherPending"
      :error="weatherError"
      :now="now"
      @retry="emit('retryWeather')"
    />

    <DashboardWeatherStatCard
      :title="t('dashboard.stats.radiation')"
      icon="i-lucide-sun"
      :reading="weather?.solar_radiation"
      :pending="weatherPending"
      :error="weatherError"
      :now="now"
      @retry="emit('retryWeather')"
    />
  </UPageGrid>
</template>
