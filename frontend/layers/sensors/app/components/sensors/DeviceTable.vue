<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type { FieldSensor, FieldSensorStatus } from '../../types/sensors'

const props = defineProps<{
  farmName: string
  sensors: FieldSensor[]
  now: number
}>()

const { t, locale } = useI18n()

const STATUS_COLOR: Record<
  FieldSensorStatus,
  'success' | 'warning' | 'neutral'
> = {
  online: 'success',
  offline: 'warning',
  never_seen: 'neutral',
  inactive: 'neutral',
}

const STATUS_ICON: Record<FieldSensorStatus, string> = {
  online: 'i-lucide-wifi',
  offline: 'i-lucide-wifi-off',
  never_seen: 'i-lucide-circle-dashed',
  inactive: 'i-lucide-power-off',
}

const columns = computed<TableColumn<FieldSensor>[]>(() => [
  { accessorKey: 'name', header: t('sensors.devices.table.name') },
  {
    accessorKey: 'serial_number',
    header: t('sensors.devices.table.serial'),
  },
  { accessorKey: 'plot_name', header: t('sensors.devices.table.plot') },
  { id: 'variables', header: t('sensors.devices.table.variables') },
  { accessorKey: 'status', header: t('sensors.devices.table.status') },
  {
    accessorKey: 'last_seen_at',
    header: t('sensors.devices.table.lastSeen'),
  },
])

const caption = computed(() =>
  t('sensors.devices.table.caption', { farm: props.farmName }),
)

const dateTimeFormatter = computed(
  () =>
    new Intl.DateTimeFormat(locale.value, {
      dateStyle: 'short',
      timeStyle: 'short',
    }),
)
</script>

<template>
  <UTable
    :data="sensors"
    :columns="columns"
    :caption="caption"
    class="rounded-lg border border-default"
  >
    <template #serial_number-cell="{ row }">
      <code v-if="row.original.serial_number" class="text-sm">{{
        row.original.serial_number
      }}</code>
      <span v-else class="text-muted">{{
        t('sensors.devices.table.noSerial')
      }}</span>
    </template>
    <template #variables-cell="{ row }">
      <div class="flex flex-wrap gap-1">
        <UBadge
          v-for="variable in row.original.variables"
          :key="variable.semantic_key + variable.name"
          color="neutral"
          variant="subtle"
          size="sm"
        >
          {{ variable.name }} ({{ variable.unit }})
        </UBadge>
      </div>
    </template>
    <template #status-cell="{ row }">
      <UBadge
        :color="STATUS_COLOR[row.original.status]"
        :icon="STATUS_ICON[row.original.status]"
        variant="subtle"
      >
        {{ t(`sensors.devices.status.${row.original.status}`) }}
      </UBadge>
    </template>
    <template #last_seen_at-cell="{ row }">
      <time
        v-if="row.original.last_seen_at"
        :datetime="row.original.last_seen_at"
        :title="dateTimeFormatter.format(new Date(row.original.last_seen_at))"
      >
        {{ formatRelativeTime(row.original.last_seen_at, locale, now) }}
      </time>
      <span v-else class="text-muted">{{
        t('sensors.devices.table.never')
      }}</span>
    </template>
  </UTable>
</template>
