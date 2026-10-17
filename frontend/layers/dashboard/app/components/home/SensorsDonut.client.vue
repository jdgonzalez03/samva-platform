<script setup lang="ts">
import { VisDonut, VisSingleContainer } from '@unovis/vue'

export interface DonutSegment {
  key: string
  count: number
  color: string
}

defineProps<{
  segments: DonutSegment[]
  centralLabel: string
  centralSubLabel: string
}>()

const value = (segment: DonutSegment): number => segment.count
const color = (segment: DonutSegment): string => segment.color
</script>

<template>
  <VisSingleContainer :data="segments" :height="180">
    <VisDonut
      :value="value"
      :color="color"
      :arc-width="22"
      :pad-angle="0.03"
      :corner-radius="4"
      :central-label="centralLabel"
      :central-sub-label="centralSubLabel"
      :show-empty-segments="false"
    />
  </VisSingleContainer>
</template>
