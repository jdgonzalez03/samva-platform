<script setup lang="ts">
import type { IrrigationPrediction } from '../../types/predictions'

const props = defineProps<{ prediction: IrrigationPrediction }>()

const { t, locale } = useI18n()

const minutes = computed(() =>
  new Intl.NumberFormat(locale.value, { maximumFractionDigits: 1 }).format(
    props.prediction.irrigation_time_minutes,
  ),
)

const computedAt = computed(() =>
  new Intl.DateTimeFormat(locale.value, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(props.prediction.requested_at)),
)
</script>

<template>
  <UCard variant="subtle">
    <div class="flex flex-wrap items-center gap-6">
      <UIcon
        name="i-lucide-droplets"
        class="size-12 text-primary shrink-0"
        aria-hidden="true"
      />
      <div class="flex flex-col gap-1">
        <h2 class="text-sm font-medium text-muted">
          {{ t('predictions.fuzzy.result.title') }}
        </h2>
        <p class="text-4xl font-semibold text-highlighted">
          {{ t('predictions.fuzzy.result.minutes', { value: minutes }) }}
        </p>
        <p class="text-xs text-muted">
          {{
            t('predictions.fuzzy.result.computedAt', {
              date: computedAt,
              hours: prediction.avg_period_hours,
            })
          }}
        </p>
      </div>
      <UBadge
        :label="t(`predictions.fuzzy.labels.${prediction.output_label}`)"
        size="xl"
        variant="subtle"
        class="ms-auto"
      />
    </div>
  </UCard>
</template>
