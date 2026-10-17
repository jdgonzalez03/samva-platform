<script setup lang="ts">
import { STATION_SPARKLINE_HEIGHT_CLASS } from '../../constants/stations'
import type { WeatherStation } from '../../types/farm'

const props = withDefaults(
  defineProps<{
    station: WeatherStation
    now: number
    headingTag?: 'h2' | 'h3'
  }>(),
  { headingTag: 'h3' },
)

const { t, te, locale } = useI18n()
const localePath = useLocalePath()

const numberFormat = computed(
  () => new Intl.NumberFormat(locale.value, { maximumFractionDigits: 1 }),
)

const dateTimeFormat = computed(
  () =>
    new Intl.DateTimeFormat(locale.value, {
      dateStyle: 'short',
      timeStyle: 'short',
    }),
)

const provider = computed(() => {
  const key = `farm.stations.providers.${props.station.provider}`
  return te(key) ? t(key) : props.station.provider
})

const lastReading = computed(() => {
  const at = props.station.last_reading_at
  if (!at) return null
  return {
    iso: at,
    relative: formatRelativeTime(at, locale.value, props.now),
    absolute: dateTimeFormat.value.format(new Date(at)),
  }
})

const sparklinePoints = computed(() =>
  (props.station.sparkline?.points ?? [])
    .map((point) => ({ t: Date.parse(point.t), value: point.value }))
    .filter((point) => !Number.isNaN(point.t)),
)

// The line is decorative; this text carries what it shows (1.1.1).
const sparklineRange = computed(() => {
  const sparkline = props.station.sparkline
  if (!sparkline || sparklinePoints.value.length < 2) return null
  const values = sparklinePoints.value.map((point) => point.value)
  const format = (value: number) =>
    `${numberFormat.value.format(value)} ${sparkline.unit}`.trim()
  return t('farm.stations.sparkline.range', {
    min: format(Math.min(...values)),
    max: format(Math.max(...values)),
  })
})

const detailPath = computed(() =>
  localePath(`/dashboard/stations/${props.station.id}`),
)
</script>

<template>
  <UCard
    variant="subtle"
    :ui="{ root: 'flex flex-col', body: 'flex flex-1 flex-col gap-4' }"
  >
    <div class="flex flex-wrap items-start justify-between gap-2">
      <div class="flex min-w-0 flex-col gap-0.5">
        <component
          :is="headingTag"
          class="flex items-center gap-2 font-semibold text-highlighted"
        >
          <UIcon
            name="i-lucide-cloud-sun"
            class="shrink-0 text-primary"
            aria-hidden="true"
          />
          <span class="truncate">{{ station.name }}</span>
        </component>
        <p class="text-xs text-muted">{{ provider }}</p>
      </div>
      <StationStatusBadge :status="station.status" />
    </div>

    <p class="text-sm text-muted">
      <template v-if="lastReading">
        {{ t('farm.stations.lastReading') }}
        <time :datetime="lastReading.iso" :title="lastReading.absolute">{{
          lastReading.relative
        }}</time>
      </template>
      <template v-else>{{ t('farm.stations.neverReported') }}</template>
    </p>

    <dl
      v-if="station.latest.length > 0"
      class="grid grid-cols-2 gap-x-4 gap-y-3"
    >
      <div
        v-for="reading in station.latest"
        :key="reading.variable_id"
        class="flex min-w-0 flex-col"
      >
        <dt class="truncate text-xs text-muted" :title="reading.name">
          {{ reading.name }}
        </dt>
        <dd class="font-semibold text-highlighted tabular-nums">
          {{ numberFormat.format(reading.value) }}
          <span class="text-sm font-normal text-muted">{{ reading.unit }}</span>
        </dd>
      </div>
    </dl>
    <p v-else class="text-sm text-muted">{{ t('farm.stations.noReadings') }}</p>

    <div v-if="sparklineRange" class="flex flex-col gap-1">
      <p class="text-xs text-muted">{{ t('farm.stations.sparkline.label') }}</p>
      <div aria-hidden="true">
        <ClientOnly>
          <StationSparkline :points="sparklinePoints" />
          <template #fallback>
            <USkeleton :class="STATION_SPARKLINE_HEIGHT_CLASS" class="w-full" />
          </template>
        </ClientOnly>
      </div>
      <p class="text-xs text-muted">{{ sparklineRange }}</p>
    </div>
    <p v-else-if="station.sparkline" class="text-xs text-muted">
      {{ t('farm.stations.sparkline.empty') }}
    </p>

    <div class="mt-auto flex justify-end">
      <UButton
        :to="detailPath"
        :label="t('farm.stations.detail')"
        :aria-label="t('farm.stations.detailFor', { name: station.name })"
        trailing-icon="i-lucide-arrow-right"
        color="neutral"
        variant="outline"
        size="sm"
      />
    </div>
  </UCard>
</template>
