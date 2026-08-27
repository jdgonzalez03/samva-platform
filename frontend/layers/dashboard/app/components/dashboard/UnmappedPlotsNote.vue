<script setup lang="ts">
import type { Plot } from '../../../../farm/app/types/farm'

const props = defineProps<{
  plots: Plot[]
}>()

const { t } = useI18n()
const localePath = useLocalePath()

const noteId = useId()
</script>

<template>
  <div class="flex flex-col gap-2">
    <p :id="noteId" class="text-sm text-muted">
      {{ t('dashboard.map.unmapped', props.plots.length) }}
    </p>
    <ul :aria-labelledby="noteId" class="flex flex-wrap gap-x-4 gap-y-1">
      <li v-for="plot in props.plots" :key="plot.id">
        <ULink
          :to="localePath(`/dashboard/plots/${plot.id}`)"
          class="inline-flex items-center min-h-6 text-sm font-medium"
        >
          {{ plot.name }}
        </ULink>
      </li>
    </ul>
  </div>
</template>
