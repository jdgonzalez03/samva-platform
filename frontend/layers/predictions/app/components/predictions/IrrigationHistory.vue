<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type { IrrigationPrediction } from '../../types/predictions'

defineProps<{
  predictions: IrrigationPrediction[]
  pending: boolean
  error: boolean
}>()

const emit = defineEmits<{ retry: [] }>()

const { t, locale } = useI18n()

const dateFormat = computed(
  () =>
    new Intl.DateTimeFormat(locale.value, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }),
)
const numberFormat = computed(
  () => new Intl.NumberFormat(locale.value, { maximumFractionDigits: 1 }),
)

const columns = computed<TableColumn<IrrigationPrediction>[]>(() => [
  {
    accessorKey: 'requested_at',
    header: t('predictions.fuzzy.history.date'),
    cell: ({ row }) =>
      dateFormat.value.format(new Date(row.original.requested_at)),
  },
  {
    accessorKey: 'irrigation_time_minutes',
    header: t('predictions.fuzzy.history.minutes'),
    cell: ({ row }) =>
      numberFormat.value.format(row.original.irrigation_time_minutes),
  },
  {
    accessorKey: 'output_label',
    header: t('predictions.fuzzy.history.label'),
    cell: ({ row }) =>
      t(`predictions.fuzzy.labels.${row.original.output_label}`),
  },
  {
    accessorKey: 'avg_period_hours',
    header: t('predictions.fuzzy.history.window'),
    cell: ({ row }) =>
      t('predictions.fuzzy.hoursOption', {
        hours: row.original.avg_period_hours,
      }),
  },
])
</script>

<template>
  <section class="flex flex-col gap-3">
    <h2 class="text-base font-semibold text-highlighted">
      {{ t('predictions.fuzzy.history.title') }}
    </h2>

    <div v-if="pending" aria-busy="true">
      <USkeleton class="h-32 w-full" />
    </div>

    <div v-else-if="error" role="alert" class="flex items-center gap-3">
      <p class="text-error">{{ t('predictions.fuzzy.history.error') }}</p>
      <UButton
        :label="t('predictions.retry')"
        icon="i-lucide-refresh-cw"
        variant="outline"
        @click="emit('retry')"
      />
    </div>

    <p v-else-if="predictions.length === 0" class="text-sm text-muted">
      {{ t('predictions.fuzzy.history.empty') }}
    </p>

    <UTable v-else :data="predictions" :columns="columns" />
  </section>
</template>
