<script setup lang="ts">
import type { PlotSummary } from '../../../../farm/app/types/farm'
import { LEVEL_COLORS, STALE_AFTER_MS } from '../../constants/plot-detail'

const props = defineProps<{ plot: PlotSummary; now: number }>()

const { t, locale } = useI18n()
const localePath = useLocalePath()

const numberFormat = computed(
  () => new Intl.NumberFormat(locale.value, { maximumFractionDigits: 1 }),
)

const condition = (key: string) =>
  props.plot.conditions.find((row) => row.semantic_key === key)

const moisture = computed(() => condition('soil_moisture'))
const temperature = computed(() => condition('air_temperature'))

const withUnit = (value: number, unit: string): string =>
  `${numberFormat.value.format(value)} ${unit}`.trim()

const reporting = computed(() => {
  if (props.plot.latest_reading_at === null) {
    return {
      label: t('dashboard.plotDetail.hero.noData'),
      color: 'neutral' as const,
    }
  }
  const stale =
    props.now - Date.parse(props.plot.latest_reading_at) > STALE_AFTER_MS
  return stale
    ? { label: t('dashboard.plotDetail.hero.stale'), color: 'warning' as const }
    : { label: t('dashboard.plotDetail.hero.live'), color: 'success' as const }
})

const stats = computed(() => {
  const noValue = t('dashboard.plotsIndex.card.noValue')
  return [
    {
      key: 'moisture',
      icon: 'i-lucide-sprout',
      label: t('dashboard.plotsIndex.card.moisture'),
      value: moisture.value
        ? withUnit(moisture.value.value, moisture.value.unit)
        : noValue,
    },
    {
      key: 'temperature',
      icon: 'i-lucide-thermometer',
      label: t('dashboard.plotsIndex.card.temperature'),
      value: temperature.value
        ? withUnit(temperature.value.value, temperature.value.unit)
        : noValue,
    },
    {
      key: 'sensors',
      icon: 'i-lucide-radio-tower',
      label: t('dashboard.plotsIndex.card.sensors'),
      value: String(props.plot.sensor_count),
    },
    {
      key: 'area',
      icon: 'i-lucide-ruler',
      label: t('dashboard.plotsIndex.card.area'),
      value:
        props.plot.area_hectares === null
          ? noValue
          : t('dashboard.plotDetail.hero.area', {
              value: numberFormat.value.format(
                Number(props.plot.area_hectares),
              ),
            }),
    },
  ]
})

const moistureLevel = computed(() => {
  const level = moisture.value?.level
  if (!level) return null
  return {
    label: t('dashboard.plotDetail.conditions.level', {
      level: t(`dashboard.plotDetail.conditions.levels.${level}`),
    }),
    color: LEVEL_COLORS.soil_moisture![level],
  }
})

const footer = computed(() =>
  props.plot.latest_reading_at
    ? t('dashboard.plotsIndex.card.lastReading', {
        time: formatRelativeTime(
          props.plot.latest_reading_at,
          locale.value,
          props.now,
        ),
      })
    : t('dashboard.plotsIndex.card.noReadings'),
)
</script>

<template>
  <UPageCard
    :to="localePath(`/dashboard/plots/${plot.id}`)"
    :title="plot.name"
    :description="plot.description || undefined"
    variant="subtle"
    spotlight
    :ui="{
      container: 'gap-y-4',
      title: 'text-lg',
      description: 'line-clamp-2',
    }"
  >
    <template #header>
      <div class="flex flex-wrap items-center justify-between gap-2">
        <UBadge
          :label="plot.farm.name"
          icon="i-lucide-tractor"
          color="neutral"
          variant="subtle"
        />
        <UBadge
          :label="reporting.label"
          :color="reporting.color"
          variant="subtle"
        >
          <template #leading>
            <span class="size-1.5 rounded-full bg-current" aria-hidden="true" />
          </template>
        </UBadge>
      </div>
    </template>

    <dl class="grid grid-cols-2 gap-2">
      <div
        v-for="stat in stats"
        :key="stat.key"
        class="flex flex-col gap-1 rounded-lg bg-elevated/50 p-3"
      >
        <dt class="flex items-center gap-1.5 text-xs text-muted">
          <UIcon
            :name="stat.icon"
            class="size-3.5 text-primary"
            aria-hidden="true"
          />
          {{ stat.label }}
        </dt>
        <dd class="font-semibold tabular-nums text-highlighted">
          {{ stat.value }}
        </dd>
      </div>
    </dl>

    <div class="flex w-full flex-wrap items-center justify-between gap-2">
      <span class="text-xs text-muted">{{ footer }}</span>
      <div class="flex flex-wrap gap-1.5">
        <UBadge
          v-if="moistureLevel"
          :label="moistureLevel.label"
          :color="moistureLevel.color"
          variant="subtle"
          size="sm"
        />
        <UBadge
          v-if="plot.irrigation"
          :label="
            t('dashboard.plotsIndex.card.irrigation', {
              value: numberFormat.format(
                plot.irrigation.irrigation_time_minutes,
              ),
            })
          "
          icon="i-lucide-droplets"
          color="info"
          variant="subtle"
          size="sm"
        />
        <UBadge
          v-if="!plot.has_geometry"
          :label="t('dashboard.plotsIndex.card.noMap')"
          icon="i-lucide-map-pin-off"
          color="neutral"
          variant="outline"
          size="sm"
        />
      </div>
    </div>
  </UPageCard>
</template>
