<script setup lang="ts">
import type {
  FarmOverview,
  PlotSensorStatus,
} from '../../../../farm/app/types/farm'
import type { DonutSegment } from './SensorsDonut.client.vue'

const props = defineProps<{ overview: FarmOverview }>()

const { t } = useI18n()

const STATUSES: { key: PlotSensorStatus; color: string }[] = [
  { key: 'online', color: 'var(--ui-success)' },
  { key: 'offline', color: 'var(--ui-warning)' },
  { key: 'never_seen', color: 'var(--ui-info)' },
  { key: 'inactive', color: 'var(--ui-border-accented)' },
]

const segments = computed<DonutSegment[]>(() =>
  STATUSES.map(({ key, color }) => ({
    key,
    color,
    count: props.overview.sensors.filter((sensor) => sensor.status === key)
      .length,
  })),
)
const online = computed(
  () => segments.value.find((segment) => segment.key === 'online')!.count,
)
const total = computed(() => props.overview.sensors.length)
</script>

<template>
  <UCard variant="subtle" class="h-full" :ui="{ body: 'flex flex-col gap-4' }">
    <template #header>
      <h2 class="flex items-center gap-2 font-semibold text-highlighted">
        <UIcon
          name="i-lucide-radio-tower"
          class="text-primary"
          aria-hidden="true"
        />
        {{ t('dashboard.home.sensors.title') }}
      </h2>
    </template>

    <p v-if="total === 0" class="text-sm text-muted">
      {{ t('dashboard.home.sensors.empty') }}
    </p>

    <template v-else>
      <div aria-hidden="true">
        <ClientOnly>
          <HomeSensorsDonut
            :segments="segments"
            :central-label="
              t('dashboard.home.sensors.center', { online, total })
            "
            :central-sub-label="t('dashboard.home.sensors.centerLabel')"
          />
          <template #fallback>
            <USkeleton class="mx-auto size-44 rounded-full" />
          </template>
        </ClientOnly>
      </div>
      <ul class="grid grid-cols-2 gap-2 text-sm">
        <li
          v-for="segment in segments"
          :key="segment.key"
          class="flex items-center gap-2"
        >
          <span
            class="size-2.5 shrink-0 rounded-full"
            :style="{ backgroundColor: segment.color }"
            aria-hidden="true"
          />
          <span class="truncate text-muted">
            {{ t(`dashboard.home.sensors.status.${segment.key}`) }}
          </span>
          <span class="ms-auto font-semibold tabular-nums text-highlighted">
            {{ segment.count }}
          </span>
        </li>
      </ul>
    </template>
  </UCard>
</template>
