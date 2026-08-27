<script setup lang="ts">
import type { Plot } from '../../../../farm/app/types/farm'

defineProps<{
  plot: Plot
}>()

const emit = defineEmits<{ navigate: [] }>()

const { t } = useI18n()
const localePath = useLocalePath()
</script>

<template>
  <div class="flex flex-col gap-1.5 p-3 w-64">
    <p class="font-medium text-highlighted">{{ plot.name }}</p>
    <p class="text-sm text-muted">
      {{ plot.description || t('dashboard.plots.noDescription') }}
    </p>
    <p class="text-sm text-muted">
      {{ t('dashboard.plots.sensors', plot.sensor_count) }}
    </p>
    <ULink
      :to="localePath(`/dashboard/plots/${plot.id}`)"
      class="inline-flex items-center min-h-8 text-sm font-medium text-primary"
      @click="emit('navigate')"
    >
      {{ t('dashboard.plots.viewPlot') }}
    </ULink>
  </div>
</template>
