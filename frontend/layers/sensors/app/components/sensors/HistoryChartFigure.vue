<script setup lang="ts">
import { CHART_HEIGHT_CLASS } from '../../constants/history'

defineProps<{
  title: string
  unit: string
  icon: string
  /** The numbers a screen reader gets in place of the SVG. */
  summary: string
}>()
</script>

<template>
  <!-- The chart itself is hidden from assistive tech on purpose: a 200-point
       SVG says nothing useful read aloud. The caption names the variable and
       its unit, the summary carries the numbers, and the Table view is the
       complete textual alternative (1.1.1). -->
  <figure class="flex flex-col gap-2 rounded-lg border border-default p-3">
    <figcaption
      class="flex items-center gap-2 text-sm font-medium text-highlighted"
    >
      <UIcon :name="icon" aria-hidden="true" class="text-dimmed" />
      {{ title }} ({{ unit }})
    </figcaption>

    <div aria-hidden="true" :class="CHART_HEIGHT_CLASS" class="w-full">
      <slot />
    </div>

    <p class="sr-only">{{ summary }}</p>
  </figure>
</template>
