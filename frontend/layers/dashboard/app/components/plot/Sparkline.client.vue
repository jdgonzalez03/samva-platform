<script setup lang="ts">
import { CurveType } from '@unovis/ts'
import { VisArea, VisLine, VisXYContainer } from '@unovis/vue'
import { SPARKLINE_HEIGHT } from '../../constants/plot-detail'
import type { SeriesPoint } from '../../utils/plot-series'

defineProps<{ points: SeriesPoint[] }>()

const x = (point: SeriesPoint): number => point.t
const y = (point: SeriesPoint): number => point.value
</script>

<template>
  <VisXYContainer
    :data="points"
    :height="SPARKLINE_HEIGHT"
    :margin="{ top: 4, right: 0, bottom: 0, left: 0 }"
    class="w-full"
  >
    <VisArea
      :x="x"
      :y="y"
      :curve-type="CurveType.MonotoneX"
      color="var(--ui-primary)"
      :opacity="0.15"
    />
    <VisLine
      :x="x"
      :y="y"
      :curve-type="CurveType.MonotoneX"
      color="var(--ui-primary)"
      :line-width="2"
    />
  </VisXYContainer>
</template>
