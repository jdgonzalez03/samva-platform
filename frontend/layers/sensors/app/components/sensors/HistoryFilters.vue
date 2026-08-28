<script setup lang="ts">
import type { Plot } from '../../../../farm/app/types/farm'
import type { HistoryVariable, SensorSemanticKey } from '../../types/sensors'
import type {
  HistoryRangePreset,
  RangeIssue,
} from '../../utils/history-filters'

const props = defineProps<{
  farmName: string
  plots: Plot[]
  plotsPending: boolean
  plotId: number | null
  variables: HistoryVariable[]
  variablesPending: boolean
  variable: SensorSemanticKey | null
  rangePreset: HistoryRangePreset
  customFrom: string | null
  customTo: string | null
  rangeIssue: RangeIssue
  hasActiveFilters: boolean
}>()

const emit = defineEmits<{
  'update:plot': [plotId: number | null]
  'update:variable': [variable: SensorSemanticKey | null]
  'update:range-preset': [preset: HistoryRangePreset]
  'update:custom-range': [from: string, to: string]
  reset: []
}>()

const { t } = useI18n()

// Reka's select items reject `null` as a value, so "all" travels as a sentinel
// string and is translated back at the boundary — the URL and the API still
// only ever see an absent key.
const ALL = 'all'

const plotItems = computed(() => [
  { label: t('sensors.history.filters.allPlots'), value: ALL },
  ...props.plots.map((plot) => ({
    label: plot.name,
    value: String(plot.id),
  })),
])

const plotValue = computed(() =>
  props.plotId === null ? ALL : String(props.plotId),
)

const variableItems = computed(() => [
  { label: t('sensors.history.filters.allVariables'), value: ALL },
  ...props.variables.map((variable) => ({
    label: `${variable.name} (${variable.unit})`,
    value: variable.semantic_key,
  })),
])

const variableValue = computed(() => props.variable ?? ALL)

const rangeItems = computed(() => [
  { label: t('sensors.history.range.last24h'), value: '24h' },
  { label: t('sensors.history.range.last7d'), value: '7d' },
  { label: t('sensors.history.range.last30d'), value: '30d' },
  { label: t('sensors.history.range.custom'), value: 'custom' },
])

const rangeIssueMessage = computed(() => {
  if (props.rangeIssue === 'tooLong') return t('sensors.history.range.tooLong')
  if (props.rangeIssue === 'invalid') return t('sensors.history.range.invalid')
  return null
})

const onPlotChange = (value: string): void => {
  emit('update:plot', value === ALL ? null : Number(value))
}

const onVariableChange = (value: string): void => {
  emit('update:variable', value === ALL ? null : (value as SensorSemanticKey))
}

const onRangeChange = (value: string): void => {
  emit('update:range-preset', value as HistoryRangePreset)
}

const onCustomRange = (from: string, to: string): void => {
  emit('update:custom-range', from, to)
}
</script>

<template>
  <section
    :aria-label="t('sensors.history.filters.label')"
    class="flex flex-col gap-3 w-full"
  >
    <div class="flex flex-wrap items-end gap-3">
      <UFormField :label="t('sensors.history.filters.farm')">
        <p
          class="text-sm font-medium text-highlighted min-h-8 flex items-center"
        >
          {{ farmName }}
        </p>
      </UFormField>

      <UFormField :label="t('sensors.history.filters.plot')">
        <USelect
          :model-value="plotValue"
          :items="plotItems"
          value-key="value"
          :loading="plotsPending"
          class="w-56"
          @update:model-value="onPlotChange"
        />
      </UFormField>

      <UFormField :label="t('sensors.history.filters.variable')">
        <USelect
          :model-value="variableValue"
          :items="variableItems"
          value-key="value"
          :loading="variablesPending"
          class="w-64"
          @update:model-value="onVariableChange"
        />
      </UFormField>

      <UFormField :label="t('sensors.history.filters.range')">
        <USelect
          :model-value="rangePreset"
          :items="rangeItems"
          value-key="value"
          class="w-48"
          @update:model-value="onRangeChange"
        />
      </UFormField>

      <UButton
        v-if="hasActiveFilters"
        variant="link"
        color="neutral"
        icon="i-lucide-filter-x"
        class="min-h-8"
        @click="emit('reset')"
      >
        {{ t('sensors.history.filters.reset') }}
      </UButton>
    </div>

    <SensorsHistoryDateRange
      v-if="rangePreset === 'custom'"
      :from="customFrom"
      :to="customTo"
      @update:range="onCustomRange"
    />

    <p
      v-if="rangeIssueMessage"
      role="alert"
      class="flex items-center gap-2 text-sm text-muted"
    >
      <UIcon name="i-lucide-triangle-alert" aria-hidden="true" />
      {{ rangeIssueMessage }}
    </p>
  </section>
</template>
