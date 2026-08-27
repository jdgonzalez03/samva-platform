<script setup lang="ts">
import type { WeatherReading } from '../../../../farm/app/types/farm'
import { WEATHER_STALE_AFTER_MINUTES } from '../../constants/weather'

const props = defineProps<{
  title: string
  icon: string
  reading: WeatherReading | undefined
  pending: boolean
  error: boolean
  now: number
}>()

const emit = defineEmits<{ retry: [] }>()

const { t, locale } = useI18n()

const elapsedMs = computed(() =>
  props.reading ? props.now - Date.parse(props.reading.recorded_at) : null,
)

// The age and the staleness flag are derived from the same instant, so they
// cannot drift apart while the page sits open.
const isStale = computed(
  () =>
    elapsedMs.value !== null &&
    elapsedMs.value > WEATHER_STALE_AFTER_MINUTES * 60 * 1000,
)

const formattedValue = computed(() =>
  props.reading
    ? new Intl.NumberFormat(locale.value, { maximumFractionDigits: 2 }).format(
        props.reading.value,
      )
    : '',
)

const age = computed(() =>
  props.reading
    ? formatRelativeTime(props.reading.recorded_at, locale.value, props.now)
    : '',
)
</script>

<template>
  <DashboardStatCard :title="title" :icon="icon">
    <div v-if="pending" aria-busy="true">
      <USkeleton class="h-8 w-24" />
    </div>

    <div
      v-else-if="error"
      role="alert"
      class="flex flex-wrap items-center gap-2 text-sm text-muted"
    >
      <span>{{ t('dashboard.stats.error') }}</span>
      <UButton
        variant="link"
        color="neutral"
        size="xs"
        class="p-0"
        @click="emit('retry')"
      >
        {{ t('dashboard.retry') }}
      </UButton>
    </div>

    <p v-else-if="!reading" class="text-2xl font-semibold text-highlighted">
      {{ t('dashboard.stats.noData') }}
    </p>

    <div v-else class="flex flex-col gap-1">
      <p class="flex flex-wrap items-baseline gap-1">
        <span class="text-2xl font-semibold text-highlighted">
          {{ formattedValue }}
        </span>
        <span class="text-sm text-muted">{{ reading.unit }}</span>
      </p>
      <div class="flex flex-wrap items-center gap-2">
        <span class="text-xs text-muted">
          {{ t('dashboard.stats.updated', { age }) }}
        </span>
        <UBadge
          v-if="isStale"
          variant="subtle"
          color="neutral"
          icon="i-lucide-clock"
          size="sm"
        >
          {{ t('dashboard.stats.stale') }}
        </UBadge>
      </div>
    </div>
  </DashboardStatCard>
</template>
