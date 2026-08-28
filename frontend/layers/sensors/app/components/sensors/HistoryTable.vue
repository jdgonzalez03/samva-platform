<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import { HISTORY_PAGE_SIZE } from '../../constants/history'
import type { SensorReading } from '../../types/sensors'

const props = defineProps<{
  farmName: string
  readings: SensorReading[]
  count: number
  pending: boolean
  isPlaceholder: boolean
  showPlotColumn: boolean
}>()

const page = defineModel<number>('page', { required: true })

const { t, locale } = useI18n()

const dateTimeFormatter = computed(
  () =>
    new Intl.DateTimeFormat(locale.value, {
      dateStyle: 'short',
      timeStyle: 'short',
    }),
)

const numberFormatter = computed(
  () => new Intl.NumberFormat(locale.value, { maximumFractionDigits: 2 }),
)

// Sorting is server-side or nothing: TanStack's client sort would reorder only
// the twenty rows on screen and quietly claim to have sorted the whole set.
const columns = computed<TableColumn<SensorReading>[]>(() => [
  { accessorKey: 'recorded_at', header: t('sensors.history.table.recordedAt') },
  ...(props.showPlotColumn
    ? [
        {
          accessorKey: 'plot_name',
          header: t('sensors.history.table.plot'),
        } satisfies TableColumn<SensorReading>,
      ]
    : []),
  { accessorKey: 'sensor_name', header: t('sensors.history.table.sensor') },
  { accessorKey: 'variable_name', header: t('sensors.history.table.variable') },
  {
    accessorKey: 'value',
    header: t('sensors.history.table.value'),
    meta: {
      class: { th: 'text-right rtl:text-left', td: 'text-right tabular-nums' },
    },
  },
  { accessorKey: 'unit', header: t('sensors.history.table.unit') },
])

const caption = computed(() =>
  t(
    'sensors.history.table.caption',
    { farm: props.farmName, count: numberFormatter.value.format(props.count) },
    props.count,
  ),
)

const loading = computed(() => props.pending || props.isPlaceholder)

// Reka labels the controls in English ("First Page", "Page 3"), so each slot
// exists only to hand the button a translated `aria-label`.
const controlButton = 'min-h-8 min-w-8'
</script>

<template>
  <div class="flex flex-col gap-4">
    <UEmpty
      v-if="count === 0 && !pending"
      icon="i-lucide-table"
      :description="t('sensors.history.table.empty')"
    />

    <template v-else>
      <UTable
        :data="readings"
        :columns="columns"
        :caption="caption"
        :loading="loading"
        :aria-busy="loading"
        class="rounded-lg border border-default transition-opacity"
        :class="isPlaceholder && 'opacity-60'"
      >
        <template #recorded_at-cell="{ row }">
          {{ dateTimeFormatter.format(new Date(row.original.recorded_at)) }}
        </template>
        <template #value-cell="{ row }">
          {{ numberFormatter.format(row.original.value) }}
        </template>
      </UTable>

      <UPagination
        v-if="count > HISTORY_PAGE_SIZE"
        v-model:page="page"
        :items-per-page="HISTORY_PAGE_SIZE"
        :total="count"
        :sibling-count="1"
        show-edges
        :aria-label="t('sensors.history.pagination.label')"
        class="justify-center"
      >
        <template #item="{ item, page: current }">
          <!-- Ellipses never reach this slot; the guard narrows the union type. -->
          <UButton
            v-if="item.type === 'page'"
            :color="current === item.value ? 'primary' : 'neutral'"
            :variant="current === item.value ? 'solid' : 'outline'"
            :label="String(item.value)"
            :aria-label="
              t('sensors.history.pagination.page', { page: item.value })
            "
            :class="controlButton"
            square
          />
        </template>
        <template #first>
          <UButton
            icon="i-lucide-chevrons-left"
            color="neutral"
            variant="outline"
            :aria-label="t('sensors.history.pagination.first')"
            :class="controlButton"
          />
        </template>
        <template #prev>
          <UButton
            icon="i-lucide-chevron-left"
            color="neutral"
            variant="outline"
            :aria-label="t('sensors.history.pagination.prev')"
            :class="controlButton"
          />
        </template>
        <template #next>
          <UButton
            icon="i-lucide-chevron-right"
            color="neutral"
            variant="outline"
            :aria-label="t('sensors.history.pagination.next')"
            :class="controlButton"
          />
        </template>
        <template #last>
          <UButton
            icon="i-lucide-chevrons-right"
            color="neutral"
            variant="outline"
            :aria-label="t('sensors.history.pagination.last')"
            :class="controlButton"
          />
        </template>
      </UPagination>
    </template>
  </div>
</template>
