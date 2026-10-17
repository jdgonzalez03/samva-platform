<script setup lang="ts">
import type { PlotSensor } from '../../../../farm/app/types/farm'
import {
  CONDITION_ICONS,
  FALLBACK_CONDITION_ICON,
  SENSOR_STATUS_COLORS,
} from '../../constants/plot-detail'

const props = defineProps<{ sensors: PlotSensor[]; now: number }>()

const { t, locale } = useI18n()

const rows = computed(() =>
  props.sensors.map((sensor) => ({
    ...sensor,
    statusLabel: t(`dashboard.plotDetail.sensors.status.${sensor.status}`),
    statusColor: SENSOR_STATUS_COLORS[sensor.status],
    lastSeen: sensor.last_seen_at
      ? t('dashboard.plotDetail.sensors.lastSeen', {
          time: formatRelativeTime(
            sensor.last_seen_at,
            locale.value,
            props.now,
          ),
        })
      : t('dashboard.plotDetail.sensors.neverSeen'),
  })),
)
</script>

<template>
  <UCard variant="subtle">
    <template #header>
      <h2 class="flex items-center gap-2 font-semibold text-highlighted">
        <UIcon
          name="i-lucide-radio-tower"
          class="text-primary"
          aria-hidden="true"
        />
        {{ t('dashboard.plotDetail.sensors.title') }}
      </h2>
    </template>

    <p v-if="rows.length === 0" class="text-sm text-muted">
      {{ t('dashboard.plotDetail.sensors.empty') }}
    </p>

    <ul v-else class="flex flex-col divide-y divide-default">
      <li
        v-for="sensor in rows"
        :key="sensor.id"
        class="flex flex-col gap-2 py-3 first:pt-0 last:pb-0"
      >
        <div class="flex items-center justify-between gap-2">
          <div class="min-w-0">
            <p class="truncate font-medium text-highlighted">
              {{ sensor.name }}
            </p>
            <p class="text-xs text-muted">
              {{
                t('dashboard.plotDetail.sensors.serial', {
                  serial: sensor.serial_number,
                })
              }}
            </p>
          </div>
          <UBadge
            :label="sensor.statusLabel"
            :color="sensor.statusColor"
            variant="subtle"
          />
        </div>
        <div class="flex flex-wrap items-center gap-1.5">
          <UBadge
            v-for="variable in sensor.variables"
            :key="variable.semantic_key"
            :label="variable.name"
            :icon="
              CONDITION_ICONS[variable.semantic_key] ?? FALLBACK_CONDITION_ICON
            "
            color="neutral"
            variant="outline"
            size="sm"
          />
        </div>
        <p class="text-xs text-muted">{{ sensor.lastSeen }}</p>
      </li>
    </ul>
  </UCard>
</template>
