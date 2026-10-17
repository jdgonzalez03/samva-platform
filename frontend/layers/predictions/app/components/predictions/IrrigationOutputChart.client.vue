<script setup lang="ts">
import {
  VisArea,
  VisAxis,
  VisLine,
  VisPlotline,
  VisXYContainer,
} from '@unovis/vue'
import { CHART_HEIGHT, CHART_MARGIN } from '../../constants/predictions'
import type { FuzzyVariableDefinition } from '../../types/predictions'
import { sampleOutput, type MembershipSample } from '../../utils/membership'

const props = defineProps<{
  definition: FuzzyVariableDefinition
  activation: Record<string, number>
  minutes: number
}>()

const { t, locale } = useI18n()

const samples = computed(() => sampleOutput(props.definition, props.activation))
const terms = computed(() => Object.keys(props.definition.terms))

const x = (sample: MembershipSample): number => sample.x
const termAccessors = computed(() =>
  terms.value.map((term) => (sample: MembershipSample) => sample.terms[term]),
)
const activated = (sample: MembershipSample): number => sample.activated

const formatMinutes = (tick: number | Date): string =>
  new Intl.NumberFormat(locale.value, { maximumFractionDigits: 1 }).format(
    Number(tick),
  )
</script>

<template>
  <VisXYContainer
    :data="samples"
    :height="CHART_HEIGHT"
    :margin="CHART_MARGIN"
    :y-domain="[0, 1]"
    class="w-full"
  >
    <VisArea :x="x" :y="activated" color="var(--ui-primary)" :opacity="0.35" />
    <VisLine
      :x="x"
      :y="termAccessors"
      color="var(--ui-text-muted)"
      :line-width="1.5"
    />
    <VisPlotline
      :value="minutes"
      axis="x"
      color="var(--ui-primary)"
      :line-width="2"
      :label-text="
        t('predictions.fuzzy.result.minutes', { value: formatMinutes(minutes) })
      "
      label-color="var(--ui-text-highlighted)"
    />
    <VisAxis
      type="x"
      :grid-line="false"
      :label="t('predictions.fuzzy.chart.axis')"
      :tick-format="formatMinutes"
    />
    <VisAxis type="y" :grid-line="false" :tick-values="[0, 0.5, 1]" />
  </VisXYContainer>
</template>
