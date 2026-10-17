<script setup lang="ts">
import { CurveType } from '@unovis/ts'
import { VisArea, VisLine, VisXYContainer } from '@unovis/vue'
import { STATION_SPARKLINE_HEIGHT } from '../../constants/stations'

interface SparklinePoint {
  t: number
  value: number
}

defineProps<{ points: SparklinePoint[] }>()

const x = (point: SparklinePoint): number => point.t
const y = (point: SparklinePoint): number => point.value
</script>

<template>
  <VisXYContainer
    :data="points"
    :height="STATION_SPARKLINE_HEIGHT"
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
